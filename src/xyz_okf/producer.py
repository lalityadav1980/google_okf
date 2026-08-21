from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from collections.abc import Awaitable, Callable
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Protocol

from xyz_okf.connectors import ChangeKind, KnowledgeSource, SourceChange, SourceRecord
from xyz_okf.identity import sha256_bytes, validate_concept_path


class ProducerContractError(RuntimeError):
    """A source, planner, publisher, or checkpoint violated the producer contract."""


class RetryableOperationError(RuntimeError):
    """An adapter operation may be retried without changing its meaning."""

    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class CheckpointConflict(ProducerContractError):
    """Another runner advanced the same source checkpoint."""


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 4
    initial_delay_seconds: float = 0.25
    multiplier: float = 2.0
    max_delay_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.initial_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("retry delays must not be negative")
        if self.multiplier < 1:
            raise ValueError("retry multiplier must be at least one")


async def retry_async[ResultT](
    operation: Callable[[], Awaitable[ResultT]],
    policy: RetryPolicy,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> ResultT:
    delay = policy.initial_delay_seconds
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await operation()
        except RetryableOperationError as exc:
            if attempt == policy.max_attempts:
                raise
            requested = exc.retry_after_seconds or 0.0
            wait_seconds = min(policy.max_delay_seconds, max(delay, requested))
            await sleep(wait_seconds)
            delay = min(policy.max_delay_seconds, delay * policy.multiplier)
    raise AssertionError("retry loop exhausted without returning or raising")


@dataclass(frozen=True, slots=True)
class Checkpoint:
    source_system: str
    collection: str
    cursor: str | None
    generation: int
    committed_at: datetime

    def __post_init__(self) -> None:
        if not self.source_system.strip() or not self.collection.strip():
            raise ValueError("checkpoint source_system and collection must not be empty")
        if self.generation < 1:
            raise ValueError("checkpoint generation must be at least one")
        if self.committed_at.tzinfo is None or self.committed_at.utcoffset() is None:
            raise ValueError("checkpoint committed_at must include a UTC offset")


class CheckpointStore(Protocol):
    async def load(self, source_system: str, collection: str) -> Checkpoint | None: ...

    async def compare_and_set(
        self,
        expected: Checkpoint | None,
        replacement: Checkpoint,
    ) -> bool: ...


@dataclass(slots=True)
class InMemoryCheckpointStore:
    """Reference store with compare-and-set semantics for tests and local use."""

    _values: dict[tuple[str, str], Checkpoint] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def load(self, source_system: str, collection: str) -> Checkpoint | None:
        async with self._lock:
            return self._values.get((source_system, collection))

    async def compare_and_set(
        self,
        expected: Checkpoint | None,
        replacement: Checkpoint,
    ) -> bool:
        key = (replacement.source_system, replacement.collection)
        async with self._lock:
            current = self._values.get(key)
            if current != expected:
                return False
            self._values[key] = replacement
            return True


@dataclass(frozen=True, slots=True)
class SQLiteCheckpointStore:
    """Durable local checkpoint store with transactional compare-and-set."""

    database_path: Path

    def __post_init__(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS producer_checkpoint (
                    source_system TEXT NOT NULL,
                    collection TEXT NOT NULL,
                    cursor TEXT,
                    generation INTEGER NOT NULL,
                    committed_at TEXT NOT NULL,
                    PRIMARY KEY (source_system, collection)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @staticmethod
    def _from_row(row: tuple[str, str, str | None, int, str] | None) -> Checkpoint | None:
        if row is None:
            return None
        return Checkpoint(
            source_system=row[0],
            collection=row[1],
            cursor=row[2],
            generation=row[3],
            committed_at=datetime.fromisoformat(row[4]),
        )

    def _load_sync(self, source_system: str, collection: str) -> Checkpoint | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT source_system, collection, cursor, generation, committed_at
                FROM producer_checkpoint
                WHERE source_system = ? AND collection = ?
                """,
                (source_system, collection),
            ).fetchone()
        return self._from_row(row)

    async def load(self, source_system: str, collection: str) -> Checkpoint | None:
        return await asyncio.to_thread(self._load_sync, source_system, collection)

    def _compare_and_set_sync(
        self,
        expected: Checkpoint | None,
        replacement: Checkpoint,
    ) -> bool:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT source_system, collection, cursor, generation, committed_at
                FROM producer_checkpoint
                WHERE source_system = ? AND collection = ?
                """,
                (replacement.source_system, replacement.collection),
            ).fetchone()
            if self._from_row(row) != expected:
                connection.rollback()
                return False
            connection.execute(
                """
                INSERT INTO producer_checkpoint (
                    source_system, collection, cursor, generation, committed_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_system, collection) DO UPDATE SET
                    cursor = excluded.cursor,
                    generation = excluded.generation,
                    committed_at = excluded.committed_at
                """,
                (
                    replacement.source_system,
                    replacement.collection,
                    replacement.cursor,
                    replacement.generation,
                    replacement.committed_at.isoformat(),
                ),
            )
            connection.commit()
            return True

    async def compare_and_set(
        self,
        expected: Checkpoint | None,
        replacement: Checkpoint,
    ) -> bool:
        if expected is not None and (
            expected.source_system != replacement.source_system
            or expected.collection != replacement.collection
        ):
            raise ValueError("expected and replacement checkpoint keys must match")
        return await asyncio.to_thread(self._compare_and_set_sync, expected, replacement)


class OperationKind(StrEnum):
    UPSERT = "upsert"
    DELETE = "delete"
    NOOP = "noop"


@dataclass(frozen=True, slots=True)
class PlannedOperation:
    kind: OperationKind
    source_system: str
    record_id: str
    source_version: str
    relative_path: PurePosixPath | None
    content: bytes | None
    reason: str
    operation_id: str

    def __post_init__(self) -> None:
        if not self.source_system or not self.record_id or not self.source_version:
            raise ValueError("planned operation identity and version must not be empty")
        if not self.reason:
            raise ValueError("planned operation reason must not be empty")
        if len(self.operation_id) != 64 or any(
            character not in "0123456789abcdef" for character in self.operation_id
        ):
            raise ValueError("operation_id must be a lowercase SHA-256 digest")
        if self.kind == OperationKind.UPSERT and (
            self.relative_path is None or self.content is None
        ):
            raise ValueError("upsert operations require a path and content")
        if self.kind == OperationKind.DELETE and (
            self.relative_path is None or self.content is not None
        ):
            raise ValueError("delete operations require a path and no content")
        if self.kind == OperationKind.NOOP and (
            self.relative_path is not None or self.content is not None
        ):
            raise ValueError("no-op operations cannot contain a path or content")

    @classmethod
    def upsert(
        cls,
        *,
        record: SourceRecord,
        relative_path: str,
        content: bytes,
        reason: str = "source version changed",
    ) -> PlannedOperation:
        path = validate_concept_path(relative_path)
        return cls._create(
            kind=OperationKind.UPSERT,
            source_system=record.source_system,
            record_id=record.record_id,
            source_version=record.version,
            relative_path=path,
            content=content,
            reason=reason,
        )

    @classmethod
    def delete(
        cls,
        *,
        change: SourceChange,
        relative_path: str,
        reason: str = "source record deleted",
    ) -> PlannedOperation:
        path = validate_concept_path(relative_path)
        return cls._create(
            kind=OperationKind.DELETE,
            source_system=change.source_system,
            record_id=change.record_id,
            source_version=change.version,
            relative_path=path,
            content=None,
            reason=reason,
        )

    @classmethod
    def noop(cls, *, change: SourceChange, reason: str) -> PlannedOperation:
        return cls._create(
            kind=OperationKind.NOOP,
            source_system=change.source_system,
            record_id=change.record_id,
            source_version=change.version,
            relative_path=None,
            content=None,
            reason=reason,
        )

    @classmethod
    def _create(
        cls,
        *,
        kind: OperationKind,
        source_system: str,
        record_id: str,
        source_version: str,
        relative_path: PurePosixPath | None,
        content: bytes | None,
        reason: str,
    ) -> PlannedOperation:
        payload = {
            "content_sha256": sha256_bytes(content) if content is not None else None,
            "kind": kind,
            "path": str(relative_path) if relative_path is not None else None,
            "record_id": record_id,
            "source_system": source_system,
            "source_version": source_version,
        }
        operation_id = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        return cls(
            kind=kind,
            source_system=source_system,
            record_id=record_id,
            source_version=source_version,
            relative_path=relative_path,
            content=content,
            reason=reason,
            operation_id=operation_id,
        )


class ChangePlanner(Protocol):
    async def plan_upsert(self, record: SourceRecord) -> PlannedOperation: ...

    async def plan_delete(self, change: SourceChange) -> PlannedOperation: ...


@dataclass(frozen=True, slots=True)
class PublicationReceipt:
    publication_id: str
    accepted_operation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.publication_id:
            raise ValueError("publication_id must not be empty")
        if len(set(self.accepted_operation_ids)) != len(self.accepted_operation_ids):
            raise ValueError("publication receipt operation IDs must be unique")


class PublicationSink(Protocol):
    """Publish atomically and idempotently by operation_id, or raise."""

    async def publish(
        self,
        operations: tuple[PlannedOperation, ...],
    ) -> PublicationReceipt: ...


@dataclass(frozen=True, slots=True)
class ProducerRunReport:
    source_system: str
    collection: str
    input_cursor: str | None
    output_cursor: str | None
    operations: tuple[PlannedOperation, ...]
    dry_run: bool
    checkpoint_advanced: bool
    has_more: bool
    publication_id: str | None = None


@dataclass(slots=True)
class ProducerEngine:
    source: KnowledgeSource
    planner: ChangePlanner
    publisher: PublicationSink
    checkpoints: CheckpointStore
    collection: str
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    async def run_page(self, *, dry_run: bool = False, limit: int = 100) -> ProducerRunReport:
        if limit < 1:
            raise ValueError("limit must be at least one")
        current = await self.checkpoints.load(self.source.source_system, self.collection)
        input_cursor = current.cursor if current is not None else None
        batch = await retry_async(
            lambda: self.source.list_changes(input_cursor, limit=limit),
            self.retry_policy,
            sleep=self.sleep,
        )
        if batch.has_more and batch.next_cursor == input_cursor:
            raise ProducerContractError("a non-final change batch must advance its cursor")

        operations: list[PlannedOperation] = []
        seen: set[tuple[str, str, str]] = set()
        for change in batch.changes:
            if change.source_system != self.source.source_system:
                raise ProducerContractError("change source_system does not match connector")
            event_key = (change.record_id, change.version, change.kind)
            if event_key in seen:
                raise ProducerContractError("change batch contains a duplicate event")
            seen.add(event_key)
            if change.kind == ChangeKind.DELETE:
                operation = await self.planner.plan_delete(change)
            else:

                async def fetch_record(record_id: str = change.record_id) -> SourceRecord:
                    return await self.source.fetch_record(record_id)

                record = await retry_async(
                    fetch_record,
                    self.retry_policy,
                    sleep=self.sleep,
                )
                if (
                    record.source_system != change.source_system
                    or record.record_id != change.record_id
                    or record.version != change.version
                ):
                    raise ProducerContractError(
                        "fetched record identity/version does not match its change event"
                    )
                operation = await self.planner.plan_upsert(record)
            if (
                operation.source_system != change.source_system
                or operation.record_id != change.record_id
                or operation.source_version != change.version
            ):
                raise ProducerContractError("planned operation does not match its change event")
            operations.append(operation)

        operations_tuple = tuple(operations)
        if dry_run:
            return ProducerRunReport(
                source_system=self.source.source_system,
                collection=self.collection,
                input_cursor=input_cursor,
                output_cursor=batch.next_cursor,
                operations=operations_tuple,
                dry_run=True,
                checkpoint_advanced=False,
                has_more=batch.has_more,
            )

        actionable = tuple(
            operation for operation in operations if operation.kind != OperationKind.NOOP
        )
        receipt: PublicationReceipt | None = None
        if actionable:
            receipt = await retry_async(
                lambda: self.publisher.publish(actionable),
                self.retry_policy,
                sleep=self.sleep,
            )
            expected_ids = {operation.operation_id for operation in actionable}
            if set(receipt.accepted_operation_ids) != expected_ids:
                raise ProducerContractError(
                    "publication receipt does not acknowledge exactly the planned operations"
                )

        replacement = Checkpoint(
            source_system=self.source.source_system,
            collection=self.collection,
            cursor=batch.next_cursor,
            generation=(current.generation + 1 if current is not None else 1),
            committed_at=self.clock(),
        )
        advanced = await self.checkpoints.compare_and_set(current, replacement)
        if not advanced:
            raise CheckpointConflict("checkpoint changed during publication")
        return ProducerRunReport(
            source_system=self.source.source_system,
            collection=self.collection,
            input_cursor=input_cursor,
            output_cursor=batch.next_cursor,
            operations=operations_tuple,
            dry_run=False,
            checkpoint_advanced=True,
            has_more=batch.has_more,
            publication_id=receipt.publication_id if receipt is not None else None,
        )
