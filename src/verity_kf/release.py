from __future__ import annotations

import gzip
import io
import json
import re
import tarfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Literal, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from verity_kf.identity import canonical_concept_sha256, sha256_bytes
from verity_kf.models import ProfileDefinition
from verity_kf.parser import parse_concept
from verity_kf.validator import validate_bundle

MANIFEST_PATH = "META-INF/verity-kf-release-manifest.json"
RELEASE_MEDIA_TYPE = "application/vnd.verity.kf.release.v1+tar+gzip"
MANIFEST_MEDIA_TYPE = "application/vnd.verity.kf.manifest.v1+json"
MAX_RELEASE_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_COMMIT = re.compile(r"^[0-9a-f]{7,64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
Classification = Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"]
_CLASSIFICATION_RANK: dict[Classification, int] = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONFIDENTIAL": 2,
    "RESTRICTED": 3,
}


class ReleaseBuildError(ValueError):
    """A bundle cannot be safely built or verified as a release."""


class ProfileReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: str
    profile_version: str
    okf_version: str


class ReleaseFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    size: int = Field(ge=0)
    media_type: str
    exact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    concept_uid: str | None = None
    concept_type: str | None = None
    classification: Classification | None = None
    acl_ref: str | None = None
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    criticality: Literal["low", "moderate", "high"] | None = None
    status: Literal["draft", "stable", "deprecated"] | None = None
    stale_after: AwareDatetime | None = None
    source_count: int | None = Field(default=None, ge=0)
    verified_count: int | None = Field(default=None, ge=0)


class ReleaseManifest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "$id": "https://schemas.verity-kf.example.invalid/okf/release-manifest-v1.schema.json",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        },
    )

    schema_version: Literal["1.0"] = "1.0"
    media_type: Literal["application/vnd.verity.kf.manifest.v1+json"] = (
        "application/vnd.verity.kf.manifest.v1+json"
    )
    bundle_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    release_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    consumer_contract_version: Literal["1.0"] = "1.0"
    created_at: AwareDatetime
    source_commit: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    prior_release_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    profile: ProfileReference
    bundle_classification: Classification
    files: list[ReleaseFile]

    @model_validator(mode="after")
    def validate_file_order_and_uniqueness(self) -> ReleaseManifest:
        paths = [entry.path for entry in self.files]
        if paths != sorted(paths):
            raise ValueError("manifest files must be sorted by path")
        if len(paths) != len(set(paths)):
            raise ValueError("manifest file paths must be unique")
        return self


@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    manifest: ReleaseManifest
    manifest_bytes: bytes
    manifest_sha256: str
    archive_bytes: bytes
    archive_sha256: str


@dataclass(frozen=True, slots=True)
class VerifiedRelease:
    manifest: ReleaseManifest
    manifest_sha256: str
    archive_sha256: str
    files: Mapping[str, bytes]


def _safe_archive_path(value: str) -> PurePosixPath:
    if value.startswith("/") or "\\" in value or "//" in value:
        raise ReleaseBuildError(f"unsafe archive path: {value}")
    path = PurePosixPath(value)
    if value != path.as_posix() or any(part in {"", ".", ".."} for part in path.parts):
        raise ReleaseBuildError(f"unsafe archive path: {value}")
    return path


def _manifest_bytes(manifest: ReleaseManifest) -> bytes:
    payload = manifest.model_dump(mode="json", exclude_none=True)
    return (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _archive_bytes(entries: dict[str, bytes]) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name in sorted(entries):
            content = entries[name]
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mtime = 0
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(content))
    return gzip.compress(tar_buffer.getvalue(), compresslevel=9, mtime=0)


def _source_digest(metadata: dict[str, object]) -> str | None:
    source_hash = metadata.get("source_hash")
    if not isinstance(source_hash, dict):
        return None
    digest = source_hash.get("digest")
    if isinstance(digest, str) and _HEX_SHA256.fullmatch(digest):
        return digest
    return None


def build_release(
    bundle: Path,
    profile: ProfileDefinition,
    *,
    bundle_id: str,
    release_id: str,
    source_commit: str,
    created_at: datetime,
    prior_release_digest: str | None = None,
) -> ReleaseArtifact:
    if not _SAFE_ID.fullmatch(bundle_id) or not _SAFE_ID.fullmatch(release_id):
        raise ReleaseBuildError("bundle_id and release_id must use safe portable identifiers")
    if not _SOURCE_COMMIT.fullmatch(source_commit):
        raise ReleaseBuildError("source_commit must be 7-64 lowercase hexadecimal characters")
    if prior_release_digest is not None and not _HEX_SHA256.fullmatch(prior_release_digest):
        raise ReleaseBuildError("prior_release_digest must be a lowercase SHA-256 digest")
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ReleaseBuildError("created_at must include a UTC offset")

    bundle_root = bundle.resolve()
    if not bundle_root.is_dir():
        raise ReleaseBuildError(f"bundle is not a directory: {bundle}")
    candidates = sorted(bundle_root.rglob("*"))
    for candidate in candidates:
        if candidate.is_symlink():
            raise ReleaseBuildError(
                f"bundle symlinks are not permitted: {candidate.relative_to(bundle_root)}"
            )
    report = validate_bundle(bundle_root, profile, now=created_at)
    if not report.is_valid:
        codes = sorted({issue.code.value for issue in report.issues if issue.severity == "error"})
        raise ReleaseBuildError("bundle validation failed: " + ", ".join(codes))

    source_entries: dict[str, bytes] = {}
    manifest_files: list[ReleaseFile] = []
    classifications: list[Classification] = []
    for candidate in candidates:
        if not candidate.is_file():
            continue
        relative_path = candidate.relative_to(bundle_root).as_posix()
        _safe_archive_path(relative_path)
        if relative_path == MANIFEST_PATH:
            raise ReleaseBuildError(
                f"bundle path is reserved for release metadata: {MANIFEST_PATH}"
            )
        content = candidate.read_bytes()
        source_entries[relative_path] = content
        values: dict[str, object] = {
            "path": relative_path,
            "size": len(content),
            "media_type": (
                "text/markdown; charset=utf-8"
                if candidate.suffix == ".md"
                else "application/octet-stream"
            ),
            "exact_sha256": sha256_bytes(content),
        }
        if candidate.suffix == ".md" and candidate.name not in {"index.md", "log.md"}:
            document = parse_concept(candidate, bundle_root)
            classification = document.metadata.get("classification")
            acl_ref = document.metadata.get("acl_ref")
            concept_uid = document.metadata.get("concept_uid")
            concept_type = document.metadata.get("type")
            criticality = document.metadata.get("criticality")
            status = document.metadata.get("status")
            stale_after = document.metadata.get("stale_after")
            sources = document.metadata.get("sources")
            verified = document.metadata.get("verified", [])
            if classification not in _CLASSIFICATION_RANK:
                raise ReleaseBuildError(
                    f"concept classification is missing or uncontrolled: {relative_path}"
                )
            classification_value = cast(Classification, classification)
            if not isinstance(acl_ref, str) or not acl_ref:
                raise ReleaseBuildError(f"concept acl_ref is missing: {relative_path}")
            if not isinstance(concept_uid, str) or not concept_uid:
                raise ReleaseBuildError(f"concept_uid is missing: {relative_path}")
            if not isinstance(concept_type, str) or not concept_type:
                raise ReleaseBuildError(f"concept type is missing: {relative_path}")
            if criticality not in {"low", "moderate", "high"}:
                raise ReleaseBuildError(f"concept criticality is missing: {relative_path}")
            if status not in {"draft", "stable", "deprecated"}:
                raise ReleaseBuildError(f"concept status is missing: {relative_path}")
            if not isinstance(stale_after, datetime) or (
                stale_after.tzinfo is None or stale_after.utcoffset() is None
            ):
                raise ReleaseBuildError(f"concept stale_after is missing or naive: {relative_path}")
            if not isinstance(sources, list) or not sources:
                raise ReleaseBuildError(f"concept sources are missing: {relative_path}")
            if isinstance(verified, dict):
                verified_count = 1
            elif isinstance(verified, list):
                verified_count = len(verified)
            else:
                raise ReleaseBuildError(f"concept verified field is invalid: {relative_path}")
            classifications.append(classification_value)
            values.update(
                {
                    "canonical_sha256": canonical_concept_sha256(content.decode("utf-8")),
                    "concept_uid": concept_uid,
                    "concept_type": concept_type,
                    "classification": classification_value,
                    "acl_ref": acl_ref,
                    "source_sha256": _source_digest(document.metadata),
                    "criticality": criticality,
                    "status": status,
                    "stale_after": stale_after,
                    "source_count": len(sources),
                    "verified_count": verified_count,
                }
            )
        manifest_files.append(ReleaseFile.model_validate(values))

    classification_values: list[Classification] = classifications or ["PUBLIC"]
    bundle_classification: Classification = max(
        classification_values,
        key=_CLASSIFICATION_RANK.__getitem__,
    )
    manifest = ReleaseManifest(
        bundle_id=bundle_id,
        release_id=release_id,
        created_at=created_at,
        source_commit=source_commit,
        prior_release_digest=prior_release_digest,
        profile=ProfileReference(
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            okf_version=profile.okf_version,
        ),
        bundle_classification=bundle_classification,
        files=manifest_files,
    )
    serialized_manifest = _manifest_bytes(manifest)
    archive_entries = {**source_entries, MANIFEST_PATH: serialized_manifest}
    archive = _archive_bytes(archive_entries)
    return ReleaseArtifact(
        manifest=manifest,
        manifest_bytes=serialized_manifest,
        manifest_sha256=sha256_bytes(serialized_manifest),
        archive_bytes=archive,
        archive_sha256=sha256_bytes(archive),
    )


def verify_release(
    archive_bytes: bytes,
    *,
    max_uncompressed_bytes: int = MAX_RELEASE_UNCOMPRESSED_BYTES,
) -> VerifiedRelease:
    if max_uncompressed_bytes < 1:
        raise ValueError("max_uncompressed_bytes must be at least one")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(archive_bytes)) as compressed:
            tar_bytes = compressed.read(max_uncompressed_bytes + 1)
    except (OSError, EOFError) as exc:
        raise ReleaseBuildError("release is not a valid gzip stream") from exc
    if len(tar_bytes) > max_uncompressed_bytes:
        raise ReleaseBuildError("release exceeds the configured uncompressed size limit")

    extracted: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as archive:
            for member in archive.getmembers():
                _safe_archive_path(member.name)
                if not member.isfile():
                    raise ReleaseBuildError(f"release contains a non-file entry: {member.name}")
                if member.name in extracted:
                    raise ReleaseBuildError(f"release contains a duplicate path: {member.name}")
                handle = archive.extractfile(member)
                if handle is None:
                    raise ReleaseBuildError(f"release entry cannot be read: {member.name}")
                extracted[member.name] = handle.read()
    except tarfile.TarError as exc:
        raise ReleaseBuildError("release is not a valid tar archive") from exc

    manifest_content = extracted.pop(MANIFEST_PATH, None)
    if manifest_content is None:
        raise ReleaseBuildError("release manifest is missing")
    try:
        manifest = ReleaseManifest.model_validate_json(manifest_content)
    except ValueError as exc:
        raise ReleaseBuildError(f"release manifest is invalid: {exc}") from exc
    if _manifest_bytes(manifest) != manifest_content:
        raise ReleaseBuildError("release manifest is not in canonical JSON form")
    expected_paths = {entry.path for entry in manifest.files}
    if set(extracted) != expected_paths:
        missing = sorted(expected_paths - set(extracted))
        extra = sorted(set(extracted) - expected_paths)
        raise ReleaseBuildError(
            f"release path inventory mismatch; missing={missing}, extra={extra}"
        )

    for entry in manifest.files:
        content = extracted[entry.path]
        if len(content) != entry.size or sha256_bytes(content) != entry.exact_sha256:
            raise ReleaseBuildError(f"exact file digest mismatch: {entry.path}")
        if entry.canonical_sha256 is not None:
            try:
                canonical_digest = canonical_concept_sha256(content.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                raise ReleaseBuildError(
                    f"canonical concept verification failed: {entry.path}"
                ) from exc
            if canonical_digest != entry.canonical_sha256:
                raise ReleaseBuildError(f"canonical concept digest mismatch: {entry.path}")

    return VerifiedRelease(
        manifest=manifest,
        manifest_sha256=sha256_bytes(manifest_content),
        archive_sha256=sha256_bytes(archive_bytes),
        files=MappingProxyType(extracted),
    )
