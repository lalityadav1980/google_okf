from __future__ import annotations

import copy
import json
import re
import stat
import uuid
import zipfile
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from verity_kf.identity import sha256_bytes

FRAMEWORK_SBOM_NAME = "verity-knowledge-fabric-runtime.cdx.json"
FRAMEWORK_EVIDENCE_NAME = "verity-knowledge-fabric-build-evidence.json"
FRAMEWORK_EVIDENCE_MEDIA_TYPE: Literal["application/vnd.verity.kf.build-evidence.v1+json"] = (
    "application/vnd.verity.kf.build-evidence.v1+json"
)
SBOM_MEDIA_TYPE = "application/vnd.cyclonedx+json; version=1.5"
REQUIRED_WHEEL_CONTRACTS = frozenset(
    {
        "verity_kf/assets/policies/release_admission.rego",
        "verity_kf/assets/schemas/framework-build-evidence-v1.schema.json",
        "verity_kf/assets/schemas/pilot-benchmark-v1.schema.json",
        "verity_kf/assets/schemas/release-manifest-v1.schema.json",
        "verity_kf/assets/schemas/serving-api-v1.openapi.json",
        "verity_kf/assets/schemas/source-discovery-v1.schema.json",
    }
)

_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_COMMIT = re.compile(r"^[0-9a-f]{7,64}$")


class FrameworkEvidenceError(ValueError):
    """Framework build evidence cannot be created or verified safely."""


class FrameworkArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    size: int = Field(ge=0)
    media_type: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FrameworkBuildEvidence(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "$id": (
                "https://schemas.verity-kf.example.invalid/okf/"
                "framework-build-evidence-v1.schema.json"
            ),
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        },
    )

    schema_version: Literal["1.0"] = "1.0"
    media_type: Literal["application/vnd.verity.kf.build-evidence.v1+json"] = (
        FRAMEWORK_EVIDENCE_MEDIA_TYPE
    )
    package_name: Literal["verity-knowledge-fabric"] = "verity-knowledge-fabric"
    package_version: str = Field(pattern=r"^[0-9A-Za-z][0-9A-Za-z.+-]*$")
    source_commit: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    created_at: AwareDatetime
    python_version: str = Field(min_length=1)
    uv_version: str = Field(min_length=1)
    uv_lock_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifacts: list[FrameworkArtifact] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_artifact_order_and_uniqueness(self) -> FrameworkBuildEvidence:
        paths = [artifact.path for artifact in self.artifacts]
        if paths != sorted(paths):
            raise ValueError("framework artifacts must be sorted by path")
        if len(paths) != len(set(paths)):
            raise ValueError("framework artifact paths must be unique")
        for path in paths:
            _safe_relative_path(path)
        return self


def _safe_relative_path(value: str) -> PurePosixPath:
    if not value or value.startswith("/") or "\\" in value or "//" in value:
        raise FrameworkEvidenceError(f"unsafe artifact path: {value}")
    path = PurePosixPath(value)
    if value != path.as_posix() or any(part in {"", ".", ".."} for part in path.parts):
        raise FrameworkEvidenceError(f"unsafe artifact path: {value}")
    return path


def _sort_properties(container: dict[str, Any]) -> None:
    properties = container.get("properties")
    if isinstance(properties, list):
        properties.sort(key=lambda value: (str(value.get("name", "")), str(value.get("value", ""))))


def normalize_cyclonedx_sbom(
    payload: Mapping[str, Any],
    *,
    package_name: str,
    package_version: str,
    uv_lock_sha256: str,
) -> bytes:
    """Normalize uv's volatile CycloneDX fields into deterministic JSON bytes."""
    if payload.get("bomFormat") != "CycloneDX" or payload.get("specVersion") != "1.5":
        raise FrameworkEvidenceError("expected a CycloneDX 1.5 JSON document")
    if not _HEX_SHA256.fullmatch(uv_lock_sha256):
        raise FrameworkEvidenceError("uv_lock_sha256 must be a lowercase SHA-256 digest")

    normalized = copy.deepcopy(dict(payload))
    normalized["serialNumber"] = "urn:uuid:" + str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"urn:verity-kf:framework:{package_name}:{package_version}:{uv_lock_sha256}",
        )
    )
    metadata = normalized.get("metadata")
    if not isinstance(metadata, dict):
        raise FrameworkEvidenceError("CycloneDX metadata must be an object")
    metadata.pop("timestamp", None)
    component = metadata.get("component")
    if not isinstance(component, dict):
        raise FrameworkEvidenceError("CycloneDX metadata.component must be an object")
    if component.get("name") != package_name or component.get("version") != package_version:
        raise FrameworkEvidenceError("CycloneDX root component does not match the package")
    properties = component.setdefault("properties", [])
    if not isinstance(properties, list):
        raise FrameworkEvidenceError("CycloneDX component properties must be an array")
    properties[:] = [
        value
        for value in properties
        if not (
            isinstance(value, dict)
            and value.get("name") == "verity-knowledge-fabric:uv-lock-sha256"
        )
    ]
    properties.append({"name": "verity-knowledge-fabric:uv-lock-sha256", "value": uv_lock_sha256})
    _sort_properties(component)

    components = normalized.get("components", [])
    if not isinstance(components, list):
        raise FrameworkEvidenceError("CycloneDX components must be an array")
    for dependency_component in components:
        if not isinstance(dependency_component, dict):
            raise FrameworkEvidenceError("CycloneDX components must contain objects")
        _sort_properties(dependency_component)
        hashes = dependency_component.get("hashes")
        if isinstance(hashes, list):
            hashes.sort(
                key=lambda value: (str(value.get("alg", "")), str(value.get("content", "")))
            )
    components.sort(
        key=lambda value: (
            str(value.get("bom-ref", "")),
            str(value.get("name", "")),
            str(value.get("version", "")),
        )
    )

    dependencies = normalized.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise FrameworkEvidenceError("CycloneDX dependencies must be an array")
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise FrameworkEvidenceError("CycloneDX dependencies must contain objects")
        depends_on = dependency.get("dependsOn")
        if isinstance(depends_on, list):
            depends_on.sort(key=str)
    dependencies.sort(key=lambda value: str(value.get("ref", "")))

    return (
        json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def verify_framework_wheel(
    wheel_path: Path,
    *,
    required_contracts: Iterable[str] = REQUIRED_WHEEL_CONTRACTS,
) -> frozenset[str]:
    if wheel_path.is_symlink() or not wheel_path.is_file():
        raise FrameworkEvidenceError(f"wheel must be a regular file: {wheel_path}")
    try:
        with zipfile.ZipFile(wheel_path) as wheel:
            members = wheel.infolist()
    except zipfile.BadZipFile as exc:
        raise FrameworkEvidenceError(f"wheel is not a valid ZIP archive: {wheel_path}") from exc

    names = [member.filename for member in members]
    if len(names) != len(set(names)):
        raise FrameworkEvidenceError("wheel contains duplicate member names")
    for member in members:
        _safe_relative_path(member.filename.rstrip("/"))
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise FrameworkEvidenceError(f"wheel contains a symlink: {member.filename}")

    required = set(required_contracts)
    missing = sorted(required.difference(names))
    if missing:
        raise FrameworkEvidenceError("wheel is missing runtime contracts: " + ", ".join(missing))
    return frozenset(names)


def _artifact_media_type(path: Path) -> str:
    if path.name == FRAMEWORK_SBOM_NAME:
        return SBOM_MEDIA_TYPE
    if path.suffix == ".whl":
        return "application/vnd.python.wheel+zip"
    if path.name.endswith(".tar.gz"):
        return "application/gzip"
    raise FrameworkEvidenceError(f"unsupported framework artifact: {path.name}")


def build_framework_evidence(
    artifacts: Sequence[Path],
    *,
    artifact_root: Path,
    package_version: str,
    source_commit: str,
    created_at: datetime,
    python_version: str,
    uv_version: str,
    uv_lock_sha256: str,
) -> FrameworkBuildEvidence:
    if not _SOURCE_COMMIT.fullmatch(source_commit):
        raise FrameworkEvidenceError("source_commit must be 7-64 lowercase hexadecimal characters")
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise FrameworkEvidenceError("created_at must include a UTC offset")
    if not _HEX_SHA256.fullmatch(uv_lock_sha256):
        raise FrameworkEvidenceError("uv_lock_sha256 must be a lowercase SHA-256 digest")

    resolved_root = artifact_root.resolve()
    entries: list[FrameworkArtifact] = []
    for artifact in artifacts:
        if artifact.is_symlink() or not artifact.is_file():
            raise FrameworkEvidenceError(f"artifact must be a regular file: {artifact}")
        resolved = artifact.resolve()
        try:
            relative = resolved.relative_to(resolved_root).as_posix()
        except ValueError as exc:
            raise FrameworkEvidenceError(f"artifact is outside artifact_root: {artifact}") from exc
        _safe_relative_path(relative)
        content = resolved.read_bytes()
        entries.append(
            FrameworkArtifact(
                path=relative,
                size=len(content),
                media_type=_artifact_media_type(resolved),
                sha256=sha256_bytes(content),
            )
        )

    return FrameworkBuildEvidence(
        package_version=package_version,
        source_commit=source_commit,
        created_at=created_at,
        python_version=python_version,
        uv_version=uv_version,
        uv_lock_sha256=uv_lock_sha256,
        artifacts=sorted(entries, key=lambda entry: entry.path),
    )


def framework_evidence_bytes(evidence: FrameworkBuildEvidence) -> bytes:
    payload = evidence.model_dump(mode="json")
    return (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def verify_framework_evidence_directory(
    artifact_root: Path,
    *,
    expected_source_commit: str | None = None,
    expected_uv_lock_sha256: str | None = None,
    expected_evidence_sha256: str | None = None,
) -> FrameworkBuildEvidence:
    """Verify artifact consistency plus optional externally supplied commit/lock expectations."""
    if artifact_root.is_symlink() or not artifact_root.is_dir():
        raise FrameworkEvidenceError(f"artifact_root must be a regular directory: {artifact_root}")
    root = artifact_root.resolve()
    evidence_path = root / FRAMEWORK_EVIDENCE_NAME
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise FrameworkEvidenceError(f"framework evidence is missing: {evidence_path}")
    evidence_content = evidence_path.read_bytes()
    if expected_evidence_sha256 is not None:
        if not _HEX_SHA256.fullmatch(expected_evidence_sha256):
            raise FrameworkEvidenceError(
                "expected_evidence_sha256 must be a lowercase SHA-256 digest"
            )
        if sha256_bytes(evidence_content) != expected_evidence_sha256:
            raise FrameworkEvidenceError("framework evidence digest does not match expected")
    try:
        evidence = FrameworkBuildEvidence.model_validate_json(evidence_content)
    except ValueError as exc:
        raise FrameworkEvidenceError("framework evidence is not valid") from exc
    if framework_evidence_bytes(evidence) != evidence_content:
        raise FrameworkEvidenceError("framework evidence is not canonically encoded")
    if expected_source_commit is not None and evidence.source_commit != expected_source_commit:
        raise FrameworkEvidenceError("framework evidence source commit does not match expected")
    if expected_uv_lock_sha256 is not None and evidence.uv_lock_sha256 != expected_uv_lock_sha256:
        raise FrameworkEvidenceError("framework evidence lock digest does not match expected")

    expected_paths = {artifact.path for artifact in evidence.artifacts}
    expected_paths.add(FRAMEWORK_EVIDENCE_NAME)
    actual_paths: set[str] = set()
    for candidate in root.iterdir():
        if candidate.is_symlink() or not candidate.is_file():
            raise FrameworkEvidenceError(
                f"unexpected non-file framework artifact: {candidate.name}"
            )
        actual_paths.add(candidate.name)
    if actual_paths != expected_paths:
        missing = sorted(expected_paths.difference(actual_paths))
        unexpected = sorted(actual_paths.difference(expected_paths))
        raise FrameworkEvidenceError(
            f"framework artifact inventory mismatch; missing={missing}; unexpected={unexpected}"
        )

    wheel_paths: list[Path] = []
    sbom_path: Path | None = None
    for artifact in evidence.artifacts:
        candidate = root / artifact.path
        if candidate.is_symlink() or not candidate.is_file():
            raise FrameworkEvidenceError(f"framework artifact is missing: {artifact.path}")
        content = candidate.read_bytes()
        if len(content) != artifact.size or sha256_bytes(content) != artifact.sha256:
            raise FrameworkEvidenceError(
                f"framework artifact digest/size mismatch: {artifact.path}"
            )
        if _artifact_media_type(candidate) != artifact.media_type:
            raise FrameworkEvidenceError(f"framework artifact media type mismatch: {artifact.path}")
        if candidate.suffix == ".whl":
            wheel_paths.append(candidate)
        elif candidate.name == FRAMEWORK_SBOM_NAME:
            sbom_path = candidate

    if len(wheel_paths) != 1 or sbom_path is None:
        raise FrameworkEvidenceError(
            "framework evidence must contain one wheel and one runtime SBOM"
        )
    verify_framework_wheel(wheel_paths[0])
    try:
        sbom_payload = json.loads(sbom_path.read_bytes())
    except json.JSONDecodeError as exc:
        raise FrameworkEvidenceError("runtime SBOM is not valid JSON") from exc
    normalized_sbom = normalize_cyclonedx_sbom(
        sbom_payload,
        package_name=evidence.package_name,
        package_version=evidence.package_version,
        uv_lock_sha256=evidence.uv_lock_sha256,
    )
    if normalized_sbom != sbom_path.read_bytes():
        raise FrameworkEvidenceError("runtime SBOM is not canonically normalized")
    return evidence


def compare_framework_evidence_directories(
    first_root: Path,
    second_root: Path,
    *,
    expected_source_commit: str | None = None,
    expected_uv_lock_sha256: str | None = None,
) -> dict[str, str]:
    """Verify two builds and prove every retained artifact is byte-identical."""
    first = verify_framework_evidence_directory(
        first_root,
        expected_source_commit=expected_source_commit,
        expected_uv_lock_sha256=expected_uv_lock_sha256,
    )
    second = verify_framework_evidence_directory(
        second_root,
        expected_source_commit=expected_source_commit,
        expected_uv_lock_sha256=expected_uv_lock_sha256,
    )
    if first != second:
        raise FrameworkEvidenceError("framework evidence documents differ between builds")

    paths = [FRAMEWORK_EVIDENCE_NAME, *(artifact.path for artifact in first.artifacts)]
    digests: dict[str, str] = {}
    for relative_path in sorted(paths):
        first_content = (first_root / relative_path).read_bytes()
        second_content = (second_root / relative_path).read_bytes()
        if first_content != second_content:
            raise FrameworkEvidenceError(
                f"framework artifact is not byte-reproducible: {relative_path}"
            )
        digests[relative_path] = sha256_bytes(first_content)
    return digests
