from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from enum import StrEnum

from opentelemetry import metrics, trace
from opentelemetry.metrics import Meter
from opentelemetry.trace import Span, Status, StatusCode, Tracer


class TelemetryOperation(StrEnum):
    SOURCE_SYNC = "source_sync"
    VALIDATION = "validation"
    RELEASE_BUILD = "release_build"
    RELEASE_ADMISSION = "release_admission"
    RELEASE_LIFECYCLE = "release_lifecycle"
    RETRIEVAL = "retrieval"


class TelemetryOutcome(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"
    FILTERED = "filtered"
    NOT_FOUND = "not_found"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    WITHDRAWN = "withdrawn"


def fingerprint(value: str) -> str:
    """Return a stable one-way identifier for potentially sensitive names."""

    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


class OkfTelemetry:
    """Vendor-neutral, content-minimized OKF traces and metrics.

    This library installs no SDK/exporter. A hosting application supplies the
    approved OpenTelemetry providers and applies environment filtering/export.
    """

    instrumentation_name = "xyz_okf"

    def __init__(self, *, tracer: Tracer | None = None, meter: Meter | None = None) -> None:
        self._tracer = tracer or trace.get_tracer(self.instrumentation_name)
        self._meter = meter or metrics.get_meter(self.instrumentation_name)
        self._authorization_decisions = self._meter.create_counter(
            "xyz.okf.authorization.decisions",
            unit="{decision}",
            description="Concept-level authorization decisions by controlled outcome",
        )
        self._retrieval_requests = self._meter.create_counter(
            "xyz.okf.retrieval.requests",
            unit="{request}",
            description="Release-aware retrieval requests without content attributes",
        )
        self._retrieval_duration = self._meter.create_histogram(
            "xyz.okf.retrieval.duration",
            unit="s",
            description="End-to-end authorized retrieval duration",
        )
        self._source_lag = self._meter.create_histogram(
            "xyz.okf.source.lag",
            unit="s",
            description="Elapsed time between source modification and producer observation",
        )
        self._validation_issues = self._meter.create_counter(
            "xyz.okf.validation.issues",
            unit="{issue}",
            description="Validation issues by stable code and severity",
        )
        self._release_outcomes = self._meter.create_counter(
            "xyz.okf.release.outcomes",
            unit="{release}",
            description="Release build, admission, promotion, rollback, or withdrawal outcomes",
        )

    @contextmanager
    def span(
        self,
        operation: TelemetryOperation,
        *,
        action: str,
        release_ref: str | None = None,
        bundle_id: str | None = None,
        source_system: str | None = None,
        collection: str | None = None,
        concept_uid: str | None = None,
    ) -> Iterator[Span]:
        attributes: dict[str, str] = {
            "xyz.okf.operation": operation,
            "xyz.okf.action": action,
        }
        if release_ref is not None:
            attributes["xyz.okf.release.ref_hash"] = fingerprint(release_ref)
        if bundle_id is not None:
            attributes["xyz.okf.bundle.id_hash"] = fingerprint(bundle_id)
        if source_system is not None:
            attributes["xyz.okf.source.system"] = source_system
        if collection is not None:
            attributes["xyz.okf.source.collection_hash"] = fingerprint(collection)
        if concept_uid is not None:
            attributes["xyz.okf.concept.uid_hash"] = fingerprint(concept_uid)
        with self._tracer.start_as_current_span(
            f"xyz.okf.{operation}",
            attributes=attributes,
            record_exception=False,
            set_status_on_exception=False,
        ) as active_span:
            try:
                yield active_span
            except Exception as exc:
                # Exception messages and stack-local values may contain source content.
                active_span.set_attribute(
                    "error.type", f"{type(exc).__module__}.{type(exc).__qualname__}"
                )
                active_span.set_status(Status(StatusCode.ERROR))
                raise
            else:
                active_span.set_status(Status(StatusCode.OK))

    def record_authorization(
        self,
        *,
        action: str,
        allowed: bool,
        classification: str,
        reason_codes: Iterable[str],
    ) -> None:
        ordered_reasons = sorted(set(reason_codes))
        reason = ordered_reasons[0] if ordered_reasons else "UNSPECIFIED"
        self._authorization_decisions.add(
            1,
            {
                "xyz.okf.action": action,
                "xyz.okf.authorization.allowed": allowed,
                "xyz.okf.authorization.reason": reason,
                "xyz.okf.classification": classification,
            },
        )

    def record_retrieval(
        self,
        *,
        action: str,
        outcome: TelemetryOutcome,
        duration_seconds: float,
    ) -> None:
        if duration_seconds < 0:
            raise ValueError("duration_seconds must not be negative")
        attributes = {"xyz.okf.action": action, "xyz.okf.outcome": outcome}
        self._retrieval_requests.add(1, attributes)
        self._retrieval_duration.record(duration_seconds, attributes)

    def record_source_lag(self, *, source_system: str, lag_seconds: float) -> None:
        if lag_seconds < 0:
            raise ValueError("lag_seconds must not be negative")
        self._source_lag.record(
            lag_seconds,
            {"xyz.okf.source.system": source_system},
        )

    def record_validation_issue(self, *, code: str, severity: str) -> None:
        self._validation_issues.add(
            1,
            {"xyz.okf.validation.code": code, "xyz.okf.validation.severity": severity},
        )

    def record_release_outcome(self, *, action: str, outcome: TelemetryOutcome) -> None:
        self._release_outcomes.add(
            1,
            {"xyz.okf.action": action, "xyz.okf.outcome": outcome},
        )
