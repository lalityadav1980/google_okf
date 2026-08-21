from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from xyz_okf.connector_conformance import ConnectorIssueCode, certify_connector
from xyz_okf.connectors import ChangeBatch, ChangeKind, SourceChange, SourceRecord

NOW = datetime(2026, 8, 21, tzinfo=UTC)


def _change(
    record_id: str,
    version: str,
    *,
    kind: ChangeKind = ChangeKind.UPSERT,
    changed_at: datetime = NOW,
    source_system: str = "synthetic",
) -> SourceChange:
    return SourceChange(source_system, record_id, version, kind, changed_at)


def _record(
    record_id: str,
    version: str,
    *,
    classification: str = "INTERNAL",
    entitlements: tuple[str, ...] = ("authz-policy:synthetic-readers",),
    resource: str | None = None,
    body: str = "# Synthetic\n",
    metadata: dict[str, object] | None = None,
) -> SourceRecord:
    return SourceRecord(
        source_system="synthetic",
        record_id=record_id,
        version=version,
        resource=resource or f"https://sources.example.invalid/{record_id}",
        title=f"Synthetic {record_id}",
        body=body,
        modified_at=NOW,
        classification=classification,
        entitlement_refs=entitlements,
        metadata=metadata or {},
    )


@dataclass
class SandboxSource:
    batches: dict[str | None, ChangeBatch]
    records: dict[str, SourceRecord]
    source_system: str = "synthetic"
    fetched_ids: list[str] = field(default_factory=list)
    alternate_replay: ChangeBatch | None = None
    list_count: int = 0

    async def list_changes(self, cursor: str | None, *, limit: int = 100) -> ChangeBatch:
        self.list_count += 1
        if self.alternate_replay is not None and self.list_count % 2 == 0:
            return self.alternate_replay
        return self.batches[cursor]

    async def fetch_record(self, record_id: str) -> SourceRecord:
        self.fetched_ids.append(record_id)
        return self.records[record_id]


def test_conformant_connector_covers_repeatable_pages_upserts_and_deletes() -> None:
    source = SandboxSource(
        batches={
            None: ChangeBatch((_change("one", "1"),), "cursor-1", True),
            "cursor-1": ChangeBatch(
                (
                    _change("two", "2", changed_at=NOW + timedelta(minutes=1)),
                    _change(
                        "removed",
                        "3",
                        kind=ChangeKind.DELETE,
                        changed_at=NOW + timedelta(minutes=2),
                    ),
                ),
                "cursor-2",
                False,
            ),
        },
        records={"one": _record("one", "1"), "two": _record("two", "2")},
    )

    report = asyncio.run(
        certify_connector(source, collection="sandbox", checked_at=NOW, page_size=10)
    )

    assert report.is_conformant
    assert report.pages_checked == 2
    assert report.upserts_checked == 2
    assert report.deletes_checked == 1
    assert "removed" not in source.fetched_ids


def test_certification_detects_cursor_replay_and_never_retains_raw_record_id() -> None:
    sensitive_id = "internal-record-name"
    first = ChangeBatch((_change(sensitive_id, "1"),), None, True)
    alternate = ChangeBatch((_change("different", "1"),), None, True)
    source = SandboxSource(
        batches={None: first},
        records={sensitive_id: _record(sensitive_id, "1")},
        alternate_replay=alternate,
    )

    report = asyncio.run(
        certify_connector(source, collection="sandbox", checked_at=NOW, page_size=1)
    )

    codes = {finding.code for finding in report.findings}
    assert ConnectorIssueCode.NON_REPEATABLE_PAGE in codes
    assert ConnectorIssueCode.CURSOR_NOT_ADVANCED in codes
    assert sensitive_id not in report.model_dump_json()


def test_certification_reports_entitlement_classification_resource_body_and_metadata() -> None:
    change = _change("invalid", "1")
    source = SandboxSource(
        batches={None: ChangeBatch((change,), "done", False)},
        records={
            "invalid": _record(
                "invalid",
                "1",
                classification="UNCONTROLLED",
                entitlements=(),
                resource="http://sources.example.invalid/invalid",
                body="   ",
                metadata={"unsupported": object()},
            )
        },
    )

    report = asyncio.run(certify_connector(source, collection="sandbox", checked_at=NOW))

    assert {finding.code for finding in report.findings} >= {
        ConnectorIssueCode.CLASSIFICATION_INVALID,
        ConnectorIssueCode.ENTITLEMENT_MISSING,
        ConnectorIssueCode.RESOURCE_SCHEME_INVALID,
        ConnectorIssueCode.BODY_EMPTY,
        ConnectorIssueCode.RECORD_NOT_CANONICALIZABLE,
    }
    assert not report.is_conformant


def test_duplicate_and_out_of_order_events_are_reported() -> None:
    later = _change("one", "1", changed_at=NOW + timedelta(minutes=1))
    earlier = _change("two", "1", changed_at=NOW)
    source = SandboxSource(
        batches={None: ChangeBatch((later, earlier, earlier), "done", False)},
        records={"one": _record("one", "1"), "two": _record("two", "1")},
    )

    report = asyncio.run(certify_connector(source, collection="sandbox", checked_at=NOW))

    codes = {finding.code for finding in report.findings}
    assert ConnectorIssueCode.DUPLICATE_EVENT in codes
    assert ConnectorIssueCode.EVENT_ORDER_INVALID in codes
