from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

REQUIRED_CAPABILITIES = frozenset(
    {
        "attachments",
        "audit",
        "body_conversion",
        "classification",
        "deletion_signal",
        "entitlements",
        "incremental_changes",
        "rate_limits",
        "records_controls",
        "residency",
        "sandbox",
        "stable_identity",
        "version_identity",
    }
)


class SourceKind(StrEnum):
    CONFLUENCE = "confluence"
    SHAREPOINT = "sharepoint"
    INTERNAL_PLATFORM = "internal-platform"
    OTHER = "other"


class EvidenceState(StrEnum):
    UNKNOWN = "unknown"
    EVIDENCED = "evidenced"
    GAP = "gap"


class DiscoveryOwners(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    product: str = Field(min_length=1)
    content: str = Field(min_length=1)
    identity_access: str = Field(min_length=1)
    records_privacy: str = Field(min_length=1)
    engineering: str = Field(min_length=1)


class CollectionScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    collection_ref: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    owner_role: str = Field(min_length=1)
    maximum_classification: Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"]
    residency_regions: tuple[str, ...] = Field(min_length=1)
    estimated_items: int = Field(ge=0)


class CapabilityEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    state: EvidenceState
    evidence_refs: tuple[str, ...] = ()
    notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_evidence_when_claimed(self) -> CapabilityEvidence:
        if self.state == EvidenceState.EVIDENCED and not self.evidence_refs:
            raise ValueError("evidenced capabilities require at least one evidence reference")
        return self


class OpenDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    decision_id: str = Field(pattern=r"^DISC-[0-9]{3}$")
    question: str = Field(min_length=1)
    owner_role: str = Field(min_length=1)
    blocking: bool
    due_by: date | None = None


class SourceDiscoveryProfile(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "$id": "https://schemas.verity-kf.example.invalid/okf/source-discovery-v1.schema.json",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        },
    )

    schema_version: Literal["1.0"] = "1.0"
    discovery_status: Literal["draft", "source-owner-review", "approved"]
    source_system: str = Field(min_length=1)
    source_kind: SourceKind
    product_version: str = Field(min_length=1)
    owners: DiscoveryOwners
    collections: tuple[CollectionScope, ...] = Field(min_length=1)
    capabilities: dict[str, CapabilityEvidence]
    open_decisions: tuple[OpenDecision, ...]
    credentials_in_document: Literal[False] = False

    @model_validator(mode="after")
    def require_capability_inventory_and_closed_approval(self) -> SourceDiscoveryProfile:
        capability_names = set(self.capabilities)
        if missing := sorted(REQUIRED_CAPABILITIES - capability_names):
            raise ValueError(f"required discovery capabilities are missing: {missing}")
        if extra := sorted(capability_names - REQUIRED_CAPABILITIES):
            raise ValueError(f"unknown discovery capabilities must be versioned first: {extra}")
        if self.discovery_status == "approved":
            unresolved = [
                name
                for name, capability in self.capabilities.items()
                if capability.state != EvidenceState.EVIDENCED
            ]
            blocking = [
                decision.decision_id for decision in self.open_decisions if decision.blocking
            ]
            if unresolved or blocking:
                raise ValueError(
                    "approved discovery requires all capabilities evidenced "
                    "and no blocking decisions"
                )
        return self
