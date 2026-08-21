# Enterprise Open Knowledge Format Proposal for XYZ Bank

This repository contains a technology-industry-grade proposal for adopting
Google Cloud's Open Knowledge Format (OKF) as a versioned, portable knowledge
interchange standard across XYZ Bank.

> **Status:** Draft for architecture, security, data, risk, and platform review
>
> **Proposal date:** 21 August 2026
>
> **Target standard:** OKF v0.2
>
> **Scope:** Global enterprise knowledge and agentic systems; no business-line-specific implementation

## Executive position

XYZ Bank should adopt OKF as the **canonical exchange and controlled release
format** for agent-ready knowledge. It should not replace Confluence,
SharePoint, YODA, RACK, source-code repositories, data catalogs, or records
management systems.

Existing platforms remain systems of authoring, record, workflow, retrieval,
or execution. Domain-owned producer pipelines convert approved knowledge into
OKF bundles. Git-based controls validate, review, version, sign, and publish
those bundles. YODA, RACK, enterprise search, AI agents, portals, and other
consumers load an approved release through authorization-aware serving and
indexing services.

## Document map

1. [Executive proposal](docs/01-executive-proposal.md) — business problem,
   objectives, options, recommendation, scope, and success measures.
2. [Target architecture](docs/02-target-architecture.md) — logical components,
   information flows, versioning, deployment, and integration patterns.
3. [Use-case catalog](docs/03-use-cases.md) — prioritized bank-wide use cases
   and suitability criteria.
4. [Security, risk, and governance](docs/04-security-risk-governance.md) —
   control model for a regulated financial institution.
5. [Operating model and roadmap](docs/05-operating-model-and-roadmap.md) — roles,
   delivery phases, pilot, metrics, and indicative work packages.
6. [XYZ Bank OKF profile](docs/06-xyz-bank-okf-profile.md) — proposed concept
   types, metadata, lifecycle, validation, and an illustrative concept.
7. [Assumptions and decisions](docs/07-assumptions-decisions-questions.md) —
   discovery assumptions, architecture decisions, and open questions.
8. [ADR-0001](docs/adr/0001-okf-as-knowledge-interchange.md) — formal decision
   record for adopting OKF as an interchange and release format.
9. [Open-source technology stack](docs/08-open-source-technology-stack.md) —
   selected tools, alternatives, licensing considerations, and adoption points.
10. [Framework design](docs/09-framework-design.md) — executable components,
    contracts, validation layers, and planned producer/release/consumer design.
11. [Development plan and tracker](docs/10-development-plan-and-tracker.md) —
    increments, epics, actions, blockers, acceptance, and delivery governance.
12. [ADR-0002](docs/adr/0002-python-core-and-open-platform.md) — initial
    framework-language and open-platform-interface decision.
13. [ADR-0003](docs/adr/0003-stable-identity-and-canonical-hashing.md) — stable
    source-anchored identity, path allocation, rename, and hashing rules.
14. [ADR-0004](docs/adr/0004-producer-transaction-boundary.md) — checkpoint,
    replay, deletion, retry, publication, and dry-run transaction semantics.
15. [Validation and conformance](docs/11-validation-and-conformance.md) — stable
    issue catalog, profile boundaries, fixture suite, and rule governance.
16. [ADR-0005](docs/adr/0005-release-manifest-and-reproducible-archive.md) —
    release inventory, deterministic archive, validation, and digest boundary.
17. [OCI signing and promotion](docs/12-oci-signing-and-promotion.md) — ORAS,
    Cosign, media types, trust options, registry controls, and unblock inputs.
18. [Release admission policy](docs/13-release-admission-policy.md) — OPA input,
    denial catalog, environment policy, evidence, tests, and lifecycle use.
19. [Authorization and serving](docs/14-authorization-and-serving.md) —
    authorize-before-retrieval invariant, catalog lifecycle, OpenAPI, and tests.
20. [ADR-0006](docs/adr/0006-authorization-before-retrieval.md) — retrieval
    authorization, immutable routing, withdrawal, and public error decisions.
21. [Source and platform discovery](docs/15-source-and-platform-discovery.md) —
    Confluence/SharePoint evidence gates, YODA/RACK maps, and connector certification.
22. [Observability and operations](docs/16-observability-and-operations.md) —
    content-minimized OpenTelemetry, SLI/SLO proposals, dashboards, and hosting gates.
23. [Evaluation and assurance](docs/17-evaluation-and-assurance.md) — benchmark,
    baseline, scoring, threat/misuse tests, evidence gate, and resilience exercises.

## Framework quick start

Prerequisites: Python 3.13 and `uv` 0.11.7 or later, below 0.13.

```bash
uv sync --locked
uv run xyz-okf render \
  examples/rendering/source-record.yaml \
  examples/rendering/mapping.yaml \
  --output-root /tmp/xyz-okf-render
uv run xyz-okf allocate-identity \
  examples/rendering/source-record.yaml \
  profiles/xyz-bank-identity.yaml \
  --type Runbook
uv run xyz-okf hash-concept \
  examples/rendering/expected/runbooks/identity-service-degradation--178875d5e353.md
uv run xyz-okf build-release examples/pilot-bundle \
  --profile profiles/xyz-bank-pilot.yaml \
  --bundle-id xyz-bank-pilot \
  --release-id 2026.08.21.1 \
  --source-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --created-at 2026-08-21T00:00:00Z
uv run xyz-okf inspect examples/pilot-bundle
uv run xyz-okf validate examples/pilot-bundle \
  --profile profiles/xyz-bank-pilot.yaml
```

Run all local quality gates:

```bash
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src
uv run pytest
```

The first vertical slice includes:

- typed OKF v0.2 and XYZ Bank profile models;
- deterministic source-record rendering with golden byte-level tests;
- a CLI validator with text and JSON output;
- controlled type, metadata, verification, freshness, link, and relationship checks;
- a portable connector contract for Confluence, SharePoint, YODA, and RACK;
- a source-discovery schema and content-minimized connector certification suite;
- a verified-release catalog with promotion, rollback, and withdrawal behavior;
- a provider-neutral authorization port and deny-by-default reference evaluator;
- an OpenID Connect-declared, release-aware FastAPI/OpenAPI serving contract;
- OpenTelemetry API spans/metrics with hashed identifiers and no content fields;
- a versioned pilot benchmark, deterministic scorer, and assurance evidence plan;
- a conformant synthetic pilot bundle; and
- automated CI, tests, issue forms, and pull-request controls.

Delivery state is tracked in
[`tracking/backlog.yaml`](tracking/backlog.yaml). The repository is currently
unlicensed; action `OKF-004` must be completed before treating the project code
as open-source software.

## Decision requested

Approve a time-boxed discovery and pilot to validate:

- the XYZ Bank OKF organizational profile;
- one Confluence and one SharePoint producer;
- the appropriate producer/consumer responsibilities for YODA and RACK;
- Git-based validation, approval, immutable release, and rollback;
- entitlement-preserving retrieval from one approved consumer; and
- measurable improvement in provenance, freshness, reuse, and answer quality.

Approval of the pilot does **not** approve replacement of an existing platform,
large-scale content migration, autonomous agent publishing, or storage of
restricted information in OKF.

## Authoritative external references

- [Open Knowledge Format v0.2 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
- [Google Cloud: Introducing the Open Knowledge Format](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- [Google Cloud: OKF v0.2 trust and attestation additions](https://cloud.google.com/blog/products/data-analytics/okf-v0-2-adds-trust-signals/)
- [Google Cloud reference implementation and sample bundles](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)

The Google reference agent and visualizer are proofs of concept. They are not
assumed to satisfy XYZ Bank production, security, resilience, or support
requirements.
