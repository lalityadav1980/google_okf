# ADR-0002: Use a Python Core with Open Platform Interfaces

- **Status:** Accepted for the initial framework
- **Date:** 2026-08-21
- **Decision owner:** Interim repository architecture owner
- **Scope:** OKF producer, validator, release, and serving framework

## Context

The framework must process Markdown and YAML, integrate enterprise content APIs,
support deterministic validation, expose CLI and API contracts, and remain
independent of YODA, RACK, cloud, search, orchestration, and model vendors.

The Google OKF reference implementation uses Python 3.13, but OKF itself does
not require Python. The adopting organisation needs a productive pilot implementation without
making the bundle format or consumer contract language-specific.

## Decision

Use Python 3.13 for the initial core with:

- uv and `pyproject.toml` for reproducible dependency management;
- Pydantic for typed models and JSON Schema;
- PyYAML and markdown-it-py for deterministic document parsing;
- Typer/Rich for CLI interaction;
- pytest, Ruff, and mypy for quality; and
- protocol/OpenAPI/OCI boundaries so other languages and platforms can
  integrate without importing the Python package.

Use open platform interfaces for later capabilities:

- OPA/Rego for policy decisions;
- OCI/ORAS and Cosign for immutable signed releases;
- OpenAPI for serving;
- OpenSearch only if retrieval benchmarking justifies it;
- OpenTelemetry for telemetry; and
- CI initially, with Argo Workflows only when scale requires orchestration.

Agent frameworks and model SDKs are adapters, not core dependencies.

## Consequences

### Positive

- Rapid implementation aligned with the reference ecosystem.
- Strong libraries for structured validation, text, APIs, and testing.
- One model definition can support CLI, JSON Schema, and later OpenAPI.
- Deterministic validation can run locally and in CI without hosted services.
- Open interfaces allow Java, Go, or internal platforms to consume releases.

### Negative

- The adopting organisation must approve Python packaging and dependency operations.
- Runtime performance may require profiling for very large bundles.
- Connector authors in other language communities need API or artifact
  contracts rather than direct library reuse.
- Pydantic models must not become an accidental replacement for the public OKF
  contract.

## Alternatives considered

- **Java core:** strong enterprise ecosystem but slower for the first Markdown/YAML and
  source-connector iteration; remains viable for consumers.
- **Go core:** excellent static binary and OCI ecosystem, but less productive for
  initial knowledge transformation; remains viable for high-throughput services.
- **TypeScript core:** good platform/API integration but weaker alignment with
  the Google reference producer and enterprise data/knowledge tooling.
- **Agent-framework core:** rejected because it couples deterministic knowledge
  controls to model/runtime choices.

## Review triggers

Revisit the decision if:

- measured bundle size or throughput cannot meet approved objectives;
- the strategic enterprise runtime disallows supported Python deployment;
- YODA or RACK requires a different public integration boundary;
- dependency or license risk becomes unacceptable; or
- a stable OKF SDK in another language materially reduces lifecycle cost.
