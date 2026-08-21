from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from verity_kf.evaluation import (
    CaseObservation,
    EvaluationBenchmark,
    EvaluationRun,
    score_evaluation,
)

PROJECT_ROOT = Path(__file__).parents[1]
DIGEST = f"sha256:{'e' * 64}"


def _benchmark() -> EvaluationBenchmark:
    loaded = yaml.safe_load(
        (PROJECT_ROOT / "profiles/pilot-benchmark.example.yaml").read_text(encoding="utf-8")
    )
    return EvaluationBenchmark.model_validate(loaded)


def _observation(
    case_id: str,
    *,
    retrieved: tuple[str, ...] = (),
    cited: tuple[str, ...] = (),
    refused: bool = False,
    human_review: bool = True,
) -> CaseObservation:
    review = (
        {"human_correctness": 5, "human_completeness": 4, "reviewer_role": "role:reviewer"}
        if human_review
        else {}
    )
    return CaseObservation(
        case_id=case_id,
        release_digest=DIGEST,
        retrieved_concept_uids=retrieved,
        cited_concept_uids=cited,
        refused=refused,
        latency_ms=500,
        **review,
    )


def test_deterministic_score_covers_citations_refusal_entitlement_latency_and_review() -> None:
    run = EvaluationRun(
        run_id="synthetic-run-1",
        consumer_id="reference-serving",
        observations=(
            _observation(
                "EVAL-001",
                retrieved=("kb:service:enterprise-identity",),
                cited=("kb:service:enterprise-identity",),
            ),
            _observation(
                "EVAL-002",
                retrieved=("kb:runbook:identity-service-degradation",),
                cited=("kb:runbook:identity-service-degradation",),
            ),
            _observation("EVAL-003", refused=True),
            _observation("EVAL-004", refused=True),
        ),
    )

    report = score_evaluation(_benchmark(), run)

    assert report.release_digests == (DIGEST,)
    assert report.mean_citation_recall == 1
    assert report.mean_citation_precision == 1
    assert report.mean_retrieval_recall == 1
    assert report.behavior_pass_rate == 1
    assert report.entitlement_pass_rate == 1
    assert report.latency_pass_rate == 1
    assert report.human_review_completion_rate == 1


def test_forbidden_concept_is_an_entitlement_failure_even_without_a_citation() -> None:
    observations = [
        _observation("EVAL-001", retrieved=("kb:service:enterprise-identity",)),
        _observation("EVAL-002", retrieved=("kb:runbook:identity-service-degradation",)),
        _observation("EVAL-003", refused=True),
        _observation(
            "EVAL-004",
            retrieved=("kb:policy:change-management",),
            refused=False,
        ),
    ]

    report = score_evaluation(
        _benchmark(),
        EvaluationRun(run_id="leak-run", consumer_id="reference", observations=observations),
    )

    entitlement_case = next(score for score in report.case_scores if score.case_id == "EVAL-004")
    assert entitlement_case.entitlement_pass is False
    assert entitlement_case.behavior_pass is False


def test_run_must_exactly_cover_benchmark_without_duplicates() -> None:
    repeated = _observation("EVAL-001")
    run = EvaluationRun(
        run_id="invalid-run",
        consumer_id="reference",
        observations=(repeated, repeated),
    )

    with pytest.raises(ValueError, match="duplicate"):
        score_evaluation(_benchmark(), run)


def test_committed_benchmark_schema_matches_model() -> None:
    committed = json.loads(
        (PROJECT_ROOT / "schemas/pilot-benchmark-v1.schema.json").read_text(encoding="utf-8")
    )

    assert committed == EvaluationBenchmark.model_json_schema()
