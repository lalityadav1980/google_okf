from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
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

    def __post_init__(self) -> None:
        required = {
            "source_system": self.source_system,
            "record_id": self.record_id,
            "version": self.version,
            "resource": self.resource,
            "title": self.title,
            "classification": self.classification,
        }
        if empty := [name for name, value in required.items() if not value.strip()]:
            raise ValueError("source record has empty required fields: " + ", ".join(empty))
        if self.modified_at.tzinfo is None or self.modified_at.utcoffset() is None:
            raise ValueError("source modified_at must include a UTC offset")
        if any(not reference.strip() for reference in self.entitlement_refs):
            raise ValueError("source entitlement references must not be empty")


class ChangeKind(StrEnum):
    UPSERT = "upsert"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class SourceChange:
    """Versioned source event; deletes never require fetching removed content."""

    source_system: str
    record_id: str
    version: str
    kind: ChangeKind
    changed_at: datetime

    def __post_init__(self) -> None:
        if not self.source_system.strip() or not self.record_id.strip() or not self.version.strip():
            raise ValueError("source change identity and version must not be empty")
        if self.changed_at.tzinfo is None or self.changed_at.utcoffset() is None:
            raise ValueError("source changed_at must include a UTC offset")


@dataclass(frozen=True, slots=True)
class ChangeBatch:
    """A repeatable page of source changes and its next incremental cursor."""

    changes: tuple[SourceChange, ...]
    next_cursor: str | None
    has_more: bool


class KnowledgeSource(Protocol):
    """Portable contract implemented by Confluence, SharePoint, YODA, and RACK adapters."""

    @property
    def source_system(self) -> str: ...

    async def list_changes(self, cursor: str | None, *, limit: int = 100) -> ChangeBatch: ...

    async def fetch_record(self, record_id: str) -> SourceRecord: ...
