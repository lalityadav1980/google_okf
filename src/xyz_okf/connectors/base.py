from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """Immutable source record returned by a producer connector."""

    source_system: str
    record_id: str
    version: str
    resource: str
    title: str
    body: str
    modified_at: datetime
    classification: str
    entitlement_refs: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChangeBatch:
    """A repeatable page of source changes and its next incremental cursor."""

    records: tuple[SourceRecord, ...]
    next_cursor: str | None
    has_more: bool


class KnowledgeSource(Protocol):
    """Portable contract implemented by Confluence, SharePoint, YODA, and RACK adapters."""

    @property
    def source_system(self) -> str: ...

    async def list_changes(self, cursor: str | None, *, limit: int = 100) -> ChangeBatch: ...

    async def fetch_record(self, record_id: str) -> SourceRecord: ...
