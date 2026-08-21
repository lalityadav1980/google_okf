from __future__ import annotations

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from verity_kf.telemetry import (
    OkfTelemetry,
    TelemetryOperation,
    TelemetryOutcome,
    fingerprint,
)


def _telemetry() -> tuple[OkfTelemetry, InMemorySpanExporter, InMemoryMetricReader]:
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    telemetry = OkfTelemetry(
        tracer=tracer_provider.get_tracer("test"),
        meter=meter_provider.get_meter("test"),
    )
    return telemetry, span_exporter, metric_reader


def test_span_hashes_identifiers_and_never_records_exception_message_or_content() -> None:
    telemetry, exporter, _ = _telemetry()
    secret_values = {
        "release": "protected-sensitive-channel",
        "bundle": "sensitive-business-domain",
        "collection": "restricted-space-name",
        "concept": "kb:sensitive:concept",
        "exception": "source body must never enter telemetry",
    }

    with (
        pytest.raises(ValueError, match="source body"),
        telemetry.span(
            TelemetryOperation.RETRIEVAL,
            action="fetch_concept",
            release_ref=secret_values["release"],
            bundle_id=secret_values["bundle"],
            source_system="confluence",
            collection=secret_values["collection"],
            concept_uid=secret_values["concept"],
        ),
    ):
        raise ValueError(secret_values["exception"])

    span = exporter.get_finished_spans()[0]
    serialized = str(span.attributes)
    assert span.attributes["verity.kf.release.ref_hash"] == fingerprint(secret_values["release"])
    assert span.attributes["verity.kf.bundle.id_hash"] == fingerprint(secret_values["bundle"])
    assert span.attributes["verity.kf.source.collection_hash"] == fingerprint(
        secret_values["collection"]
    )
    assert span.attributes["verity.kf.concept.uid_hash"] == fingerprint(secret_values["concept"])
    assert all(value not in serialized for value in secret_values.values())
    assert span.attributes["error.type"] == "builtins.ValueError"
    assert span.events == ()


def test_metrics_use_bounded_content_free_attribute_sets() -> None:
    telemetry, _, reader = _telemetry()

    telemetry.record_authorization(
        action="read",
        allowed=False,
        classification="INTERNAL",
        reason_codes=("PRINCIPAL_NOT_ENTITLED",),
    )
    telemetry.record_retrieval(
        action="fetch_concept",
        outcome=TelemetryOutcome.DENIED,
        duration_seconds=0.015,
    )
    telemetry.record_source_lag(source_system="sharepoint", lag_seconds=12.5)
    telemetry.record_validation_issue(code="VKF-ACL-REF", severity="error")
    telemetry.record_release_outcome(action="admission", outcome=TelemetryOutcome.SUCCEEDED)

    metrics_data = reader.get_metrics_data()
    metrics = [
        metric
        for resource_metric in metrics_data.resource_metrics
        for scope_metric in resource_metric.scope_metrics
        for metric in scope_metric.metrics
    ]
    assert {metric.name for metric in metrics} == {
        "verity.kf.authorization.decisions",
        "verity.kf.release.outcomes",
        "verity.kf.retrieval.duration",
        "verity.kf.retrieval.requests",
        "verity.kf.source.lag",
        "verity.kf.validation.issues",
    }
    serialized = str(metrics_data)
    assert "query" not in serialized
    assert "body" not in serialized
    assert "principal" not in serialized
    assert "acl_ref" not in serialized


@pytest.mark.parametrize(
    ("method", "kwargs"),
    [
        ("record_retrieval", {"action": "search", "outcome": "failed", "duration_seconds": -1}),
        ("record_source_lag", {"source_system": "synthetic", "lag_seconds": -1}),
    ],
)
def test_negative_measurements_are_rejected(method: str, kwargs: dict[str, object]) -> None:
    telemetry, _, _ = _telemetry()

    with pytest.raises(ValueError, match="must not be negative"):
        getattr(telemetry, method)(**kwargs)
