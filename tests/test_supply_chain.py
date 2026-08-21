from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from verity_kf.profile import load_profile
from verity_kf.release import RELEASE_MEDIA_TYPE, build_release
from verity_kf.supply_chain import (
    OciTarget,
    SignatureVerificationPolicy,
    SupplyChainError,
    build_supply_chain_plan,
    cosign_sign_command,
    cosign_verify_command,
    oras_push_command,
    parse_oras_push_output,
)

PROJECT_ROOT = Path(__file__).parents[1]


def _artifact():
    return build_release(
        PROJECT_ROOT / "examples/pilot-bundle",
        load_profile(PROJECT_ROOT / "profiles/verity-kf-pilot.yaml"),
        bundle_id="verity-kf-pilot",
        release_id="2026.08.21.1",
        source_commit="a" * 40,
        created_at=datetime(2026, 8, 21, tzinfo=UTC),
    )


def test_oras_push_command_uses_typed_layer_and_no_credentials() -> None:
    target = OciTarget(repository="registry.example.invalid/okf/pilot", tag="2026.08.21.1")
    command = oras_push_command(Path("release.tar.gz"), target, _artifact())

    assert command[:3] == ("oras", "push", "--no-tty")
    assert RELEASE_MEDIA_TYPE in command
    assert "release.tar.gz:application/vnd.verity.kf.release.layer.v1+tar+gzip" in command
    assert "--username" not in command and "--password" not in command
    annotation_pairs = [
        command[index + 1] for index, value in enumerate(command) if value == "--annotation"
    ]
    assert annotation_pairs == sorted(annotation_pairs)


def test_oras_output_must_return_expected_repository_digest_and_type() -> None:
    target = OciTarget(repository="registry.example.invalid/okf/pilot", tag="candidate")
    digest = "b" * 64
    output = json.dumps(
        {
            "artifactType": RELEASE_MEDIA_TYPE,
            "digest": f"sha256:{digest}",
            "reference": f"{target.repository}@sha256:{digest}",
        }
    )

    descriptor = parse_oras_push_output(output, target)

    assert descriptor.digest == f"sha256:{digest}"


def test_cosign_commands_require_digest_and_explicit_verification_identity() -> None:
    reference = f"registry.example.invalid/okf/pilot@sha256:{'c' * 64}"
    policy = SignatureVerificationPolicy(
        certificate_identity="okf-release@example.invalid",
        certificate_oidc_issuer="https://issuer.example.invalid",
    )

    assert cosign_sign_command(reference) == ("cosign", "sign", "--yes", reference)
    verify = cosign_verify_command(reference, policy)
    assert "--certificate-identity" in verify
    assert "--certificate-oidc-issuer" in verify
    with pytest.raises(SupplyChainError, match="immutable OCI"):
        cosign_sign_command("registry.example.invalid/okf/pilot:mutable")


def test_key_verification_mode_is_mutually_exclusive() -> None:
    with pytest.raises(ValidationError, match="select either"):
        SignatureVerificationPolicy(
            key_ref="awskms:///example",
            certificate_identity="identity",
            certificate_oidc_issuer="issuer",
        )


def test_supply_chain_plan_never_promotes_or_signs_by_tag() -> None:
    artifact = _artifact()
    target = OciTarget(repository="registry.example.invalid/okf/pilot", tag="candidate")
    policy = SignatureVerificationPolicy(key_ref="awskms:///alias/okf-release")
    digest = "d" * 64

    plan = build_supply_chain_plan(
        Path("release.tar.gz"),
        target,
        artifact,
        registry_manifest_digest=digest,
        signing_key_ref="awskms:///alias/okf-release",
        verification_policy=policy,
    )

    immutable_reference = f"{target.repository}@sha256:{digest}"
    assert plan.cosign_sign[-1] == immutable_reference
    assert plan.cosign_verify[-1] == immutable_reference
    assert plan.expected_archive_sha256 == artifact.archive_sha256


@pytest.mark.parametrize(
    ("repository", "tag"),
    [
        ("https://registry.example.invalid/repo", "tag"),
        ("Registry.example.invalid/repo", "tag"),
        ("registry.example.invalid/../repo", "tag"),
        ("registry.example.invalid/repo", "bad tag"),
    ],
)
def test_oci_target_rejects_unsafe_or_nonportable_values(repository: str, tag: str) -> None:
    with pytest.raises(ValidationError):
        OciTarget(repository=repository, tag=tag)
