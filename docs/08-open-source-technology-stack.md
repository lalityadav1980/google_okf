# Open-Source Technology Stack

## 1. Recommendation

Use a small Python framework for OKF production and validation, surrounded by
open standards for policy, artifacts, search, orchestration, and telemetry.
Adopt components incrementally; the pilot should not require the complete
production stack.

The core decision is:

```text
Python producer/validator SDK
        + Git review
        + OKF Markdown/YAML
        + immutable OCI release
        + authorization-aware retrieval
```

The code must remain usable without YODA, RACK, a vector database, Kubernetes,
or a particular model provider. Those systems integrate through adapters.

The initial core choice is recorded in
[ADR-0002](adr/0002-python-core-and-open-platform.md).

## 2. Selection criteria

Components are assessed for:

- recognized open-source license and active governance;
- compatibility with open formats and replaceable interfaces;
- deterministic and offline operation for validation;
- security maintenance and software-supply-chain support;
- enterprise identity, authorization, audit, and observability integration;
- self-hosting and regional deployment;
- developer productivity and testability;
- operational maturity at large scale; and
- ability to obtain commercial support without changing the core contract.

All licenses in this document are indicative. XYZ Bank open-source governance
and Legal must verify the exact version, transitive dependencies, distribution
model, and intended use before production approval.

## 3. Core development stack — selected

| Capability | Technology | Indicative license | Decision and rationale |
|---|---|---|---|
| Runtime | Python 3.13 | PSF | Selected. Aligns with the Google OKF reference implementation and is strong for Markdown, YAML, APIs, and knowledge engineering. |
| Project/dependency management | uv | Apache-2.0/MIT | Selected. Fast, reproducible `pyproject.toml` and cross-platform lockfile workflow. |
| Data models and schema | Pydantic v2 | MIT | Selected. Typed validation and JSON Schema generation for profiles, manifests, reports, and APIs. |
| YAML | PyYAML safe loader | MIT | Selected for validation. A round-trip-preserving writer can be added only when automated editing is required. |
| Markdown parsing | markdown-it-py | MIT | Selected. Structured token parsing avoids fragile regular expressions for links. |
| CLI | Typer + Rich | MIT | Selected. Typed commands and readable local/CI validation reports. |
| Tests | pytest + pytest-cov | MIT | Selected. Supports unit, fixture, contract, integration, and conformance tests. |
| Lint and format | Ruff | MIT | Selected. One fast, reproducible linter/formatter with `pyproject.toml` configuration. |
| Static types | mypy | MIT | Selected for strict checking of the framework and connector contracts. |
| Version control | Git | GPL-2.0-only | Selected as the portable history/review substrate; hosting platform remains replaceable. |

The Google reference repository currently demonstrates Python-based generation,
bundle validation, and visualization, while emphasizing that OKF is independent
of any agent framework. See the
[official OKF repository](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf).

Official project references:

- [uv project and lockfile workflow](https://docs.astral.sh/uv/guides/projects/)
- [Pydantic JSON Schema](https://github.com/pydantic/pydantic/blob/main/docs/concepts/json_schema.md)
- [Typer documentation](https://typer.tiangolo.com/tutorial/)
- [Ruff linter](https://docs.astral.sh/ruff/linter/) and
  [formatter](https://docs.astral.sh/ruff/formatter/)
- [pytest fixtures and scalable tests](https://docs.pytest.org/en/stable/explanation/fixtures.html)

## 4. Production platform stack — recommended

| Layer | Primary recommendation | Why it fits | Adoption point |
|---|---|---|---|
| Policy-as-code | Open Policy Agent (OPA/Rego) | General-purpose, open policy decision engine for CI and runtime authorization decisions | Pilot policy gates; production retrieval |
| Release packaging | OCI artifact with ORAS | Content-addressed, registry-portable distribution of arbitrary artifacts | Pilot release milestone |
| Artifact integrity | Sigstore Cosign | Signs/verifies OCI artifacts or blobs; supports identity/KMS-based models | Pilot release milestone |
| Release registry | Existing OCI-compatible registry; Harbor or Zot are open-source options | Avoids introducing a separate proprietary knowledge artifact store | Reuse existing bank platform first |
| Release catalog | PostgreSQL | Durable metadata, transactions, mature operations, portable SQL | Production hardening |
| Serving API | FastAPI `>=0.141,<0.142` | Implemented OpenAPI/JSON Schema boundary from the same Pydantic contracts; enterprise identity/PDP integration remains external | Consumer contract implemented; production wiring after IAM approval |
| Hybrid retrieval | OpenSearch | One Apache-2.0 engine for lexical and vector/hybrid retrieval | Consumer pilot, if current YODA/RACK search is unsuitable |
| Workflow orchestration | CI for pilot; Argo Workflows on Kubernetes at scale | Keeps pilot small; Argo supports container DAGs, retries, schedules, artifacts, and audit history | Add only after connector count/volume justifies it |
| Telemetry | OpenTelemetry | Vendor-neutral traces, metrics, and logs | Instrument from first hosted service |
| Metrics | Prometheus | Open monitoring model and broad platform support | Production service |
| Dashboards | Existing approved backend; Grafana OSS is an option | Avoids forcing a new dashboard platform | Reuse bank standard first |
| Runtime | OCI containers on Kubernetes with Helm/Kustomize | Portable deployment and policy integration | Production hardening, not local CLI |

Primary references:

- [OPA policy-as-code](https://www.openpolicyagent.org/docs)
- [ORAS and OCI artifacts](https://oras.land/docs/)
- [Cosign signature verification](https://docs.sigstore.dev/cosign/verifying/verify/)
- [FastAPI open-standard features](https://fastapi.tiangolo.com/features/)
- [OpenSearch hybrid retrieval](https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/index/)
- [Argo Workflows](https://argo-workflows.readthedocs.io/en/latest/)
- [OpenTelemetry](https://opentelemetry.io/docs/)

## 5. Deliberately not selected as core dependencies

### Agent frameworks

Do not make LangChain, LlamaIndex, Google ADK, or another agent framework a core
dependency. They may have consumer adapters, but OKF parsing, validation,
production, and release must remain deterministic and model-independent.

### A vector database as source of truth

Embeddings are derived, model-specific, and difficult to review. Git and the
immutable OKF release are authoritative; a vector index can be deleted and
rebuilt.

### A generic document connector framework for the first controlled sources

Generic ingestion tools are useful for low-risk discovery but often fail to
preserve source record versions, anchors, approvals, classifications, deletions,
and entitlements precisely enough for regulated publication. Confluence and
SharePoint producers should implement the framework's narrow connector contract
against approved source APIs. Reuse existing connectors only after contract and
control testing.

### Kubernetes and workflow orchestration for local development

The validator and producers must run from a CLI and CI job. Requiring a cluster
would slow the pilot, obscure deterministic behavior, and increase the initial
attack surface.

### A graph database for the pilot

Markdown links and typed relationship metadata are sufficient for the first
bundle. Add a relationship index only when benchmarked use cases demonstrate a
need; do not create a second authoritative graph.

## 6. Build-versus-integrate rules

Build only the OKF-specific intellectual property:

- the XYZ Bank profile and validation policy;
- stable concept and source identity rules;
- source adapters that preserve bank metadata and entitlements;
- deterministic source-to-concept transformation;
- release manifest and knowledge quality controls;
- YODA/RACK consumer adapters; and
- benchmark/evaluation packs.

Integrate established open-source or bank-standard services for identity,
authorization, Git, artifacts, search, workflow execution, telemetry, secrets,
and databases.

## 7. Open-source governance actions

Before the first distributable release:

1. Select and approve a license for this repository. It is currently unlicensed;
   public visibility alone does not make the code open source.
2. Generate an SBOM for Python, container, and workflow dependencies.
3. Pin direct dependencies and CI actions; verify lockfile and action updates.
4. Run dependency, secret, license, and vulnerability scanning.
5. Define patch/update SLOs by severity.
6. Record provenance for built packages and OCI artifacts.
7. Maintain a component register with owner, version, license, support route,
   data classification, and exit strategy.
8. Prefer standards-based interfaces so a component can be replaced without
   changing OKF bundles.

## 8. Technology decision checkpoints

| Checkpoint | Decision evidence required |
|---|---|
| Confluence/SharePoint producer | Source API, version, delete, ACL, attachment, and rate-limit proof |
| OCI registry | Existing platform capability, immutability, retention, signing, replication, and access controls |
| OPA runtime | Policy ownership, decision inputs, bundle distribution, latency, and fail-closed behavior |
| OpenSearch | Benchmark against existing YODA/RACK retrieval before adopting another search platform |
| Argo Workflows | Connector volume, scheduling, retries, isolation, audit, and Kubernetes ownership justify it |
| FastAPI gateway | Consumer contract and authorization architecture are approved |
| Grafana or other backend | Reuse the approved enterprise observability platform unless a gap is demonstrated |
