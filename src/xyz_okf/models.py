from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

_TOOL_ACTOR = re.compile(r"^[^\s/:]+(?:[-_.][^\s/:]+)*/[^\s/]+$")


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ActorEvent(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    by: str = Field(min_length=1)
    at: AwareDatetime

    @field_validator("by")
    @classmethod
    def validate_actor(cls, value: str) -> str:
        if value.startswith(("human:", "process:")) or _TOOL_ACTOR.fullmatch(value):
            return value
        raise ValueError("actor must use human:<id>, process:<id>, or <producer>/<version> syntax")


class Source(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    resource: str = Field(min_length=1)
    id: str | None = None
    title: str | None = None
    author: str | None = None
    usage_count: int | None = Field(default=None, ge=0)
    last_modified: AwareDatetime | None = None


class ConceptFrontmatter(BaseModel):
    """OKF v0.2 frontmatter with permissive producer extensions."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    type: str = Field(min_length=1)
    title: str | None = None
    description: str | None = None
    resource: str | None = None
    tags: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    generated: ActorEvent | None = None
    verified: list[ActorEvent] = Field(default_factory=list)
    status: Literal["draft", "stable", "deprecated"] | None = None
    stale_after: AwareDatetime | None = None

    @field_validator("verified", mode="before")
    @classmethod
    def accept_single_verification(cls, value: Any) -> Any:
        # OKF v0.2 consumers must accept a bare mapping as a one-element list.
        if isinstance(value, dict):
            return [value]
        return value


class ValidationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require_root_index: bool = True
    broken_internal_links: Severity = Severity.ERROR
    escaped_bundle_links: Severity = Severity.ERROR
    stale_concepts: Severity = Severity.WARNING
    unknown_types: Severity = Severity.ERROR
    verified_required_for_criticality: list[str] = Field(default_factory=list)


class ProfileDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    okf_version: str = Field(min_length=1)
    required_fields: list[str] = Field(default_factory=list)
    allowed_types: list[str] = Field(default_factory=list)
    enum_fields: dict[str, list[str]] = Field(default_factory=dict)
    allowed_relationship_types: list[str] = Field(default_factory=list)
    policy: ValidationPolicy = Field(default_factory=ValidationPolicy)


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Severity
    code: str
    message: str
    path: str
    concept_id: str | None = None
    field: str | None = None


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle: str
    profile_id: str
    profile_version: str
    checked_at: datetime
    documents_checked: int = 0
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(issue.severity == Severity.ERROR for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == Severity.WARNING for issue in self.issues)

    @property
    def info_count(self) -> int:
        return sum(issue.severity == Severity.INFO for issue in self.issues)

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0
