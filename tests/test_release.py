from __future__ import annotations

import gzip
import io
import json
import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from xyz_okf.cli import app
from xyz_okf.profile import load_profile
from xyz_okf.release import (
    MANIFEST_PATH,
    ReleaseBuildError,
    ReleaseManifest,
    build_release,
    verify_release,
)

PROJECT_ROOT = Path(__file__).parents[1]
PROFILE = load_profile(PROJECT_ROOT / "profiles/xyz-bank-pilot.yaml")
BUNDLE = PROJECT_ROOT / "examples/pilot-bundle"
CREATED_AT = datetime(2026, 8, 21, tzinfo=UTC)
SOURCE_COMMIT = "a" * 40
RUNNER = CliRunner()


def _build(**overrides: object):
    values: dict[str, object] = {
        "bundle_id": "xyz-bank-pilot",
        "release_id": "2026.08.21.1",
        "source_commit": SOURCE_COMMIT,
        "created_at": CREATED_AT,
    }
    values.update(overrides)
    return build_release(BUNDLE, PROFILE, **values)  # type: ignore[arg-type]


def test_release_build_is_byte_reproducible_and_verifiable() -> None:
    first = _build()
    second = _build()

    assert first.archive_bytes == second.archive_bytes
    assert first.archive_sha256 == second.archive_sha256
    assert first.manifest_bytes == second.manifest_bytes
    verified = verify_release(first.archive_bytes)
    assert verified.archive_sha256 == first.archive_sha256
    assert verified.manifest == first.manifest


def test_manifest_captures_profile_identity_acl_classification_and_prior_release() -> None:
    prior_digest = "b" * 64
    artifact = _build(prior_release_digest=prior_digest)
    concepts = [entry for entry in artifact.manifest.files if entry.concept_uid is not None]

    assert artifact.manifest.prior_release_digest == prior_digest
    assert artifact.manifest.profile.profile_id == "xyz-bank-okf"
    assert artifact.manifest.bundle_classification == "INTERNAL"
    assert len(artifact.manifest.files) == 4
    assert len(concepts) == 3
    assert all(entry.acl_ref for entry in concepts)
    assert all(entry.canonical_sha256 for entry in concepts)
    assert all(entry.source_count == 1 for entry in concepts)
    assert all(entry.verified_count == 1 for entry in concepts)
    assert all(entry.status == "stable" and entry.stale_after for entry in concepts)
    assert [entry.path for entry in artifact.manifest.files] == sorted(
        entry.path for entry in artifact.manifest.files
    )


def test_archive_metadata_and_member_order_are_normalized() -> None:
    artifact = _build()
    with tarfile.open(
        fileobj=io.BytesIO(gzip.decompress(artifact.archive_bytes)), mode="r:"
    ) as archive:
        members = archive.getmembers()

    assert [member.name for member in members] == sorted(member.name for member in members)
    assert MANIFEST_PATH in {member.name for member in members}
    assert all(member.mtime == 0 for member in members)
    assert all(member.uid == 0 and member.gid == 0 for member in members)
    assert all(member.mode == 0o644 for member in members)


def test_invalid_bundle_is_never_packaged(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "index.md").write_text(
        '---\nokf_version: "0.2"\n---\n\n# Invalid\n', encoding="utf-8"
    )
    (bundle / "concept.md").write_text("---\ntype: Reference\n---\n", encoding="utf-8")

    with pytest.raises(ReleaseBuildError, match="bundle validation failed"):
        build_release(
            bundle,
            PROFILE,
            bundle_id="invalid-bundle",
            release_id="invalid-release",
            source_commit=SOURCE_COMMIT,
            created_at=CREATED_AT,
        )


def test_bundle_symlink_is_rejected(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLE, bundle)
    outside = tmp_path / "outside.txt"
    outside.write_text("not bundle content\n", encoding="utf-8")
    (bundle / "linked.txt").symlink_to(outside)

    with pytest.raises(ReleaseBuildError, match="symlinks are not permitted"):
        build_release(
            bundle,
            PROFILE,
            bundle_id="symlink-bundle",
            release_id="symlink-release",
            source_commit=SOURCE_COMMIT,
            created_at=CREATED_AT,
        )


def test_tampered_archive_fails_verification() -> None:
    archive = bytearray(_build().archive_bytes)
    archive[len(archive) // 2] ^= 1

    with pytest.raises((ReleaseBuildError, OSError, EOFError)):
        verify_release(bytes(archive))


def test_verification_enforces_uncompressed_size_limit() -> None:
    with pytest.raises(ReleaseBuildError, match="uncompressed size limit"):
        verify_release(_build().archive_bytes, max_uncompressed_bytes=1)


def test_committed_release_manifest_schema_matches_model() -> None:
    committed = json.loads(
        (PROJECT_ROOT / "schemas/release-manifest-v1.schema.json").read_text(encoding="utf-8")
    )

    assert committed == ReleaseManifest.model_json_schema()


def test_release_cli_builds_and_verifies(tmp_path: Path) -> None:
    build = RUNNER.invoke(
        app,
        [
            "build-release",
            str(BUNDLE),
            "--profile",
            str(PROJECT_ROOT / "profiles/xyz-bank-pilot.yaml"),
            "--bundle-id",
            "xyz-bank-pilot",
            "--release-id",
            "2026.08.21.1",
            "--source-commit",
            SOURCE_COMMIT,
            "--created-at",
            "2026-08-21T00:00:00Z",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert build.exit_code == 0, build.output
    payload = json.loads(build.output)
    archive = tmp_path / "2026.08.21.1.tar.gz"
    assert payload["archive_sha256"]
    assert archive.is_file()

    verify = RUNNER.invoke(app, ["verify-release", str(archive)])
    assert verify.exit_code == 0, verify.output
    assert json.loads(verify.output)["valid"] is True
