# Development Plan and Delivery Tracker

## 1. Tracking model

The machine-readable source for delivery actions is
[`tracking/backlog.yaml`](../tracking/backlog.yaml). GitHub Issues should be
created from those IDs when work is assigned. Do not create a second ID or
silently change acceptance criteria in a project board.

Statuses:

| Status | Meaning |
|---|---|
| `BACKLOG` | Accepted scope, not yet refined or sequenced |
| `READY` | Dependencies known; owner can begin without further discovery |
| `IN_PROGRESS` | Named owner actively delivering the action |
| `BLOCKED` | Cannot progress; blocker and decision owner must be explicit |
| `IN_REVIEW` | Implementation complete and in technical/control review |
| `DONE` | Acceptance evidence exists and required review is complete |

Priority:

- `P0`: required for the current milestone or a control/safety prerequisite;
- `P1`: required for the pilot outcome;
- `P2`: production hardening or scale; and
- `P3`: optional optimization.

## 2. Delivery increments

### Increment 0 — Repository and architecture foundation

Outcome: reviewable proposal, selected open-source stack, executable package,
quality tooling, contribution controls, and visible backlog.

Current evidence:

- architecture and security proposal;
- Python package and locked dependencies;
- OKF/profile validator CLI;
- deterministic source-to-concept renderer and golden output fixture;
- sample bank bundle;
- unit and CLI tests;
- strict lint/type checks; and
- CI and issue templates.

Exit requires the first remote CI run to pass and the repository license action
to have a named decision owner.

### Increment 1 — Validator and producer SDK

Outcome: conformance-grade validation and a deterministic source-to-concept SDK.

Scope:

- golden valid/invalid fixture corpus;
- stable issue-code catalog;
- deterministic OKF renderer;
- canonical hashing and source lineage;
- checkpoint, retry, deletion, and dry-run contracts;
- connector contract test kit; and
- profile v0.2 proposal based on implementation feedback.

### Increment 2 — Controlled source producers

Outcome: one Confluence and one SharePoint collection produce reviewable,
entitlement-preserving OKF changes.

Scope:

- API and authorization discovery;
- stable ID/version/change-feed mapping;
- page/document, attachment, deletion, and ACL behavior;
- classification and source-owner mapping;
- incremental connector implementations;
- deterministic transformations; and
- controlled Git change proposal.

### Increment 3 — Immutable release supply chain

Outcome: approved bundle commits become signed, reproducible OCI releases.

Scope:

- manifest schema and canonical archive;
- OCI media types and ORAS publication;
- Cosign trust model and verification;
- OPA release policy;
- artifact promotion, retention, withdrawal, and rollback; and
- release catalog.

### Increment 4 — Authorized consumer pilot

Outcome: one YODA or RACK consumer retrieves approved concepts from an explicit
release without entitlement widening.

Scope:

- YODA/RACK capability decision;
- serving OpenAPI contract;
- bank identity and policy-decision integration;
- release-aware lexical/hybrid retrieval;
- citations and trace IDs;
- negative entitlement tests; and
- emergency withdrawal.

### Increment 5 — Assurance and production hardening

Outcome: measurable pilot value and a production go/no-go decision.

Scope:

- benchmark/evaluation pack;
- threat model and penetration testing;
- privacy, records, residency, and model-risk evidence;
- performance, resilience, recovery, and rollback tests;
- OpenTelemetry dashboards and SLOs;
- support and incident model; and
- residual-risk decisions.

## 3. Epic map

| Epic | Outcome | Lead role | Dependency |
|---|---|---|---|
| E00 Foundation and governance | Buildable, reviewable, legally governable repository | Platform product owner | Sponsor and governance |
| E10 Profile and validation | Stable bank profile and conformance engine | Knowledge architecture | OKF v0.2 |
| E20 Producer SDK | Deterministic source-to-concept framework | Platform engineering | E10 |
| E30 Confluence producer | Controlled Confluence source changes | Connector team/source owner | E20, API access |
| E31 SharePoint producer | Controlled SharePoint source changes | Connector team/source owner | E20, API access |
| E40 Release supply chain | Signed immutable bundle release | Platform/security | E10 |
| E50 Policy and authorization | Fail-closed publication and retrieval | Security/IAM | Internal policy services |
| E60 Serving and retrieval | Release-aware consumer API and index | Platform/search | E40, E50 |
| E70 YODA/RACK integration | One approved consumer using the contract | Internal platform owners | Capability decisions |
| E80 Observability and operations | SLOs, traces, metrics and incident procedures | SRE/platform | Hosted components |
| E90 Pilot evaluation and assurance | Evidence-backed production decision | Product/risk | E30/E31/E60/E70 |

## 4. Immediate action queue

These are the next actions in execution order. IDs match the backlog file.

1. **OKF-003:** enable the repository CI workflow and confirm the first protected
   branch check succeeds.
2. **OKF-004:** assign Legal/Open Source Office ownership and choose the
   repository license; Apache-2.0 is the technical recommendation.
3. **OKF-105:** add official OKF v0.2 conformance and regression fixtures.
4. **OKF-201 (in review):** deterministic `SourceRecord` rendering, fail-closed
   entitlement mapping, CLI, and byte-level golden evidence are implemented.
5. **OKF-202:** define canonical source/output hashing and stable concept-path
   allocation.
6. **OKF-203:** implement checkpoint, deletion/tombstone, retry, and dry-run
   contracts.
7. **OKF-301 and OKF-311:** run Confluence and SharePoint API/ACL discovery in
   parallel with source owners.
8. **OKF-401:** specify and implement the release manifest and canonical archive.
9. **OKF-501:** create OPA policies for profile, classification, verification,
   and release admission.
10. **OKF-701 and OKF-702:** complete YODA and RACK capability maps and select
    the pilot consumer.

## 5. Blocked actions requiring XYZ Bank input

| Action | Blocker | Required decision/evidence |
|---|---|---|
| OKF-004 | Repository has no approved license | Owner and approved license |
| OKF-301/302 | Confluence scope and API identity unknown | Pilot spaces, API access, versions, ACL/change-feed evidence |
| OKF-311/312 | SharePoint scope and API identity unknown | Pilot sites/libraries, Graph/API access, records and ACL evidence |
| OKF-502 | Enterprise authorization service unspecified | PDP/PEP design, identity attributes, group/relationship data and SLO |
| OKF-701 | YODA capabilities not defined | Product owner, interfaces, data flow, control and roadmap map |
| OKF-702 | RACK capabilities not defined | Product owner, interfaces, data flow, control and roadmap map |
| OKF-901 | Pilot questions/users not selected | Use-case owner, benchmark, expected sources and baseline |

## 6. Definition of ready

An action is `READY` only when it has:

- a stable action ID and epic;
- a named accountable owner role;
- an outcome and acceptance criteria;
- dependencies and blockers identified;
- security/data classification considered;
- test/evidence expectations; and
- no unresolved decision that materially changes implementation.

## 7. Definition of done

An implementation action is `DONE` only when:

- code, tests, documentation, and telemetry are complete where applicable;
- acceptance criteria pass with retained evidence;
- lint, type, unit, security, and profile validation pass;
- new dependencies have license/security review;
- public contract changes are versioned and documented;
- control-owner review is complete for security-sensitive work;
- rollback or removal is defined; and
- the backlog, issue, ADR, and release notes are updated.

## 8. Pull-request evidence

Each pull request must reference an action ID and contain:

- outcome and scope;
- architecture/profile impact;
- security, privacy, records, and entitlement impact;
- tests and commands executed;
- before/after or sample report when behavior changes;
- dependency/license changes;
- rollback approach; and
- remaining risks or follow-up IDs.

## 9. Weekly delivery review

The product owner should review:

1. milestone exit criteria and evidence;
2. P0/P1 actions by status and age;
3. blockers, decision owner, and due date;
4. new risks and architecture decisions;
5. knowledge-quality and engineering-quality metrics;
6. dependency/security alerts;
7. spend and capacity; and
8. changes to YODA/RACK/source-system roadmaps.

Do not report percentage complete without the completed/total acceptance
criteria and evidence. A blocked action remains visible and is never relabeled
as progress.
