from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from xyz_okf.connectors import ChangeBatch, ChangeKind, SourceChange, SourceRecord
from xyz_okf.producer import (
    ChangePlanner,
    Checkpoint,
    InMemoryCheckpointStore,
    OperationKind,
    PlannedOperation,
    ProducerEngine,
    PublicationReceipt,
    RetryableOperationError,
    RetryPolicy,
    SQLiteCheckpointStore,
)

NOW = datetime(2026, 8, 21, tzinfo=UTC)


def _change(
    record_id: str = "record-1",
    version: str = "1",
    kind: ChangeKind = ChangeKind.UPSERT,
) -> SourceChange:
    return SourceChange("synthetic", record_id, version, kind, NOW)


def _record(record_id: str = "record-1", version: str = "1") -> SourceRecord:
    return SourceRecord(
        source_system="synthetic",
        record_id=record_id,
        version=version,
        resource=f"https://sources.example.invalid/{record_id}",
        title=f"Synthetic {record_id}",
        body="# Synthetic\n",
        modified_at=NOW,
        classification="INTERNAL",
        entitlement_refs=("authz-policy:synthetic-readers",),
    )


@dataclass
class FakeSource:
    batches: dict[str | None, ChangeBatch]
    records: dict[str, SourceRecord]
    source_system: str = "synthetic"
    list_failures: int = 0
    list_calls: list[str | None] = field(default_factory=list)

    async def list_changes(self, cursor: str | None, *, limit: int = 100) -> ChangeBatch:
        self.list_calls.append(cursor)
        if self.list_failures:
            self.list_failures -= 1
            raise RetryableOperationError("rate limited", retry_after_seconds=0.5)
        return self.batches[cursor]

    async def fetch_record(self, record_id: str) -> SourceRecord:
        return self.records[record_id]


@dataclass
class FakePlanner(ChangePlanner):
    deleted_paths: dict[str, str] = field(default_factory=dict)
    fail_record: str | None = None

    async def plan_upsert(self, record: SourceRecord) -> PlannedOperation:
        if record.record_id == self.fail_record:
            raise RuntimeError("synthetic planner failure")
        return PlannedOperation.upsert(
            record=record,
            relative_path=f"references/{record.record_id}.md",
            content=record.body.encode(),
        )

    async def plan_delete(self, change: SourceChange) -> PlannedOperation:
        path = self.deleted_paths.get(change.record_id)
        if path is None:
            return PlannedOperation.noop(change=change, reason="no published identity")
        return PlannedOperation.delete(change=change, relative_path=path)


@dataclass
class FakePublisher:
    publications: list[tuple[PlannedOperation, ...]] = field(default_factory=list)
    failures: int = 0

    async def publish(self, operations: tuple[PlannedOperation, ...]) -> PublicationReceipt:
        if self.failures:
            self.failures -= 1
            raise RetryableOperationError("temporary publication failure")
        self.publications.append(operations)
        return PublicationReceipt(
            publication_id=f"publication-{len(self.publications)}",
            accepted_operation_ids=tuple(operation.operation_id for operation in operations),
        )


def _engine(
    source: FakeSource,
    *,
    planner: FakePlanner | None = None,
    publisher: FakePublisher | None = None,
    checkpoints: InMemoryCheckpointStore | None = None,
    sleeps: list[float] | None = None,
) -> ProducerEngine:
    async def record_sleep(delay: float) -> None:
        if sleeps is not None:
            sleeps.append(delay)

    return ProducerEngine(
        source=source,
        planner=planner or FakePlanner(),
        publisher=publisher or FakePublisher(),
        checkpoints=checkpoints or InMemoryCheckpointStore(),
        collection="pilot",
        retry_policy=RetryPolicy(initial_delay_seconds=0.1, max_delay_seconds=1),
        sleep=record_sleep,
        clock=lambda: NOW,
    )


def test_checkpoint_drives_incremental_restart() -> None:
    source = FakeSource(
        batches={
            None: ChangeBatch((_change(),), "cursor-1", True),
            "cursor-1": ChangeBatch((_change("record-2"),), "cursor-2", False),
        },
        records={"record-1": _record(), "record-2": _record("record-2")},
    )
    checkpoints = InMemoryCheckpointStore()
    engine = _engine(source, checkpoints=checkpoints)

    first = asyncio.run(engine.run_page())
    second = asyncio.run(engine.run_page())

    assert first.output_cursor == "cursor-1"
    assert second.input_cursor == "cursor-1"
    assert source.list_calls == [None, "cursor-1"]
    stored = asyncio.run(checkpoints.load("synthetic", "pilot"))
    assert stored is not None and stored.cursor == "cursor-2" and stored.generation == 2


def test_partial_planning_failure_does_not_publish_or_checkpoint() -> None:
    source = FakeSource(
        batches={None: ChangeBatch((_change(), _change("record-2")), "cursor-1", False)},
        records={"record-1": _record(), "record-2": _record("record-2")},
    )
    publisher = FakePublisher()
    checkpoints = InMemoryCheckpointStore()
    engine = _engine(
        source,
        planner=FakePlanner(fail_record="record-2"),
        publisher=publisher,
        checkpoints=checkpoints,
    )

    with pytest.raises(RuntimeError, match="planner failure"):
        asyncio.run(engine.run_page())

    assert publisher.publications == []
    assert asyncio.run(checkpoints.load("synthetic", "pilot")) is None


def test_retry_honors_retry_after_and_is_bounded() -> None:
    source = FakeSource(
        batches={None: ChangeBatch((), "cursor-1", False)},
        records={},
        list_failures=2,
    )
    sleeps: list[float] = []

    report = asyncio.run(_engine(source, sleeps=sleeps).run_page())

    assert report.checkpoint_advanced
    assert len(source.list_calls) == 3
    assert sleeps == [0.5, 0.5]


def test_delete_is_published_without_fetching_removed_record() -> None:
    source = FakeSource(
        batches={None: ChangeBatch((_change(kind=ChangeKind.DELETE),), "cursor-1", False)},
        records={},
    )
    publisher = FakePublisher()
    planner = FakePlanner(deleted_paths={"record-1": "references/record-1.md"})

    report = asyncio.run(_engine(source, planner=planner, publisher=publisher).run_page())

    assert report.operations[0].kind == OperationKind.DELETE
    assert publisher.publications[0][0].content is None


def test_unknown_delete_is_noop_but_checkpoint_advances() -> None:
    source = FakeSource(
        batches={None: ChangeBatch((_change(kind=ChangeKind.DELETE),), "cursor-1", False)},
        records={},
    )
    publisher = FakePublisher()

    report = asyncio.run(_engine(source, publisher=publisher).run_page())

    assert report.operations[0].kind == OperationKind.NOOP
    assert publisher.publications == []
    assert report.checkpoint_advanced


def test_dry_run_has_no_publication_or_checkpoint_side_effect() -> None:
    source = FakeSource(
        batches={None: ChangeBatch((_change(),), "cursor-1", False)},
        records={"record-1": _record()},
    )
    publisher = FakePublisher()
    checkpoints = InMemoryCheckpointStore()

    report = asyncio.run(
        _engine(source, publisher=publisher, checkpoints=checkpoints).run_page(dry_run=True)
    )

    assert len(report.operations) == 1
    assert report.dry_run and not report.checkpoint_advanced
    assert publisher.publications == []
    assert asyncio.run(checkpoints.load("synthetic", "pilot")) is None


def test_publication_retry_reuses_same_operation_id() -> None:
    source = FakeSource(
        batches={None: ChangeBatch((_change(),), "cursor-1", False)},
        records={"record-1": _record()},
    )
    publisher = FakePublisher(failures=1)
    sleeps: list[float] = []

    report = asyncio.run(_engine(source, publisher=publisher, sleeps=sleeps).run_page())

    assert report.publication_id == "publication-1"
    assert len(publisher.publications) == 1
    assert len(report.operations[0].operation_id) == 64
    assert sleeps == [0.1]


def test_retry_stops_after_configured_attempts() -> None:
    source = FakeSource(
        batches={},
        records={},
        list_failures=10,
    )
    sleeps: list[float] = []

    with pytest.raises(RetryableOperationError, match="rate limited"):
        asyncio.run(_engine(source, sleeps=sleeps).run_page())

    assert len(source.list_calls) == 4
    assert sleeps == [0.5, 0.5, 0.5]


def test_sqlite_checkpoint_is_durable_and_compare_and_set_is_atomic(tmp_path) -> None:
    database = tmp_path / "state" / "checkpoints.sqlite3"
    first_store = SQLiteCheckpointStore(database)
    initial = Checkpoint("synthetic", "pilot", "cursor-1", 1, NOW)

    assert asyncio.run(first_store.compare_and_set(None, initial))
    second_store = SQLiteCheckpointStore(database)
    assert asyncio.run(second_store.load("synthetic", "pilot")) == initial

    winner = Checkpoint("synthetic", "pilot", "cursor-2", 2, NOW)
    stale = Checkpoint("synthetic", "pilot", "cursor-stale", 2, NOW)
    assert asyncio.run(second_store.compare_and_set(initial, winner))
    assert not asyncio.run(first_store.compare_and_set(initial, stale))
    assert asyncio.run(first_store.load("synthetic", "pilot")) == winner
