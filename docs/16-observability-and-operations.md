# Content-Minimized Observability and Operations

## 1. Status

The framework now exposes OpenTelemetry API instrumentation and instruments the
reference serving/authorization path. It intentionally installs no global SDK,
exporter, endpoint, credential, sampler, or vendor agent. The hosting
application owns those decisions and must use the approved XYZ Bank telemetry
platform.

Production completion remains blocked on the telemetry backend, data-handling
approval, service ownership, SLOs, residency, retention, alert routes, and live
publication/source integrations.

The reference uses OpenTelemetry Python API `>=1.44,<2`; its tests use the SDK
at the same range. OpenTelemetry's Python guidance distinguishes library use of
the API from application configuration of the SDK, and current Python traces
and metrics are stable:

- [OpenTelemetry Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/)
- [OpenTelemetry Python status](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/)

## 2. Data-minimization invariant

Telemetry must never contain:

- concept body, title, description, search query, snippet, prompt, or answer;
- source URL, page/document/space/site/library name, or raw collection ID;
- human/workload subject, group membership, token, cookie, or credential;
- raw concept UID, ACL reference, exception message, stack-local value, or user input;
- attachment name/content or YODA/RACK interaction content.

Potentially sensitive bundle, collection, channel/reference, and concept
identifiers are one-way SHA-256 fingerprints in spans. Metrics use bounded,
controlled dimensions only. Exceptions record the Python exception type and
error status; automatic exception events are disabled because messages may
contain source data.

OpenTelemetry explicitly warns that attributes can contain PII and that URL
telemetry can expose sensitive data; unknown URL/query content should be
redacted rather than guessed safe:

- [Semantic convention guidance for sensitive attributes](https://opentelemetry.io/docs/specs/semconv/how-to-write-conventions/)
- [URL semantic convention security guidance](https://opentelemetry.io/docs/specs/semconv/url/)

## 3. Trace contract

Low-cardinality span names use `xyz.okf.<operation>` for:

- `source_sync`;
- `validation`;
- `release_build`;
- `release_admission`;
- `release_lifecycle`; and
- `retrieval`.

Allowed span attributes are limited to controlled action/operation,
source-system adapter name, hashed collection/bundle/release-reference/concept
identity, and error type. The exact immutable registry/archive/manifest
digests, profile version, authorization decision ID/policy version, operation
ID, and consumer trace ID belong in the protected audit record. The telemetry
trace links to that record using an approved opaque audit correlation ID once
the bank defines it; it must not duplicate the complete audit payload.

## 4. Metric contract

| Instrument | Type/unit | Allowed dimensions | Intended SLI |
|---|---|---|---|
| `xyz.okf.source.lag` | Histogram, seconds | source system | Change-to-observation freshness |
| `xyz.okf.validation.issues` | Counter, issues | stable code, severity | Bundle/profile quality |
| `xyz.okf.release.outcomes` | Counter, releases | controlled action/outcome | Build/admit/promote/withdraw reliability |
| `xyz.okf.authorization.decisions` | Counter, decisions | action, allowed, controlled first reason, classification | Denial/error behavior without identity leakage |
| `xyz.okf.retrieval.requests` | Counter, requests | action, controlled outcome | Availability/error/denial rate |
| `xyz.okf.retrieval.duration` | Histogram, seconds | action, controlled outcome | Retrieval latency |

Index build duration/lag, citation coverage, connector retry/exhaustion,
checkpoint conflicts, archive/registry verification, cache behavior, and
approved cost/resource metrics are still required when those hosted components
exist. Cost telemetry must contain aggregate resource units, never request
content or user identity.

## 5. Proposed service objectives for pilot approval

These are placeholders to calibrate with owners and load tests, not production
commitments:

| Indicator | Pilot proposal | Measurement caveat |
|---|---|---|
| Unauthorized content exposure | Zero known events | Negative entitlement and penetration tests plus incident monitoring |
| Withdraw-to-deny | Less than 5 minutes | Must include channel, caches, indexes, and exact-digest serving |
| Protected release integrity | 100% verified/admitted | Registry, signature, archive, and OPA evidence required |
| Source freshness | Per-source percentile target | Starts at authoritative source modification time |
| Serving availability | Owner-defined | Excludes correctly denied/filtered/not-found requests |
| Retrieval latency | Per-endpoint p50/p95/p99 | Separate PDP, index, body-store, and consumer latency |
| Citation presence | 100% for returned concepts/hits | Citation correctness assessed by benchmark/review |

## 6. Dashboard and alerts

Minimum dashboard views:

1. source lag/backlog, retries, checkpoint generation/conflicts, and deletes;
2. validation issues by stable code/profile and freshness failures;
3. release build/sign/admission/promotion/rollback/withdrawal outcomes;
4. active channel-to-digest state and index build state;
5. PDP latency/availability, allow/deny/reason/classification aggregates;
6. retrieval throughput/latency/outcomes and citation coverage; and
7. SLO burn, dependency health, recovery exercise, and aggregate cost.

Alerts route to named source, platform, IAM/security, or consumer owners. A high
denial rate alone is not a security incident; it requires context without
logging principals or content. Signature/admission bypass, unauthorized
exposure, stale-revocation behavior, integrity mismatch, or failed withdrawal
is a high-priority control event.

## 7. Hosting and verification gates

Before enabling an exporter:

- approve collector/exporter, endpoint, TLS/workload identity, regions, and egress;
- configure resource identity without host/user secrets;
- approve sampling, tail rules, attribute processor/allowlist, retention, RBAC,
  tenant isolation, support access, and deletion/legal-hold behavior;
- run canary strings resembling content/identifiers and prove they are absent at
  application, collector, backend, dashboard, alert, and support-export layers;
- load-test telemetry overhead and backpressure/failure behavior;
- ensure exporter failure never bypasses authorization or release controls; and
- document dashboards, alerts, on-call, incident classification, and evidence retention.

The application must fail safe for the business control even when telemetry is
unavailable; inability to export a span must not change an authorization denial
into an allow.
