# Framework Design

## 1. Purpose

The framework provides reusable, deterministic building blocks for producing,
validating, releasing, and consuming XYZ Bank OKF bundles. It is not an agent
runtime, content-management system, search engine, or workflow platform.

The first implementation milestone is a working validator and connector
contract. Release and serving components are introduced only after the content
contract is stable.

## 2. Framework boundaries

```mermaid
flowchart LR
    S[Source API] --> C[Connector contract]
    C --> N[Normalizer and concept renderer]
    N --> V[OKF and bank-profile validator]
    V --> G[Git review]
    G --> M[Manifest and OCI packager]
    M --> P[Policy and signature gates]
    P --> R[Release registry]
    R --> A[Authorized serving adapter]
    A --> Y[YODA, RACK, search, and agents]
```

Implemented now:

- Python package and CLI;
- Pydantic models for OKF v0.2 and the XYZ Bank profile;
- Markdown/YAML parsing;
- base and bank-profile validation;
- link, relationship, identity, freshness, and verification checks;
- connector protocol and immutable source-record contract;
- deterministic source-to-concept renderer and versioned mapping contract;
- governed issue-code catalog and OKF v0.1/v0.2 conformance fixtures;
- checkpoint, retry, deletion, dry-run, and source certification contracts;
- deterministic release archive, OCI/signing command, and OPA admission contracts;
- authorization-before-retrieval, lifecycle catalog, and OpenAPI serving contract;
- content-minimized OpenTelemetry API instrumentation;
- sample bundle and automated tests; and
- locked dependencies and CI-ready commands.

Planned:

- Confluence and SharePoint adapters;
- approved remote OCI/Cosign and enterprise OPA/PDP integrations;
- production enterprise entitlement adapter;
- production catalog and hybrid index adapter;
- YODA and RACK adapters; and
- approved OpenTelemetry SDK/exporter, dashboards, alerts, and operational SLOs.

## 3. Repository structure

```text
.
├── .github/                    # CI, issue forms and PR controls
├── docs/                       # Proposal, architecture and development guidance
├── examples/pilot-bundle/      # Conformant illustrative OKF bundle
├── profiles/                   # Versioned organizational profile definitions
├── src/xyz_okf/
│   ├── cli.py                  # User and CI commands
│   ├── connector_conformance.py # Reusable source sandbox certification
│   ├── discovery.py            # Governed source discovery evidence model
│   ├── evaluation.py           # Content-free benchmark scoring contract
│   ├── identity.py             # Stable identity and canonical digest profiles
│   ├── models.py               # Typed OKF/profile/report models
│   ├── parser.py               # UTF-8, YAML frontmatter and Markdown parsing
│   ├── profile.py              # Profile loader
│   ├── producer.py             # Change planning, retry, publication and checkpoints
│   ├── release.py              # Manifest, deterministic archive and verification
│   ├── renderer.py             # Deterministic source-to-concept rendering
│   ├── serving.py              # Authorized release catalog and retrieval
│   ├── supply_chain.py         # Safe ORAS/Cosign digest command contracts
│   ├── telemetry.py            # Content-minimized OpenTelemetry API contract
│   ├── validator.py            # Bundle/profile validation engine
│   └── connectors/base.py      # Portable source adapter contract
├── tests/                      # Unit, CLI and conformance tests
├── tracking/                   # Machine-readable delivery backlog
├── pyproject.toml              # Package, dependencies and quality configuration
└── uv.lock                     # Reproducible dependency resolution
```

## 4. CLI contract

### Validate a bundle

```bash
uv run xyz-okf validate examples/pilot-bundle \
  --profile profiles/xyz-bank-pilot.yaml
```

### Render a source record

```bash
uv run xyz-okf render \
  examples/rendering/source-record.yaml \
  examples/rendering/mapping.yaml \
  --output-root /tmp/xyz-okf-render
```

The mapping owns the stable concept UID and output path until `OKF-202` defines
their allocation rules. An existing, different output is not replaced unless
`--force` is explicit. CI can prove that committed output is current without
writing by adding `--check`.

Exit codes:

- `0`: no validation errors; warnings may exist;
- `1`: one or more bundle/profile errors; and
- `2`: invalid invocation or profile configuration.

JSON for CI or API integration:

```bash
uv run xyz-okf validate examples/pilot-bundle \
  --profile profiles/xyz-bank-pilot.yaml \
  --format json
```

### Inspect a bundle

```bash
uv run xyz-okf inspect examples/pilot-bundle
```

### Export the profile-definition schema

```bash
uv run xyz-okf profile-schema
```

## 5. Validation architecture

Validation runs in layers:

1. **File layer:** recursive Markdown discovery and UTF-8 decoding.
2. **OKF structure:** frontmatter delimiter, YAML mapping, required base `type`,
   reserved `index.md`/`log.md`, and root OKF version.
3. **Typed OKF metadata:** timestamps, actor identity, sources, tags, lifecycle,
   and single-or-list verification compatibility.
4. **XYZ Bank profile:** required fields, controlled types/enums, criticality
   verification, relationship vocabulary, and stable concept UID.
5. **Bundle integrity:** duplicate UIDs, link containment, and missing targets.
6. **Time-dependent policy:** staleness evaluated against an explicit clock.

The validator returns structured issues with severity, stable code, document,
concept ID, field, and message. Consumer automation must rely on issue codes,
not human-readable message text.

## 6. Producer connector contract

Each source adapter implements `KnowledgeSource`:

```python
class KnowledgeSource(Protocol):
    @property
    def source_system(self) -> str: ...

    async def list_changes(
        self, cursor: str | None, *, limit: int = 100
    ) -> ChangeBatch: ...

    async def fetch_record(self, record_id: str) -> SourceRecord: ...
```

`ChangeBatch` carries ordered `SourceChange` events and an opaque next cursor.
Each event is an `upsert` or `delete` with stable record ID, exact source
version, and aware change timestamp. `SourceRecord` is immutable and must contain:

- source system and stable record ID;
- source version and canonical resource URI;
- title and body;
- source modification time;
- classification and entitlement references; and
- source-specific metadata.

Connectors fetch facts. They do not decide the final concept type, silently
merge conflicting authority, expand user permissions, or publish directly to
the protected branch.

## 7. Producer execution and rendering contract

```text
discover change
  -> fetch versioned source record
  -> verify source entitlement and classification
  -> normalize deterministic representation
  -> split into stable concepts
  -> optionally propose AI enrichment
  -> render OKF with source lineage
  -> validate
  -> create reviewable change set
  -> checkpoint only after approved publication
```

Required design properties:

- idempotency: the same source version produces the same deterministic content;
- incremental cursors: restart without rereading the full source;
- deletion/tombstone support;
- stable concept UID independent of file path;
- no checkpoint advancement on partial failure;
- source and output hashes;
- bounded retries and rate limiting;
- attachment and embedded-content policy; and
- dry-run/diff mode before any proposed change.

`ProducerEngine` now implements the page-level execution boundary. It retries
only explicitly retryable source/publication failures, validates fetched record
identity and version, treats deletions as first-class events, and publishes a
deterministic operation batch before atomically compare-and-setting its
checkpoint. Every operation has a content-derived idempotency key. Partial
planning/publication failures never advance the cursor, and dry run performs no
publication or checkpoint write.

`InMemoryCheckpointStore` is the contract reference. `SQLiteCheckpointStore`
provides durable single-runner local state. Production stores must implement the
same compare-and-set protocol using an approved transactional platform.

The first deterministic stage is implemented. `RenderMapping` is a versioned,
reviewable input containing classification-independent mapping decisions such
as type, owner, domain, criticality, tags, relationships, concept UID, and
output path. `SourceRecord` remains authoritative for title, source URI,
version, modification time, classification, body, and entitlement references.

For identical source-record and mapping values the renderer guarantees:

- UTF-8 output with LF line endings and exactly one final body newline;
- timestamps normalized to UTC with an explicit `Z` suffix;
- sorted, de-duplicated tags and deterministic relationship/verification order;
- stable top-level frontmatter ordering and recursively sorted extension keys;
- retained source system, record ID, source version, resource, and mapping version;
- a SHA-256 digest over the exact rendered bytes; and
- a fail-closed error for zero/multiple entitlements or an ACL mapping absent
  from the source entitlement set.

Extensions cannot replace fields controlled by the renderer, including source
identity, classification, authorization, provenance, and lifecycle metadata.
The renderer does not generate verification claims and contains no model call.
Approved verification events must be explicitly supplied in the mapping.
Connector-specific `SourceRecord.metadata` is context for mapping logic and is
not copied into frontmatter automatically; every published extension is an
explicit, reviewed mapping field. The CLI also rejects syntactic path traversal
and output paths that escape the bundle through a filesystem symlink.

Stable identity/path allocation and versioned source/concept canonical hashes
are implemented under `OKF-202`. Page checkpoints, deletion events, bounded
retry, idempotent operation IDs, and read-only dry-run behavior are implemented
under `OKF-203`.

## 8. Release contract

The release builder now:

1. validate the bundle with a pinned profile and clock;
2. create canonical per-file SHA-256 digests;
3. generate a manifest containing source commit, profile, prior release, files,
   classifications, and authorization references;
4. builds and verifies a deterministic manifest-bearing `tar.gz` archive; and
5. returns exact manifest/archive digests for the next transport stage.

Planned follow-on stages publish the same bytes as a typed OCI artifact with
ORAS, sign/attest the immutable digest with Cosign using the approved bank trust
model, verify before promotion, and write release metadata to the release
catalog.

The packager must not push an artifact when validation errors exist. Promotion
uses the same digest across environments.

## 9. Consumer contract

The reference serving adapter now exposes:

- list authorized bundles/releases;
- resolve release channel to immutable digest;
- fetch authorized concept metadata and body;
- filter by lifecycle, freshness, classification, and verification;
- return citations and source resources;
- record release/profile/policy versions in trace events; and
- support emergency withdrawal without deleting audit evidence.

FastAPI implements the HTTP boundary, while the committed OpenAPI contract keeps
YODA, RACK, and other consumers independent of Python. The application cannot be
constructed without an explicit principal resolver and HTTPS OpenID Connect
discovery URL. The provider-neutral PDP port authorizes candidates before body,
snippet, citation, or link-target retrieval.

`ReleaseCatalog` verifies archives admitted under signature/archive/OPA
evidence, keeps OCI and archive digests separate, promotes the same digest via a
channel pointer, rolls back to a prior admitted digest, and denies withdrawn
digests without deleting evidence. Its in-memory implementation and lexical
search are reference adapters, not the production persistence or retrieval
decision. See [authorization and serving](14-authorization-and-serving.md).

## 10. Testing strategy

| Level | Purpose |
|---|---|
| Unit | Parser, models, path resolution, policy and rendering behavior |
| Golden fixture | Known-valid and known-invalid OKF bundles with stable issue codes |
| Contract | Every connector passes the same change, version, deletion, ACL, and retry suite |
| Integration | Source sandbox, Git review, OCI registry, OPA and consumer API |
| Security | Path traversal, malicious Markdown, secret leakage, source poisoning, authorization bypass |
| Performance | Large bundle scan, incremental source sync, archive/index build and retrieval latency |
| Resilience | Retry, partial failure, restart, source deletion, registry outage and rollback |
| Evaluation | Benchmark questions, expected concepts, citation correctness, groundedness and refusal |

No test should require a live model unless it is explicitly marked as an
evaluation or integration test. The core validator remains deterministic.

## 11. Extension rules

- Add source integrations under `connectors/`; do not put source-specific logic
  in the validator.
- Add new profile fields to the profile definition and documentation before
  enforcing them.
- Preserve unknown OKF frontmatter fields.
- Add a stable issue code and tests for every validation rule.
- Keep network calls outside parsing and base validation.
- Keep model/AI enrichment behind an interface and feature flag.
- Do not include credentials or real bank content in fixtures.
- Record an ADR for a new platform dependency or public contract.
