from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from verity_kf.framework_evidence import (
    FRAMEWORK_EVIDENCE_NAME,
    FRAMEWORK_SBOM_NAME,
    REQUIRED_WHEEL_CONTRACTS,
    FrameworkBuildEvidence,
    FrameworkEvidenceError,
    build_framework_evidence,
    compare_framework_evidence_directories,
    framework_evidence_bytes,
    normalize_cyclonedx_sbom,
    verify_framework_evidence_directory,
    verify_framework_wheel,
)

PROJECT_ROOT = Path(__file__).parents[1]
LOCK_SHA256 = "a" * 64


def _raw_sbom(*, serial: str = "urn:uuid:random", timestamp: str = "now") -> dict[str, object]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": serial,
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "tools": [{"name": "uv", "version": "0.11.7"}],
            "component": {
                "type": "library",
                "bom-ref": "verity-knowledge-fabric@0.2.0",
                "name": "verity-knowledge-fabric",
                "version": "0.2.0",
                "properties": [{"name": "uv:package:is_project_root", "value": "true"}],
            },
        },
        "components": [
            {"type": "library", "bom-ref": "b@2", "name": "b", "version": "2"},
            {"type": "library", "bom-ref": "a@1", "name": "a", "version": "1"},
        ],
        "dependencies": [
            {"ref": "b@2", "dependsOn": []},
            {"ref": "a@1", "dependsOn": ["b@2"]},
        ],
    }


def _normalize(payload: dict[str, object], lock_sha256: str = LOCK_SHA256) -> bytes:
    return normalize_cyclonedx_sbom(
        payload,
        package_name="verity-knowledge-fabric",
        package_version="0.2.0",
        uv_lock_sha256=lock_sha256,
    )


def _write_wheel(path: Path, members: set[str]) -> None:
    with zipfile.ZipFile(path, "w") as wheel:
        for member in sorted(members):
            wheel.writestr(member, b"contract\n")


def _write_valid_evidence(
    root: Path, *, source_content: bytes = b"source distribution"
) -> FrameworkBuildEvidence:
    root.mkdir()
    wheel = root / "verity_knowledge_fabric-0.2.0-py3-none-any.whl"
    source = root / "verity_knowledge_fabric-0.2.0.tar.gz"
    sbom = root / FRAMEWORK_SBOM_NAME
    _write_wheel(wheel, set(REQUIRED_WHEEL_CONTRACTS) | {"verity_kf/__init__.py"})
    source.write_bytes(source_content)
    sbom.write_bytes(_normalize(_raw_sbom()))
    evidence = build_framework_evidence(
        [wheel, source, sbom],
        artifact_root=root,
        package_version="0.2.0",
        source_commit="c" * 40,
        created_at=datetime(2026, 8, 21, tzinfo=UTC),
        python_version="3.13.7",
        uv_version="0.11.7",
        uv_lock_sha256=LOCK_SHA256,
    )
    (root / FRAMEWORK_EVIDENCE_NAME).write_bytes(framework_evidence_bytes(evidence))
    return evidence


def test_cyclonedx_normalization_is_deterministic_and_binds_lock() -> None:
    first = _normalize(_raw_sbom(serial="urn:uuid:first", timestamp="first"))
    second = _normalize(_raw_sbom(serial="urn:uuid:second", timestamp="second"))

    assert first == second
    payload = json.loads(first)
    assert "timestamp" not in payload["metadata"]
    assert payload["components"][0]["name"] == "a"
    assert payload["dependencies"][0]["ref"] == "a@1"
    assert {
        "name": "verity-knowledge-fabric:uv-lock-sha256",
        "value": LOCK_SHA256,
    } in payload["metadata"]["component"]["properties"]
    assert _normalize(_raw_sbom(), "b" * 64) != first


def test_cyclonedx_normalization_rejects_wrong_format_or_root() -> None:
    wrong_format = _raw_sbom()
    wrong_format["specVersion"] = "1.6"
    with pytest.raises(FrameworkEvidenceError, match=r"CycloneDX 1\.5"):
        _normalize(wrong_format)

    wrong_root = _raw_sbom()
    metadata = wrong_root["metadata"]
    assert isinstance(metadata, dict)
    component = metadata["component"]
    assert isinstance(component, dict)
    component["name"] = "another-package"
    with pytest.raises(FrameworkEvidenceError, match="root component"):
        _normalize(wrong_root)


def test_framework_evidence_hashes_and_sorts_artifacts(tmp_path: Path) -> None:
    wheel = tmp_path / "verity_knowledge_fabric-0.2.0-py3-none-any.whl"
    source = tmp_path / "verity_knowledge_fabric-0.2.0.tar.gz"
    sbom = tmp_path / FRAMEWORK_SBOM_NAME
    wheel.write_bytes(b"wheel")
    source.write_bytes(b"source")
    sbom.write_bytes(b"sbom")

    evidence = build_framework_evidence(
        [wheel, source, sbom],
        artifact_root=tmp_path,
        package_version="0.2.0",
        source_commit="c" * 40,
        created_at=datetime(2026, 8, 21, tzinfo=UTC),
        python_version="3.13.7",
        uv_version="0.11.7",
        uv_lock_sha256=LOCK_SHA256,
    )

    assert [artifact.path for artifact in evidence.artifacts] == sorted(
        artifact.path for artifact in evidence.artifacts
    )
    assert all(len(artifact.sha256) == 64 for artifact in evidence.artifacts)
    assert framework_evidence_bytes(evidence) == framework_evidence_bytes(evidence)


def test_framework_evidence_rejects_outside_and_symlink_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "dist"
    root.mkdir()
    outside = tmp_path / "verity_knowledge_fabric-0.2.0-py3-none-any.whl"
    outside.write_bytes(b"wheel")
    symlink = root / "verity_knowledge_fabric-0.2.0-py3-none-any.whl"
    symlink.symlink_to(outside)
    common = {
        "artifact_root": root,
        "package_version": "0.2.0",
        "source_commit": "c" * 40,
        "created_at": datetime(2026, 8, 21, tzinfo=UTC),
        "python_version": "3.13.7",
        "uv_version": "0.11.7",
        "uv_lock_sha256": LOCK_SHA256,
    }

    with pytest.raises(FrameworkEvidenceError, match="outside artifact_root"):
        build_framework_evidence([outside], **common)  # type: ignore[arg-type]
    with pytest.raises(FrameworkEvidenceError, match="regular file"):
        build_framework_evidence([symlink], **common)  # type: ignore[arg-type]


def test_framework_evidence_model_rejects_unsorted_artifacts() -> None:
    with pytest.raises(ValidationError, match="sorted by path"):
        FrameworkBuildEvidence.model_validate(
            {
                "package_version": "0.2.0",
                "source_commit": "c" * 40,
                "created_at": "2026-08-21T00:00:00Z",
                "python_version": "3.13.7",
                "uv_version": "0.11.7",
                "uv_lock_sha256": LOCK_SHA256,
                "artifacts": [
                    {
                        "path": name,
                        "size": 1,
                        "media_type": "application/octet-stream",
                        "sha256": "d" * 64,
                    }
                    for name in ["z.whl", "a.whl", "m.whl"]
                ],
            }
        )


def test_framework_wheel_requires_contracts_and_rejects_unsafe_members(tmp_path: Path) -> None:
    valid = tmp_path / "valid.whl"
    _write_wheel(valid, set(REQUIRED_WHEEL_CONTRACTS) | {"verity_kf/__init__.py"})
    names = verify_framework_wheel(valid)
    assert REQUIRED_WHEEL_CONTRACTS.issubset(names)

    missing = tmp_path / "missing.whl"
    _write_wheel(missing, {"verity_kf/__init__.py"})
    with pytest.raises(FrameworkEvidenceError, match="missing runtime contracts"):
        verify_framework_wheel(missing)

    unsafe = tmp_path / "unsafe.whl"
    _write_wheel(unsafe, {"../outside.txt"})
    with pytest.raises(FrameworkEvidenceError, match="unsafe artifact path"):
        verify_framework_wheel(unsafe, required_contracts=())


def test_committed_framework_evidence_schema_matches_model() -> None:
    committed = json.loads(
        (PROJECT_ROOT / "schemas/framework-build-evidence-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert committed == FrameworkBuildEvidence.model_json_schema()


def test_framework_evidence_directory_verifies_exact_inventory_and_expectations(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evidence"
    expected = _write_valid_evidence(root)

    verified = verify_framework_evidence_directory(
        root,
        expected_source_commit="c" * 40,
        expected_uv_lock_sha256=LOCK_SHA256,
        expected_evidence_sha256=hashlib.sha256(
            (root / FRAMEWORK_EVIDENCE_NAME).read_bytes()
        ).hexdigest(),
    )
    assert verified == expected

    with pytest.raises(FrameworkEvidenceError, match="source commit"):
        verify_framework_evidence_directory(root, expected_source_commit="d" * 40)
    with pytest.raises(FrameworkEvidenceError, match="lock digest"):
        verify_framework_evidence_directory(root, expected_uv_lock_sha256="d" * 64)
    with pytest.raises(FrameworkEvidenceError, match="evidence digest"):
        verify_framework_evidence_directory(root, expected_evidence_sha256="d" * 64)


def test_framework_evidence_directory_rejects_tamper_and_unexpected_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evidence"
    _write_valid_evidence(root)
    wheel = root / "verity_knowledge_fabric-0.2.0-py3-none-any.whl"
    wheel.write_bytes(wheel.read_bytes() + b"tampered")

    with pytest.raises(FrameworkEvidenceError, match="digest/size mismatch"):
        verify_framework_evidence_directory(root)

    root = tmp_path / "unexpected"
    _write_valid_evidence(root)
    (root / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(FrameworkEvidenceError, match="inventory mismatch"):
        verify_framework_evidence_directory(root)


def test_framework_evidence_directory_rejects_noncanonical_manifest(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    evidence = _write_valid_evidence(root)
    (root / FRAMEWORK_EVIDENCE_NAME).write_text(
        json.dumps(evidence.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(FrameworkEvidenceError, match="canonically encoded"):
        verify_framework_evidence_directory(root)


def test_framework_build_comparison_requires_all_four_files_to_match(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_valid_evidence(first)
    shutil.copytree(first, second)

    digests = compare_framework_evidence_directories(
        first,
        second,
        expected_source_commit="c" * 40,
        expected_uv_lock_sha256=LOCK_SHA256,
    )
    assert set(digests) == {
        FRAMEWORK_EVIDENCE_NAME,
        FRAMEWORK_SBOM_NAME,
        "verity_knowledge_fabric-0.2.0-py3-none-any.whl",
        "verity_knowledge_fabric-0.2.0.tar.gz",
    }

    third = tmp_path / "third"
    _write_valid_evidence(third, source_content=b"different source distribution")
    with pytest.raises(FrameworkEvidenceError, match="documents differ"):
        compare_framework_evidence_directories(first, third)
