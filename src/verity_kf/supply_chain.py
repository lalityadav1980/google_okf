from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verity_kf.release import RELEASE_MEDIA_TYPE, ReleaseArtifact, VerifiedRelease

RELEASE_LAYER_MEDIA_TYPE = "application/vnd.verity.kf.release.layer.v1+tar+gzip"
_TAG = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$")
_DIGEST_REFERENCE = re.compile(r"^([^@\s]+)@sha256:([0-9a-f]{64})$")
_ANNOTATION_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


class SupplyChainError(ValueError):
    """OCI or signature inputs/outputs violate the release supply-chain contract."""


class OciTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str = Field(min_length=3)
    tag: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_target(self) -> OciTarget:
        if (
            "://" in self.repository
            or "@" in self.repository
            or any(character.isspace() for character in self.repository)
            or self.repository != self.repository.lower()
            or "/" not in self.repository
        ):
            raise ValueError(
                "OCI repository must be lowercase host/path without scheme, digest, or whitespace"
            )
        if any(segment in {"", ".", ".."} for segment in self.repository.split("/")):
            raise ValueError("OCI repository contains an unsafe path segment")
        if not _TAG.fullmatch(self.tag):
            raise ValueError("OCI tag is not portable")
        return self

    @property
    def tagged_reference(self) -> str:
        return f"{self.repository}:{self.tag}"


class SignatureVerificationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key_ref: str | None = None
    certificate_identity: str | None = None
    certificate_oidc_issuer: str | None = None

    @model_validator(mode="after")
    def select_one_trust_mode(self) -> SignatureVerificationPolicy:
        has_key = self.key_ref is not None
        has_identity = self.certificate_identity is not None
        has_issuer = self.certificate_oidc_issuer is not None
        if has_key == (has_identity or has_issuer):
            raise ValueError("select either key_ref or certificate identity/issuer verification")
        if has_identity != has_issuer:
            raise ValueError("certificate identity and OIDC issuer must be supplied together")
        for value in (self.key_ref, self.certificate_identity, self.certificate_oidc_issuer):
            if value is not None and (
                not value or any(character in "\r\n\x00" for character in value)
            ):
                raise ValueError("signature policy values must not contain control characters")
        return self


@dataclass(frozen=True, slots=True)
class OciDescriptor:
    reference: str
    digest: str
    artifact_type: str


@dataclass(frozen=True, slots=True)
class SupplyChainPlan:
    oras_push: tuple[str, ...]
    cosign_sign: tuple[str, ...]
    cosign_verify: tuple[str, ...]
    expected_archive_sha256: str


def digest_reference(repository: str, digest: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise SupplyChainError("OCI manifest digest must be lowercase SHA-256")
    if "://" in repository or "@" in repository or any(value.isspace() for value in repository):
        raise SupplyChainError("OCI repository is invalid")
    return f"{repository}@sha256:{digest}"


def _validate_digest_reference(reference: str) -> None:
    if not _DIGEST_REFERENCE.fullmatch(reference):
        raise SupplyChainError("operation requires an immutable OCI sha256 digest reference")


def _annotation_arguments(annotations: dict[str, str]) -> list[str]:
    arguments: list[str] = []
    for key, value in sorted(annotations.items()):
        if not _ANNOTATION_KEY.fullmatch(key):
            raise SupplyChainError(f"invalid OCI annotation key: {key}")
        if any(character in "\r\n\x00" for character in value):
            raise SupplyChainError(f"invalid OCI annotation value for: {key}")
        arguments.extend(("--annotation", f"{key}={value}"))
    return arguments


def oras_push_command(
    archive_path: Path,
    target: OciTarget,
    release: ReleaseArtifact | VerifiedRelease,
) -> tuple[str, ...]:
    manifest = release.manifest
    archive_sha256 = release.archive_sha256
    annotations = {
        "org.opencontainers.image.created": manifest.created_at.isoformat(),
        "org.opencontainers.image.revision": manifest.source_commit,
        "org.opencontainers.image.title": manifest.release_id,
        "verity.kf.archive.sha256": archive_sha256,
        "verity.kf.bundle.id": manifest.bundle_id,
        "verity.kf.profile": f"{manifest.profile.profile_id}/{manifest.profile.profile_version}",
    }
    return (
        "oras",
        "push",
        "--no-tty",
        "--artifact-type",
        RELEASE_MEDIA_TYPE,
        *_annotation_arguments(annotations),
        "--format",
        "json",
        target.tagged_reference,
        f"{archive_path}:{RELEASE_LAYER_MEDIA_TYPE}",
    )


def parse_oras_push_output(output: str, target: OciTarget) -> OciDescriptor:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise SupplyChainError("ORAS output is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise SupplyChainError("ORAS output must be a JSON object")
    digest = payload.get("digest")
    reference = payload.get("reference")
    artifact_type = payload.get("artifactType")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise SupplyChainError("ORAS output has no valid manifest digest")
    expected_reference = f"{target.repository}@{digest}"
    if reference != expected_reference:
        raise SupplyChainError("ORAS digest reference does not match the target repository")
    if artifact_type != RELEASE_MEDIA_TYPE:
        raise SupplyChainError("ORAS artifact type does not match the OKF release media type")
    return OciDescriptor(reference=reference, digest=digest, artifact_type=artifact_type)


def cosign_sign_command(reference: str, *, key_ref: str | None = None) -> tuple[str, ...]:
    _validate_digest_reference(reference)
    command = ["cosign", "sign", "--yes"]
    if key_ref is not None:
        if not key_ref or any(character in "\r\n\x00" for character in key_ref):
            raise SupplyChainError("Cosign key reference is invalid")
        command.extend(("--key", key_ref))
    command.append(reference)
    return tuple(command)


def cosign_verify_command(
    reference: str,
    policy: SignatureVerificationPolicy,
) -> tuple[str, ...]:
    _validate_digest_reference(reference)
    command = ["cosign", "verify"]
    if policy.key_ref is not None:
        command.extend(("--key", policy.key_ref))
    else:
        command.extend(("--certificate-identity", str(policy.certificate_identity)))
        command.extend(("--certificate-oidc-issuer", str(policy.certificate_oidc_issuer)))
    command.append(reference)
    return tuple(command)


def build_supply_chain_plan(
    archive_path: Path,
    target: OciTarget,
    release: ReleaseArtifact | VerifiedRelease,
    *,
    registry_manifest_digest: str,
    signing_key_ref: str | None,
    verification_policy: SignatureVerificationPolicy,
) -> SupplyChainPlan:
    reference = digest_reference(target.repository, registry_manifest_digest)
    return SupplyChainPlan(
        oras_push=oras_push_command(archive_path, target, release),
        cosign_sign=cosign_sign_command(reference, key_ref=signing_key_ref),
        cosign_verify=cosign_verify_command(reference, verification_policy),
        expected_archive_sha256=release.archive_sha256,
    )
