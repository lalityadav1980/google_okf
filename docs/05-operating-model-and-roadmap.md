# Operating Model and Delivery Roadmap

## 1. Operating-model principle

XYZ Bank should operate OKF as a federated knowledge product:

- domain teams own meaning, source authority, classification, verification, and
  freshness;
- a central platform team owns the profile tooling, producer framework, release
  service, serving controls, reliability, and developer experience; and
- enterprise architecture, security, privacy, records, data governance, and AI
  risk define and assure common policy.

This avoids both uncontrolled local formats and a central team becoming the
editor of all bank knowledge.

## 2. Roles

| Role | Primary accountability |
|---|---|
| Executive sponsor | Outcome, funding, cross-platform mandate, risk acceptance route |
| Enterprise architecture | Reference architecture, platform boundaries, standards and ADRs |
| OKF platform product owner | Product roadmap, service levels, adoption and value metrics |
| OKF platform engineering | Producer SDK, validators, release, serving, telemetry and support |
| Domain knowledge owner | Meaning, authority, owner assignment, verification and freshness |
| Source-system owner | Supported extraction, versions, entitlements, change events and source availability |
| YODA owner | Confirmed producer/consumer integration and user-experience controls |
| RACK owner | Confirmed producer/consumer integration and catalog/retrieval controls |
| Information security | Threat model, authorization, cryptography, supply chain and monitoring |
| Privacy and records management | Data minimization, residency, retention, legal hold and disposition |
| AI/model risk | Use-case classification, evaluation, oversight and model controls |
| Consumer product owner | Retrieval policy, user outcome, evaluations, feedback and incident response |
| Internal audit/assurance | Independent review of control design and operating evidence as required |

## 3. RACI for core activities

Legend: A = accountable, R = responsible, C = consulted, I = informed.

| Activity | Platform | Domain owner | Source owner | YODA/RACK consumer | Security/risk | Architecture |
|---|---|---|---|---|---|---|
| Define OKF organizational profile | R | C | C | C | C | A |
| Define concept content and authority | C | A/R | C | I | C | I |
| Build source connector | R | C | A/R | I | C | C |
| Classify and map entitlements | R | A | R | C | C | I |
| Verify critical concept | I | A/R | C | I | C | I |
| Approve release tooling | A/R | I | I | C | C | C |
| Approve domain release | R | A | C | I | C | I |
| Index and serve release | A/R | I | I | R | C | C |
| Approve consumer use case | C | C | I | A/R | C | C |
| Respond to knowledge incident | R | A/R | R | R | C | I |
| Accept residual risk | C | C | I | C | R/A per bank policy | C |

The bank's existing governance may assign accountability differently. The final
RACI must use named organizational roles rather than platform names.

## 4. Delivery phases

### Phase 0: Mobilize and discover — approximately 2–3 weeks

Deliverables:

- confirmed definitions and capability maps for YODA and RACK;
- current-state source, consumer, content-flow, and entitlement inventory;
- candidate use-case scoring and pilot selection;
- authoritative-source and ownership map;
- initial data-classification and residency assessment;
- current metrics baseline; and
- agreed decision authorities and pilot guardrails.

Exit criteria:

- two bounded source collections and one consumer are approved;
- content owners and control partners are assigned;
- no unresolved ambiguity exists about the pilot's source of truth.

### Phase 1: Profile and reference architecture — approximately 3–4 weeks

Deliverables:

- XYZ Bank OKF profile v0.1;
- concept taxonomy and relationship conventions;
- source/owner/classification/entitlement metadata contract;
- threat model and control design;
- repository, branching, review, release, retention, and rollback design;
- consumer contract and release manifest; and
- benchmark and acceptance-test design.

Exit criteria:

- architecture, security, data/knowledge governance, and risk approve build of
  the pilot control plane.

### Phase 2: Controlled pilot — approximately 6–8 weeks

Deliverables:

- reusable producer skeleton;
- one Confluence producer and one SharePoint producer;
- optional structured catalog connector if needed for the technology use case;
- profile validator and policy gates;
- protected repository and reviewer workflow;
- signed immutable release and release catalog;
- entitlement-aware lexical/vector retrieval for one YODA or RACK consumer;
- benchmark suite and operational dashboard; and
- read-only user pilot.

Exit criteria:

- all mandatory security and release tests pass;
- benchmark outcomes improve against the agreed baseline;
- rollback, source withdrawal, entitlement revocation, and index rebuild are
  demonstrated;
- residual risks have named owners and acceptance decisions.

### Phase 3: Production hardening — approximately 8–12 weeks

Deliverables:

- high availability and disaster recovery;
- capacity, performance, and failure testing;
- platform SLOs and support model;
- regional/residency deployment where required;
- automated owner, freshness, drift, and source-removal workflows;
- consumer SDK or documented API;
- compatibility suite for YODA, RACK, and approved agent runtimes;
- security monitoring and incident procedures; and
- service onboarding standards.

### Phase 4: Federated scale — continuous

Deliverables:

- self-service domain onboarding with certification gates;
- reusable connectors and mappings;
- organization-wide release catalog;
- quality scorecards and remediation workflow;
- cost and reuse telemetry;
- additional consumer integrations; and
- periodic OKF/specification and bank-profile compatibility reviews.

## 5. Pilot backlog

### Workstream A: Product and governance

- Confirm use cases, users, outcomes, sources, and exclusions.
- Assign domain owners and reviewers.
- Define profile, taxonomy, source precedence, and lifecycle.
- Define operational and knowledge-incident processes.

### Workstream B: Producer framework

- Create connector interface and incremental cursor/checkpoint contract.
- Preserve stable source IDs, versions, anchors, and entitlements.
- Implement deterministic normalization and idempotent generation.
- Add optional AI enrichment behind a feature flag and review requirement.
- Produce source-to-concept lineage evidence.

### Workstream C: Repository and release

- Configure protected branches and ownership rules.
- Implement syntax, profile, content, security, and link validation.
- Build manifest, digest/signing, immutable artifact, promotion, and rollback.
- Implement emergency withdrawal and source-deletion propagation.

### Workstream D: Serving and consumer

- Implement release-aware concept API and indexes.
- Enforce authorization before candidate retrieval and graph expansion.
- Integrate one approved YODA or RACK consumer.
- Return concept citations, source links, lifecycle, and release ID.

### Workstream E: Evaluation and assurance

- Build benchmark questions and expected source sets.
- Test groundedness, citation correctness, completeness, and refusal.
- Test stale, deprecated, conflicting, poisoned, and broken concepts.
- Test cross-user, cross-group, and inferred-entitlement leakage.
- Exercise rollback, rebuild, and emergency withdrawal.

## 6. Key performance indicators

### Knowledge quality

- percentage with accountable owner;
- percentage with authoritative source and valid source link;
- percentage within freshness window;
- percentage satisfying required verification tier;
- duplicate, conflicting, orphaned, and broken-link counts; and
- mean time to remediate stale or withdrawn content.

### Consumer quality

- benchmark groundedness and citation precision;
- correct refusal when evidence or entitlement is insufficient;
- retrieval precision/recall for approved source sets;
- user task completion and time-to-answer;
- corrections per 1,000 responses; and
- percentage of material responses traceable to a release and concepts.

### Platform health

- source-change-to-approved-release latency;
- release success/failure and rollback time;
- entitlement-change propagation latency;
- index build duration and release lag;
- serving availability and latency;
- cost per published concept and per retrieval; and
- number of consumers reusing each concept or bundle.

## 7. Go/no-go criteria after pilot

Proceed to production hardening only when:

- OKF demonstrates measurable value over direct source-specific retrieval;
- the profile expresses the required bank controls without breaking baseline OKF
  interoperability;
- entitlement preservation passes independent negative testing;
- source change, deletion, and revocation propagate within agreed objectives;
- domain owners accept the curation workload;
- YODA/RACK capability boundaries and ownership are agreed;
- indexes can be reproduced and rolled back from immutable releases;
- the operating cost and support model are acceptable; and
- architecture, security, privacy, records, AI risk, and business owners approve
  the residual risk.

Stop or redesign if the pilot merely creates another unmanaged copy, cannot
preserve authorization, or depends on unreviewed AI generation for critical
knowledge.
