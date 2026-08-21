from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

from verity_kf.connectors import SourceRecord
from verity_kf.parser import split_frontmatter

_SOURCE_SYSTEM = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_RESERVED_NAMES = {"index.md", "log.md"}
CONCEPT_CANONICALIZATION_PROFILE = "verity-kf-concept-c14n-v1"
SOURCE_CANONICALIZATION_PROFILE = "verity-kf-source-c14n-v1"
_CONCEPT_HASH_DOMAIN = f"{CONCEPT_CANONICALIZATION_PROFILE}\n".encode()
_SOURCE_HASH_DOMAIN = f"{SOURCE_CANONICALIZATION_PROFILE}\n".encode()


class CanonicalizationError(ValueError):
    """Input cannot be represented by the VerityKF canonicalization profile."""


class SourceAnchor(BaseModel):
    """Stable source identity; version and mutable display fields are excluded."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_system: str = Field(min_length=2, max_length=32)
    record_id: str = Field(min_length=1)
    fragment: str = ""

    @field_validator("source_system")
    @classmethod
    def validate_source_system(cls, value: str) -> str:
        if not _SOURCE_SYSTEM.fullmatch(value):
            raise ValueError("source_system must match ^[a-z][a-z0-9_-]{1,31}$")
        return value

    @field_validator("record_id", "fragment")
    @classmethod
    def reject_ambiguous_text(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value)
        if "\x00" in normalized:
            raise ValueError("source anchor fields must not contain NUL")
        return normalized

    def canonical_name(self) -> str:
        return json.dumps(
            self.model_dump(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


class IdentityPolicy(BaseModel):
    """Versioned organizational rules for new stable IDs and paths."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    namespace_uuid: UUID
    uid_prefix: str = Field(default="urn:verity-kf:concept:", min_length=1)
    default_directory: str = Field(default="concepts", min_length=1)
    type_directories: dict[str, str] = Field(default_factory=dict)
    max_slug_length: int = Field(default=72, ge=16, le=160)

    @field_validator("default_directory")
    @classmethod
    def validate_default_directory(cls, value: str) -> str:
        _validate_directory(value)
        return value

    @field_validator("type_directories")
    @classmethod
    def validate_type_directories(cls, values: dict[str, str]) -> dict[str, str]:
        for type_name, directory in values.items():
            if not type_name.strip():
                raise ValueError("type directory keys must not be empty")
            _validate_directory(directory)
        return values


@dataclass(frozen=True, slots=True)
class AllocatedIdentity:
    concept_uid: str
    output_path: PurePosixPath
    concept_id: str
    source_anchor: SourceAnchor
    policy_id: str
    policy_version: str


def _validate_directory(value: str) -> None:
    if value.startswith("/") or "\\" in value or "//" in value:
        raise ValueError("concept directories must be normalized relative POSIX paths")
    path = PurePosixPath(value)
    if value != path.as_posix() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("concept directories must be normalized relative POSIX paths")


def validate_concept_path(value: str) -> PurePosixPath:
    if value.startswith("/") or "\\" in value or "//" in value:
        raise ValueError("concept path must be a normalized relative POSIX path")
    path = PurePosixPath(value)
    if (
        value != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.suffix != ".md"
        or path.name.casefold() in _RESERVED_NAMES
    ):
        raise ValueError("concept path must be a non-reserved relative .md path")
    return path


def concept_id_from_path(path: str | PurePosixPath) -> str:
    validated = validate_concept_path(str(path))
    return validated.with_suffix("").as_posix()


def _slug(value: str, max_length: int) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii").casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    slug = slug[:max_length].rstrip("-")
    return slug or "concept"


def allocate_identity(
    anchor: SourceAnchor,
    *,
    title: str,
    concept_type: str,
    policy: IdentityPolicy,
    retained_path: str | None = None,
) -> AllocatedIdentity:
    """Allocate a stable UID and initial path, or retain a reviewed prior path."""

    stable_uuid = uuid5(policy.namespace_uuid, anchor.canonical_name())
    concept_uid = f"{policy.uid_prefix}{stable_uuid}"
    if retained_path is not None:
        output_path = validate_concept_path(retained_path)
    else:
        directory = policy.type_directories.get(concept_type, policy.default_directory)
        filename = f"{_slug(title, policy.max_slug_length)}--{stable_uuid.hex[:12]}.md"
        output_path = validate_concept_path(f"{directory}/{filename}")
    return AllocatedIdentity(
        concept_uid=concept_uid,
        output_path=output_path,
        concept_id=concept_id_from_path(output_path),
        source_anchor=anchor,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
    )


def _normalize_datetime(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CanonicalizationError("canonical timestamps must include a UTC offset")
    normalized = value.astimezone(UTC)
    timespec = "microseconds" if normalized.microsecond else "seconds"
    return normalized.isoformat(timespec=timespec).replace("+00:00", "Z")


def _canonical_value(value: Any) -> list[Any]:
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError("non-finite YAML numbers are not canonicalizable")
        return ["float", repr(value)]
    if isinstance(value, datetime):
        return ["datetime", _normalize_datetime(value)]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, str):
        return ["string", unicodedata.normalize("NFC", value)]
    if isinstance(value, Mapping):
        normalized_items: list[tuple[str, list[Any]]] = []
        seen: set[str] = set()
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("canonical mapping keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in seen:
                raise CanonicalizationError("mapping keys collide after Unicode normalization")
            seen.add(normalized_key)
            normalized_items.append((normalized_key, _canonical_value(item)))
        return ["mapping", [[key, item] for key, item in sorted(normalized_items)]]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return ["sequence", [_canonical_value(item) for item in value]]
    raise CanonicalizationError(f"unsupported canonical value type: {type(value).__name__}")


def _canonical_body(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    stripped = normalized.strip("\n")
    return stripped + "\n" if stripped else ""


def _canonical_payload(value: Any) -> bytes:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_concept_bytes(text: str) -> bytes:
    metadata, body = split_frontmatter(text)
    payload = {
        "frontmatter": metadata,
        "body": _canonical_body(body),
    }
    return _CONCEPT_HASH_DOMAIN + _canonical_payload(payload)


def canonical_concept_sha256(text: str) -> str:
    return sha256_bytes(canonical_concept_bytes(text))


def canonical_source_record_bytes(record: SourceRecord) -> bytes:
    payload = {
        "body": _canonical_body(record.body),
        "classification": record.classification,
        "entitlement_refs": sorted(set(record.entitlement_refs)),
        "metadata": record.metadata,
        "modified_at": record.modified_at,
        "record_id": record.record_id,
        "resource": record.resource,
        "source_system": record.source_system,
        "title": record.title,
        "version": record.version,
    }
    return _SOURCE_HASH_DOMAIN + _canonical_payload(payload)


def canonical_source_record_sha256(record: SourceRecord) -> str:
    return sha256_bytes(canonical_source_record_bytes(record))
