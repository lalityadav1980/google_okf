from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from xyz_okf.connectors import ChangeKind, KnowledgeSource, SourceChange, SourceRecord
from xyz_okf.identity import canonical_source_record_sha256


class ConnectorIssueCode(StrEnum):
    SOURCE_CALL_FAILED = "CON-001"
    NON_REPEATABLE_PAGE = "CON-002"
    PAGE_LIMIT_EXCEEDED = "CON-003"
    CURSOR_NOT_ADVANCED = "CON-004"
    CURSOR_LOOP = "CON-005"
    DUPLICATE_EVENT = "CON-006"
    EVENT_SOURCE_MISMATCH = "CON-007"
    EVENT_ORDER_INVALID = "CON-008"
    FETCH_FAILED = "CON-009"
    RECORD_IDENTITY_MISMATCH = "CON-010"
    NON_REPEATABLE_RECORD = "CON-011"
    CLASSIFICATION_INVALID = "CON-012"
    ENTITLEMENT_MISSING = "CON-013"
    ENTITLEMENT_DUPLICATE = "CON-014"
    RESOURCE_SCHEME_INVALID = "CON-015"
    BODY_EMPTY = "CON-016"
    RECORD_NOT_CANONICALIZABLE = "CON-017"
    MAX_PAGES_REACHED = "CON-018"


class ConnectorFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ConnectorIssueCode
    message: str
    page: int = Field(ge=1)
    record_fingerprint: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")


class ConnectorCertificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str = "1.0"
    source_system: str
    collection: str
    checked_at: AwareDatetime
    pages_checked: int = Field(ge=0)
    upserts_checked: int = Field(ge=0)
    deletes_checked: int = Field(ge=0)
    terminal_cursor_reached: bool
    findings: tuple[ConnectorFinding, ...]

    @property
    def is_conformant(self) -> bool:
        return not self.findings and self.terminal_cursor_reached


def _fingerprint(change: SourceChange) -> str:
    value = f"{change.source_system}\x00{change.record_id}".encode()
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


async def certify_connector(
    source: KnowledgeSource,
    *,
    collection: str,
    checked_at: datetime,
    starting_cursor: str | None = None,
    page_size: int = 100,
    max_pages: int = 100,
) -> ConnectorCertificationReport:
    """Exercise a connector sandbox without retaining source content or raw record IDs."""

    if not collection.strip():
        raise ValueError("collection must not be empty")
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("checked_at must include a UTC offset")
    if page_size < 1 or max_pages < 1:
        raise ValueError("page_size and max_pages must be at least one")

    findings: list[ConnectorFinding] = []
    cursor = starting_cursor
    seen_output_cursors: set[str | None] = set()
    seen_events: set[tuple[str, str, str, ChangeKind]] = set()
    previous_changed_at: datetime | None = None
    pages_checked = 0
    upserts_checked = 0
    deletes_checked = 0
    terminal_cursor_reached = False

    for page in range(1, max_pages + 1):
        try:
            batch = await source.list_changes(cursor, limit=page_size)
            replay = await source.list_changes(cursor, limit=page_size)
        except Exception as exc:  # certification turns adapter failures into retained evidence
            findings.append(
                ConnectorFinding(
                    code=ConnectorIssueCode.SOURCE_CALL_FAILED,
                    message=f"list_changes failed with {type(exc).__name__}",
                    page=page,
                )
            )
            break
        pages_checked += 1
        if batch != replay:
            findings.append(
                ConnectorFinding(
                    code=ConnectorIssueCode.NON_REPEATABLE_PAGE,
                    message="replaying the same cursor and limit returned a different page",
                    page=page,
                )
            )
        if len(batch.changes) > page_size:
            findings.append(
                ConnectorFinding(
                    code=ConnectorIssueCode.PAGE_LIMIT_EXCEEDED,
                    message="connector returned more changes than the requested page limit",
                    page=page,
                )
            )
        if batch.has_more and batch.next_cursor == cursor:
            findings.append(
                ConnectorFinding(
                    code=ConnectorIssueCode.CURSOR_NOT_ADVANCED,
                    message="a non-terminal page did not advance its cursor",
                    page=page,
                )
            )
            break
        if batch.has_more and batch.next_cursor in seen_output_cursors:
            findings.append(
                ConnectorFinding(
                    code=ConnectorIssueCode.CURSOR_LOOP,
                    message="change pagination returned a previously seen output cursor",
                    page=page,
                )
            )
            break
        seen_output_cursors.add(batch.next_cursor)

        for change in batch.changes:
            record_fingerprint = _fingerprint(change)
            event_key = (
                change.source_system,
                change.record_id,
                change.version,
                change.kind,
            )
            if event_key in seen_events:
                findings.append(
                    ConnectorFinding(
                        code=ConnectorIssueCode.DUPLICATE_EVENT,
                        message="change stream repeated the same record/version/kind event",
                        page=page,
                        record_fingerprint=record_fingerprint,
                    )
                )
            seen_events.add(event_key)
            if change.source_system != source.source_system:
                findings.append(
                    ConnectorFinding(
                        code=ConnectorIssueCode.EVENT_SOURCE_MISMATCH,
                        message="change source_system differs from the connector identity",
                        page=page,
                        record_fingerprint=record_fingerprint,
                    )
                )
            if previous_changed_at is not None and change.changed_at < previous_changed_at:
                findings.append(
                    ConnectorFinding(
                        code=ConnectorIssueCode.EVENT_ORDER_INVALID,
                        message="change events are not ordered by changed_at",
                        page=page,
                        record_fingerprint=record_fingerprint,
                    )
                )
            previous_changed_at = change.changed_at
            if change.kind == ChangeKind.DELETE:
                deletes_checked += 1
                continue

            upserts_checked += 1
            try:
                record = await source.fetch_record(change.record_id)
                replayed_record = await source.fetch_record(change.record_id)
            except Exception as exc:
                findings.append(
                    ConnectorFinding(
                        code=ConnectorIssueCode.FETCH_FAILED,
                        message=f"fetch_record failed with {type(exc).__name__}",
                        page=page,
                        record_fingerprint=record_fingerprint,
                    )
                )
                continue
            _check_record(
                record,
                replayed_record,
                change,
                page=page,
                record_fingerprint=record_fingerprint,
                findings=findings,
            )

        if not batch.has_more:
            terminal_cursor_reached = True
            break
        cursor = batch.next_cursor
    else:
        findings.append(
            ConnectorFinding(
                code=ConnectorIssueCode.MAX_PAGES_REACHED,
                message="certification stopped at max_pages before a terminal page",
                page=max_pages,
            )
        )

    return ConnectorCertificationReport(
        source_system=source.source_system,
        collection=collection,
        checked_at=checked_at,
        pages_checked=pages_checked,
        upserts_checked=upserts_checked,
        deletes_checked=deletes_checked,
        terminal_cursor_reached=terminal_cursor_reached,
        findings=tuple(findings),
    )


def _check_record(
    record: SourceRecord,
    replayed_record: SourceRecord,
    change: SourceChange,
    *,
    page: int,
    record_fingerprint: str,
    findings: list[ConnectorFinding],
) -> None:
    if (
        record.source_system != change.source_system
        or record.record_id != change.record_id
        or record.version != change.version
    ):
        findings.append(
            ConnectorFinding(
                code=ConnectorIssueCode.RECORD_IDENTITY_MISMATCH,
                message="record source/ID/version differs from its change event",
                page=page,
                record_fingerprint=record_fingerprint,
            )
        )
    if record != replayed_record:
        findings.append(
            ConnectorFinding(
                code=ConnectorIssueCode.NON_REPEATABLE_RECORD,
                message="re-fetching the same record returned different normalized data",
                page=page,
                record_fingerprint=record_fingerprint,
            )
        )
    if record.classification not in {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"}:
        findings.append(
            ConnectorFinding(
                code=ConnectorIssueCode.CLASSIFICATION_INVALID,
                message="record classification is not in the bank profile vocabulary",
                page=page,
                record_fingerprint=record_fingerprint,
            )
        )
    if not record.entitlement_refs:
        findings.append(
            ConnectorFinding(
                code=ConnectorIssueCode.ENTITLEMENT_MISSING,
                message="record has no source entitlement reference",
                page=page,
                record_fingerprint=record_fingerprint,
            )
        )
    elif len(record.entitlement_refs) != len(set(record.entitlement_refs)):
        findings.append(
            ConnectorFinding(
                code=ConnectorIssueCode.ENTITLEMENT_DUPLICATE,
                message="record contains duplicate source entitlement references",
                page=page,
                record_fingerprint=record_fingerprint,
            )
        )
    if urlparse(record.resource).scheme not in {"https", "urn"}:
        findings.append(
            ConnectorFinding(
                code=ConnectorIssueCode.RESOURCE_SCHEME_INVALID,
                message="record resource must use an HTTPS or URN identifier",
                page=page,
                record_fingerprint=record_fingerprint,
            )
        )
    if not record.body.strip():
        findings.append(
            ConnectorFinding(
                code=ConnectorIssueCode.BODY_EMPTY,
                message="record body is empty after normalization",
                page=page,
                record_fingerprint=record_fingerprint,
            )
        )
    try:
        canonical_source_record_sha256(record)
    except (TypeError, ValueError):
        findings.append(
            ConnectorFinding(
                code=ConnectorIssueCode.RECORD_NOT_CANONICALIZABLE,
                message="record metadata cannot be canonicalized deterministically",
                page=page,
                record_fingerprint=record_fingerprint,
            )
        )
