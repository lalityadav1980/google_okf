from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from verity_kf.release import Classification

_CLASSIFICATION_RANK: dict[Classification, int] = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONFIDENTIAL": 2,
    "RESTRICTED": 3,
}


class PrincipalType(StrEnum):
    HUMAN = "human"
    WORKLOAD = "workload"


class RetrievalAction(StrEnum):
    DISCOVER = "discover"
    SEARCH = "search"
    READ = "read"
    FOLLOW_LINK = "follow_link"


class AuthorizationReason(StrEnum):
    ALLOW = "ALLOW"
    ACL_NOT_FOUND = "ACL_NOT_FOUND"
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
    CLASSIFICATION_EXCEEDS_CLEARANCE = "CLASSIFICATION_EXCEEDS_CLEARANCE"
    PRINCIPAL_NOT_ENTITLED = "PRINCIPAL_NOT_ENTITLED"
    PRINCIPAL_TYPE_NOT_ALLOWED = "PRINCIPAL_TYPE_NOT_ALLOWED"


class PrincipalContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    subject: str = Field(min_length=1, pattern=r"^[^\s\x00-\x1f]+$")
    principal_type: PrincipalType
    groups: tuple[str, ...] = ()
    clearance: Classification

    @field_validator("groups")
    @classmethod
    def normalize_groups(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item or any(character.isspace() for character in item) for item in value):
            raise ValueError("groups must be non-empty identifiers without whitespace")
        return tuple(sorted(set(value)))


class ResourceContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    bundle_id: str = Field(min_length=1)
    release_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    concept_uid: str = Field(min_length=1)
    concept_path: str = Field(min_length=1)
    classification: Classification
    acl_ref: str = Field(min_length=1)
    action: RetrievalAction


class AuthorizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    principal: PrincipalContext
    resource: ResourceContext


class AuthorizationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed: bool
    decision_id: str = Field(pattern=r"^authz:[0-9a-f]{64}$")
    policy_version: str = Field(min_length=1)
    reason_codes: tuple[AuthorizationReason, ...]

    @model_validator(mode="after")
    def validate_reason_contract(self) -> AuthorizationDecision:
        if self.allowed and self.reason_codes != (AuthorizationReason.ALLOW,):
            raise ValueError("allowed decisions must contain only ALLOW")
        if not self.allowed and (
            not self.reason_codes or AuthorizationReason.ALLOW in self.reason_codes
        ):
            raise ValueError("denied decisions require one or more denial reasons")
        return self


class PolicyDecisionPoint(Protocol):
    def authorize(self, request: AuthorizationRequest) -> AuthorizationDecision: ...


class AclBinding(BaseModel):
    """Synthetic/local ACL rule used to exercise the portable PDP contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subjects: tuple[str, ...] = ()
    groups: tuple[str, ...] = ()
    principal_types: tuple[PrincipalType, ...] = (
        PrincipalType.HUMAN,
        PrincipalType.WORKLOAD,
    )
    actions: tuple[RetrievalAction, ...] = (
        RetrievalAction.DISCOVER,
        RetrievalAction.SEARCH,
        RetrievalAction.READ,
        RetrievalAction.FOLLOW_LINK,
    )

    @field_validator("subjects", "groups")
    @classmethod
    def normalize_identifiers(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item or any(character.isspace() for character in item) for item in value):
            raise ValueError("ACL identifiers must be non-empty and contain no whitespace")
        return tuple(sorted(set(value)))

    @field_validator("principal_types", "actions")
    @classmethod
    def normalize_enums[EnumT: StrEnum](cls, value: tuple[EnumT, ...]) -> tuple[EnumT, ...]:
        return tuple(sorted(set(value), key=str))

    @model_validator(mode="after")
    def require_entitlement_selector(self) -> AclBinding:
        if not self.subjects and not self.groups:
            raise ValueError("an ACL binding requires at least one exact subject or group")
        if not self.principal_types or not self.actions:
            raise ValueError("an ACL binding requires principal types and actions")
        return self


class ReferencePolicyDecisionPoint:
    """Deny-by-default evaluator for tests and local demonstrations.

    Production deployments replace this adapter with the approved enterprise PDP;
    they do not load local ACL bindings into the serving process.
    """

    def __init__(self, bindings: Mapping[str, AclBinding], *, policy_version: str) -> None:
        if not policy_version:
            raise ValueError("policy_version is required")
        self._bindings = dict(bindings)
        self._policy_version = policy_version

    def authorize(self, request: AuthorizationRequest) -> AuthorizationDecision:
        reasons: set[AuthorizationReason] = set()
        binding = self._bindings.get(request.resource.acl_ref)
        if binding is None:
            reasons.add(AuthorizationReason.ACL_NOT_FOUND)
        else:
            if request.principal.principal_type not in binding.principal_types:
                reasons.add(AuthorizationReason.PRINCIPAL_TYPE_NOT_ALLOWED)
            if request.resource.action not in binding.actions:
                reasons.add(AuthorizationReason.ACTION_NOT_ALLOWED)
            subject_match = request.principal.subject in binding.subjects
            group_match = bool(set(request.principal.groups).intersection(binding.groups))
            if not subject_match and not group_match:
                reasons.add(AuthorizationReason.PRINCIPAL_NOT_ENTITLED)

        if (
            _CLASSIFICATION_RANK[request.resource.classification]
            > _CLASSIFICATION_RANK[request.principal.clearance]
        ):
            reasons.add(AuthorizationReason.CLASSIFICATION_EXCEEDS_CLEARANCE)

        ordered_reasons = tuple(sorted(reasons, key=str)) or (AuthorizationReason.ALLOW,)
        allowed = ordered_reasons == (AuthorizationReason.ALLOW,)
        fingerprint_payload = {
            "allowed": allowed,
            "policy_version": self._policy_version,
            "principal": request.principal.model_dump(mode="json"),
            "reasons": ordered_reasons,
            "resource": request.resource.model_dump(mode="json"),
        }
        canonical = json.dumps(
            fingerprint_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return AuthorizationDecision(
            allowed=allowed,
            decision_id=f"authz:{hashlib.sha256(canonical).hexdigest()}",
            policy_version=self._policy_version,
            reason_codes=ordered_reasons,
        )
