from __future__ import annotations

from enum import StrEnum
from statistics import fmean
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskCategory(StrEnum):
    KNOWLEDGE_DISCOVERY = "knowledge-discovery"
    POLICY_LOOKUP = "policy-lookup"
    PROCEDURE_NAVIGATION = "procedure-navigation"
    SERVICE_CONTEXT = "service-context"
    ARCHITECTURE_CONTEXT = "architecture-context"
    INSUFFICIENT_KNOWLEDGE = "insufficient-knowledge"
    ENTITLEMENT_BOUNDARY = "entitlement-boundary"


class ExpectedBehavior(StrEnum):
    ANSWER = "answer"
    REFUSE = "refuse"


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    case_id: str = Field(pattern=r"^EVAL-[0-9]{3}$")
    category: TaskCategory
    task: str = Field(min_length=1)
    principal_fixture: str = Field(min_length=1)
    expected_behavior: ExpectedBehavior
    expected_concept_uids: tuple[str, ...] = ()
    forbidden_concept_uids: tuple[str, ...] = ()
    maximum_latency_ms: int = Field(gt=0)
    human_review_required: bool = True

    @model_validator(mode="after")
    def validate_expectations(self) -> BenchmarkCase:
        expected = set(self.expected_concept_uids)
        forbidden = set(self.forbidden_concept_uids)
        if len(expected) != len(self.expected_concept_uids):
            raise ValueError("expected concept UIDs must be unique")
        if len(forbidden) != len(self.forbidden_concept_uids):
            raise ValueError("forbidden concept UIDs must be unique")
        if expected.intersection(forbidden):
            raise ValueError("a concept cannot be both expected and forbidden")
        if self.expected_behavior == ExpectedBehavior.ANSWER and not expected:
            raise ValueError("answer cases require at least one expected concept UID")
        return self


class EvaluationBenchmark(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "$id": "https://schemas.xyz-bank.example.invalid/okf/pilot-benchmark-v1.schema.json",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        },
    )

    schema_version: Literal["1.0"] = "1.0"
    benchmark_id: str = Field(min_length=1)
    benchmark_version: str = Field(min_length=1)
    status: Literal["draft", "approved"]
    outcome_owner_role: str = Field(min_length=1)
    cases: tuple[BenchmarkCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_case_ids_and_coverage(self) -> EvaluationBenchmark:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("benchmark case IDs must be unique")
        categories = {case.category for case in self.cases}
        if self.status == "approved" and (
            TaskCategory.INSUFFICIENT_KNOWLEDGE not in categories
            or TaskCategory.ENTITLEMENT_BOUNDARY not in categories
        ):
            raise ValueError(
                "approved benchmarks require insufficient-knowledge and entitlement cases"
            )
        return self


class CaseObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    case_id: str = Field(pattern=r"^EVAL-[0-9]{3}$")
    release_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    retrieved_concept_uids: tuple[str, ...] = ()
    cited_concept_uids: tuple[str, ...] = ()
    refused: bool
    latency_ms: int = Field(ge=0)
    human_correctness: int | None = Field(default=None, ge=1, le=5)
    human_completeness: int | None = Field(default=None, ge=1, le=5)
    reviewer_role: str | None = None

    @model_validator(mode="after")
    def require_consistent_human_review(self) -> CaseObservation:
        scores = (self.human_correctness, self.human_completeness)
        if any(score is not None for score in scores) and (
            any(score is None for score in scores) or not self.reviewer_role
        ):
            raise ValueError("human review requires both scores and a reviewer role")
        return self


class EvaluationRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    schema_version: Literal["1.0"] = "1.0"
    run_id: str = Field(min_length=1)
    consumer_id: str = Field(min_length=1)
    observations: tuple[CaseObservation, ...] = Field(min_length=1)


class CaseScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    citation_recall: float = Field(ge=0, le=1)
    citation_precision: float = Field(ge=0, le=1)
    retrieval_recall: float = Field(ge=0, le=1)
    behavior_pass: bool
    entitlement_pass: bool
    latency_pass: bool
    human_review_complete: bool


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    benchmark_id: str
    benchmark_version: str
    run_id: str
    consumer_id: str
    release_digests: tuple[str, ...]
    case_scores: tuple[CaseScore, ...]
    mean_citation_recall: float = Field(ge=0, le=1)
    mean_citation_precision: float = Field(ge=0, le=1)
    mean_retrieval_recall: float = Field(ge=0, le=1)
    behavior_pass_rate: float = Field(ge=0, le=1)
    entitlement_pass_rate: float = Field(ge=0, le=1)
    latency_pass_rate: float = Field(ge=0, le=1)
    human_review_completion_rate: float = Field(ge=0, le=1)


def score_evaluation(
    benchmark: EvaluationBenchmark,
    run: EvaluationRun,
) -> EvaluationReport:
    observations = {observation.case_id: observation for observation in run.observations}
    if len(observations) != len(run.observations):
        raise ValueError("evaluation run contains duplicate case observations")
    expected_ids = {case.case_id for case in benchmark.cases}
    if set(observations) != expected_ids:
        raise ValueError(
            "evaluation observations must exactly cover benchmark cases; "
            f"missing={sorted(expected_ids - set(observations))}, "
            f"extra={sorted(set(observations) - expected_ids)}"
        )

    scores: list[CaseScore] = []
    for case in benchmark.cases:
        observation = observations[case.case_id]
        expected = set(case.expected_concept_uids)
        retrieved = set(observation.retrieved_concept_uids)
        cited = set(observation.cited_concept_uids)
        forbidden = set(case.forbidden_concept_uids)
        expected_count = len(expected)
        citation_recall = len(expected.intersection(cited)) / expected_count if expected else 1.0
        retrieval_recall = (
            len(expected.intersection(retrieved)) / expected_count if expected else 1.0
        )
        citation_precision = (
            len(expected.intersection(cited)) / len(cited)
            if cited
            else (1.0 if not expected else 0.0)
        )
        expected_refusal = case.expected_behavior == ExpectedBehavior.REFUSE
        human_complete = not case.human_review_required or (
            observation.human_correctness is not None
            and observation.human_completeness is not None
            and observation.reviewer_role is not None
        )
        scores.append(
            CaseScore(
                case_id=case.case_id,
                citation_recall=citation_recall,
                citation_precision=citation_precision,
                retrieval_recall=retrieval_recall,
                behavior_pass=observation.refused == expected_refusal,
                entitlement_pass=not forbidden.intersection(retrieved.union(cited)),
                latency_pass=observation.latency_ms <= case.maximum_latency_ms,
                human_review_complete=human_complete,
            )
        )

    return EvaluationReport(
        benchmark_id=benchmark.benchmark_id,
        benchmark_version=benchmark.benchmark_version,
        run_id=run.run_id,
        consumer_id=run.consumer_id,
        release_digests=tuple(sorted({item.release_digest for item in run.observations})),
        case_scores=tuple(scores),
        mean_citation_recall=fmean(score.citation_recall for score in scores),
        mean_citation_precision=fmean(score.citation_precision for score in scores),
        mean_retrieval_recall=fmean(score.retrieval_recall for score in scores),
        behavior_pass_rate=fmean(score.behavior_pass for score in scores),
        entitlement_pass_rate=fmean(score.entitlement_pass for score in scores),
        latency_pass_rate=fmean(score.latency_pass for score in scores),
        human_review_completion_rate=fmean(score.human_review_complete for score in scores),
    )
