from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from typing import Any, Literal

import yaml
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from xyz_okf.connectors import SourceRecord
from xyz_okf.identity import (
    CONCEPT_CANONICALIZATION_PROFILE,
    SOURCE_CANONICALIZATION_PROFILE,
    canonical_concept_sha256,
    canonical_source_record_sha256,
)
from xyz_okf.models import ActorEvent

_RENDERED_FIELDS = {
    "type",
    "title",
    "description",
    "resource",
    "tags",
    "sources",
    "generated",
    "verified",
    "status",
    "stale_after",
    "xyz_profile_version",
    "concept_uid",
    "domain",
    "owner",
    "classification",
    "acl_ref",
    "criticality",
    "source_system",
    "source_record_id",
    "source_version",
    "source_hash",
    "canonicalization_profile",
    "producer_mapping",
    "relationships",
}
_RESERVED_OUTPUTS = {"index.md", "log.md"}


class RenderError(ValueError):
    """A deterministic render cannot proceed without violating its contract."""


class SourceRecordDocument(BaseModel):
    """Portable YAML representation used to exercise a connector record."""

    model_config = ConfigDict(extra="forbid")

    source_system: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str
    modified_at: AwareDatetime
    classification: str = Field(min_length=1)
    entitlement_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("entitlement_refs")
    @classmethod
    def validate_entitlement_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("entitlement references must not be empty")
        return values

    def to_source_record(self) -> SourceRecord:
        return SourceRecord(
            source_system=self.source_system,
            record_id=self.record_id,
            version=self.version,
            resource=self.resource,
            title=self.title,
            body=self.body,
            modified_at=self.modified_at,
            classification=self.classification,
            entitlement_refs=tuple(self.entitlement_refs),
            metadata=self.metadata,
        )


class RelationshipMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    type: str = Field(min_length=1)
    target: str = Field(min_length=1)


class RenderMapping(BaseModel):
    """Versioned, reviewable decisions for rendering one source record."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    mapping_id: str = Field(min_length=1)
    mapping_version: str = Field(min_length=1)
    output_path: str = Field(min_length=1)
    concept_uid: str = Field(min_length=1)
    type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    criticality: Literal["low", "moderate", "high"]
    profile_version: str = Field(min_length=1)
    generated_by: str = Field(min_length=1)
    stale_after_days: int = Field(gt=0)
    tags: list[str] = Field(default_factory=list)
    status: Literal["draft", "stable", "deprecated"] = "draft"
    acl_ref: str | None = None
    source_author: str | None = None
    verified: list[ActorEvent] = Field(default_factory=list)
    relationships: list[RelationshipMapping] = Field(default_factory=list)
    frontmatter_extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, value: str) -> str:
        if "\\" in value or value.startswith("/") or "//" in value:
            raise ValueError("output_path must be a normalized relative POSIX path")
        path = PurePosixPath(value)
        if (
            value != path.as_posix()
            or any(part in {"", ".", ".."} for part in path.parts)
            or path.suffix != ".md"
            or path.name in _RESERVED_OUTPUTS
        ):
            raise ValueError(
                "output_path must be a normalized relative .md concept path and not a reserved file"
            )
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("tags must not be empty")
        return values

    @model_validator(mode="after")
    def protect_rendered_fields(self) -> RenderMapping:
        collisions = sorted(_RENDERED_FIELDS & self.frontmatter_extensions.keys())
        if collisions:
            raise ValueError(
                "frontmatter_extensions cannot replace renderer-controlled fields: "
                + ", ".join(collisions)
            )
        return self


@dataclass(frozen=True, slots=True)
class RenderedConcept:
    relative_path: PurePosixPath
    content: bytes
    sha256: str
    canonical_sha256: str
    source_sha256: str

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")


def _iso8601_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RenderError("source and verification timestamps must include a UTC offset")
    normalized = value.astimezone(UTC)
    timespec = "microseconds" if normalized.microsecond else "seconds"
    return normalized.isoformat(timespec=timespec).replace("+00:00", "Z")


def _canonical_json_value(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        return {key: _canonical_json_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical_json_value(item) for item in value]
    return value


def _select_acl(record: SourceRecord, mapping: RenderMapping) -> str:
    source_refs = tuple(sorted(set(record.entitlement_refs)))
    if mapping.acl_ref is not None:
        if mapping.acl_ref not in source_refs:
            raise RenderError(
                f"mapped acl_ref '{mapping.acl_ref}' is not present in source entitlements"
            )
        return mapping.acl_ref
    if len(source_refs) != 1:
        raise RenderError(
            "acl_ref must be explicitly mapped when the source has zero or multiple entitlements"
        )
    return source_refs[0]


def _canonical_body(body: str) -> str:
    normalized = body.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    return normalized + "\n" if normalized else ""


def _frontmatter(record: SourceRecord, mapping: RenderMapping) -> dict[str, Any]:
    modified_at = _iso8601_utc(record.modified_at)
    stale_after = _iso8601_utc(record.modified_at + timedelta(days=mapping.stale_after_days))
    generated = ActorEvent(by=mapping.generated_by, at=record.modified_at)

    metadata: dict[str, Any] = {
        "type": mapping.type,
        "title": record.title,
        "description": mapping.description,
        "resource": record.resource,
        "tags": sorted(set(mapping.tags)),
        "sources": [
            {
                "id": record.source_system,
                "resource": record.resource,
                "title": record.title,
                **({"author": mapping.source_author} if mapping.source_author else {}),
                "last_modified": modified_at,
            }
        ],
        "generated": {"by": generated.by, "at": modified_at},
    }
    if mapping.verified:
        metadata["verified"] = [
            {"by": event.by, "at": _iso8601_utc(event.at)}
            for event in sorted(mapping.verified, key=lambda item: (_iso8601_utc(item.at), item.by))
        ]
    metadata.update(
        {
            "status": mapping.status,
            "stale_after": stale_after,
            "xyz_profile_version": mapping.profile_version,
            "concept_uid": mapping.concept_uid,
            "domain": mapping.domain,
            "owner": mapping.owner,
            "classification": record.classification,
            "acl_ref": _select_acl(record, mapping),
            "criticality": mapping.criticality,
            "source_system": record.source_system,
            "source_record_id": record.record_id,
            "source_version": record.version,
            "source_hash": {
                "algorithm": "sha256",
                "profile": SOURCE_CANONICALIZATION_PROFILE,
                "digest": canonical_source_record_sha256(record),
            },
            "canonicalization_profile": CONCEPT_CANONICALIZATION_PROFILE,
            "producer_mapping": {
                "id": mapping.mapping_id,
                "version": mapping.mapping_version,
            },
        }
    )
    if mapping.relationships:
        metadata["relationships"] = [
            {"type": relationship.type, "target": relationship.target}
            for relationship in sorted(
                mapping.relationships,
                key=lambda item: (item.type, item.target),
            )
        ]
    metadata.update(
        {
            key: _canonical_json_value(value)
            for key, value in sorted(mapping.frontmatter_extensions.items())
        }
    )
    return metadata


def render_concept(record: SourceRecord, mapping: RenderMapping) -> RenderedConcept:
    """Render canonical UTF-8 OKF bytes from a source record and mapping version."""

    required_source_values: Mapping[str, str] = {
        "source_system": record.source_system,
        "record_id": record.record_id,
        "version": record.version,
        "resource": record.resource,
        "title": record.title,
        "classification": record.classification,
    }
    empty = [name for name, value in required_source_values.items() if not value.strip()]
    if empty:
        raise RenderError("source record has empty required fields: " + ", ".join(empty))

    metadata = _frontmatter(record, mapping)
    dumped = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=10_000,
    )
    text = f"---\n{dumped}---\n\n{_canonical_body(record.body)}"
    content = text.encode("utf-8")
    return RenderedConcept(
        relative_path=PurePosixPath(mapping.output_path),
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        canonical_sha256=canonical_concept_sha256(text),
        source_sha256=canonical_source_record_sha256(record),
    )
