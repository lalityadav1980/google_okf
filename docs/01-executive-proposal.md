# Enterprise Open Knowledge Format Proposal

## 1. Executive summary

XYZ Bank's knowledge is distributed across collaboration platforms,
repositories, catalogs, internal platforms, operational systems, and the
experience of subject-matter experts. Confluence, SharePoint, YODA, RACK, and
other platforms each solve valuable parts of the knowledge lifecycle, but they
do not currently expose knowledge through one portable, reviewable contract
that can be consumed consistently by humans and AI agents.

This fragmentation creates repeated ingestion, conflicting copies, weak
provenance, inconsistent freshness, platform-specific integrations, and an
inability to reproduce exactly what an agent knew when it produced an answer or
took an action.

The proposal is to adopt Open Knowledge Format (OKF) v0.2 as XYZ Bank's
enterprise knowledge **interchange and release standard**. OKF represents a
knowledge bundle as Markdown documents with YAML frontmatter and links between
concepts. The format is human-readable, agent-readable, portable, and suitable
for Git-based version control. The standard defines provenance, verification,
freshness, lifecycle, and optional attested-computation vocabulary, while
deliberately leaving storage, retrieval, authorization, and execution to the
adopting organization.

OKF complements the current estate:

- Confluence and SharePoint remain authoring, collaboration, publishing, or
  records-management systems as applicable.
- YODA and RACK retain their validated internal responsibilities, such as
  agent experience, orchestration, search, catalog, retrieval, or knowledge
  management.
- Source systems remain authoritative for operational facts and governed
  records.
- OKF becomes the common representation used to publish approved, versioned,
  agent-ready knowledge from those systems.

The recommended first decision is a bounded pilot, not an enterprise migration.

## 2. Current-state problem statement

### 2.1 Fragmented knowledge surfaces

Knowledge about a single subject is frequently split across a policy page, an
operating procedure, a service catalog entry, an architecture document, an API
definition, support guidance, and informal commentary. Consumers must discover
and reconcile these surfaces independently.

### 2.2 Multiple copies with unclear authority

The same material can be copied into Confluence, SharePoint, YODA, RACK, local
documents, prompts, and retrieval indexes. It is difficult for a user or agent
to determine:

- which copy is authoritative;
- whether it is approved and effective;
- who owns it;
- when it becomes stale;
- which source statements support it; and
- which prior version was used for an earlier decision.

### 2.3 Platform-specific agent integrations

Each agent or assistant requires custom connectors, content parsing, chunking,
metadata mapping, and retrieval behavior. The same integration problem is
repeated for every source-consumer pair. Changing an authoring or retrieval
platform can require rebuilding the knowledge layer.

### 2.4 Weak reproducibility and rollback

Many knowledge indexes are mutable. Even when the original source has history,
the exact assembled context presented to an agent is not consistently released,
identified, or recoverable. This impedes incident analysis, assurance, audit,
and controlled rollback.

### 2.5 Freshness and lifecycle gaps

Documents may be accessible after their effective period, superseded content
may rank above current content, and ownership is often separated from the
retrieval system. Staleness is usually detected by a user rather than enforced
as a publishing or consumption policy.

### 2.6 Access-control and aggregation risk

Indexing content from several systems can create a new aggregation whose
sensitivity is higher than that of each source. If source entitlements are not
preserved through extraction, indexing, retrieval, and generation, an agent can
disclose information to an unauthorized user even though each source system is
correctly controlled.

### 2.7 Cost and operational duplication

Teams repeatedly crawl, parse, embed, summarize, classify, and relate the same
material. This increases infrastructure and model cost while producing
inconsistent results.

## 3. Why OKF

Google Cloud introduced OKF as an open, vendor-neutral representation for the
metadata, context, and curated knowledge needed by humans and agents. A bundle
is a directory of Markdown files; each non-reserved concept document starts
with YAML frontmatter. The only universally required concept field is `type`.
Producers may extend the metadata, and consumers are expected to tolerate
unknown fields.

OKF v0.2 adds optional first-class signals for:

- provenance through `sources`;
- generation through `generated`;
- independent confirmation through `verified`;
- lifecycle through `status`;
- freshness through `stale_after`; and
- sanctioned, verifiable calculations through `Attested Computation`.

Git is the recommended distribution mechanism because it supplies attribution,
history, diffs, review, and rollback. The specification remains a format rather
than a platform: it does not define a central registry, access control,
retrieval infrastructure, workflow engine, scheduler, or full execution
runtime. This separation allows XYZ Bank to use its existing strategic
platforms and security controls.

Sources: [OKF v0.2 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md),
[Google Cloud introduction](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing),
and [v0.2 trust additions](https://cloud.google.com/blog/products/data-analytics/okf-v0-2-adds-trust-signals/).

## 4. Objectives

The proposed program has ten objectives.

1. Establish a vendor-neutral contract for human- and agent-readable knowledge.
2. Make every published concept attributable to authoritative sources and an
   accountable owner.
3. Release knowledge immutably so a consumer can reproduce, compare, and roll
   back the knowledge it used.
4. Separate authoring, knowledge representation, retrieval, and agent execution
   so each layer can evolve independently.
5. Reuse a knowledge concept across YODA, RACK, search, assistants, portals, and
   future agent platforms without bespoke re-authoring.
6. Apply lifecycle, freshness, classification, and verification policy before a
   concept enters an agent's context.
7. Preserve source-system authorization throughout the knowledge supply chain.
8. Support federated domain ownership under centrally governed interoperability
   and security standards.
9. Reduce duplicate crawling, parsing, enrichment, and embedding.
10. Improve auditability of agent-assisted answers and actions.

## 5. Design principles

- **Complement, do not displace.** Existing systems retain the functions for
  which they are authoritative.
- **Source authority is explicit.** A published concept identifies its source,
  owner, generation method, and verification state.
- **No entitlement widening.** Publishing or indexing never grants access that
  the consumer does not already possess.
- **Human accountability for high-impact knowledge.** Agent-generated content
  cannot self-approve or self-declare human verification.
- **Immutable releases, disposable indexes.** An approved bundle is retained;
  search, vector, and graph indexes can be rebuilt from it.
- **Federated content, common controls.** Domains own meaning and freshness;
  the platform team owns formats, tooling, reliability, and common guardrails.
- **Progressive disclosure.** Consumers discover a small index, then retrieve
  only the concepts necessary for a task.
- **Open core, bank profile.** XYZ Bank adopts the permissive OKF standard and
  overlays a stricter organizational profile.
- **Evidence before autonomy.** Retrieval and answer quality are proven before
  write-back or action-taking capabilities are expanded.

## 6. Scope

### In scope

- An XYZ Bank OKF organizational profile and controlled concept taxonomy.
- Producer adapters for approved enterprise knowledge sources.
- Git-based validation, review, release, signing, retention, and rollback.
- Entitlement-aware publication, serving, and indexing.
- YODA and RACK integration patterns based on confirmed current capabilities.
- Consumption by enterprise search and agentic platforms.
- Freshness, provenance, verification, quality, and operational monitoring.
- Feedback and proposed-change workflows using pull requests or equivalent
  controlled approval.

### Out of scope for the initial proposal

- Replacing Confluence, SharePoint, YODA, RACK, or records-management systems.
- Moving all enterprise documents into Git.
- Treating OKF as the legal system of record.
- Building a new foundation model.
- Using OKF as a workflow or data-pipeline execution engine.
- Permitting autonomous agents to publish directly to production knowledge.
- Copying secrets, credentials, customer data, or unrestricted source content
  into bundles without approved information-control patterns.
- Production use of attested computations before a separately assured executor,
  receipt, attester, and sandbox model exists.

## 7. Options considered

| Option | Description | Benefits | Limitations | Assessment |
|---|---|---|---|---|
| A. Maintain current state | Continue platform-specific ingestion and retrieval | No transformation cost | Duplication, weak portability and inconsistent controls remain | Not strategic |
| B. Select one existing platform as the enterprise repository | Migrate or synchronize all knowledge to one product | Single user experience | High migration cost, lock-in, authorization and record-boundary complexity | Not recommended as a prerequisite |
| C. Adopt OKF as interchange and release format | Existing systems produce and consume a common versioned representation | Portable, incremental, reviewable, compatible with current estate | Requires profile, adapters, governance, and serving controls | **Recommended** |
| D. Build a new end-to-end knowledge platform | Replace authoring, storage, retrieval, and agent layers | Maximum theoretical control | Highest cost, risk, and time; duplicates strategic platforms | Not recommended |

## 8. Recommended solution

Adopt option C through five capabilities:

1. **Enterprise OKF profile** — bank-required metadata, taxonomy, relationship
   vocabulary, quality rules, security labels, lifecycle, and compatibility.
2. **Producer framework** — reusable source connectors, deterministic extraction,
   content decomposition, enrichment, provenance, and change detection.
3. **Controlled knowledge repository** — domain- and entitlement-aligned Git
   repositories with protected branches, ownership rules, validation, and
   immutable releases.
4. **Serving and indexing layer** — authorized distribution plus lexical,
   vector, and graph views derived from a named release.
5. **Consumer and feedback integration** — YODA, RACK, search, and other agents
   consume approved releases and submit corrections through governed change
   workflows.

The [target architecture](02-target-architecture.md) describes these components
in detail.

## 9. Expected outcomes

- One approved representation can serve multiple agent and human experiences.
- Answers can cite a stable concept and its originating source.
- Consumers can pin, compare, and roll back knowledge releases.
- Stale, deprecated, unverified, or unauthorized concepts can be filtered before
  retrieval.
- Domain owners can review knowledge changes using familiar engineering controls.
- Platform replacement no longer requires re-authoring the knowledge corpus.
- Knowledge defects produce traceable changes rather than silent prompt edits.

## 10. Preliminary success measures

Final thresholds require pilot baselines. The following targets are proposed for
critical pilot content:

| Measure | Proposed pilot target |
|---|---:|
| Concepts with a named accountable owner | 100% |
| Concepts linked to one or more authoritative sources | at least 95% |
| Critical concepts within their freshness period | at least 95% |
| Critical concepts with required human or controlled-process verification | 100% |
| Consumer responses identifying bundle release and cited concepts | 100% |
| Unauthorized retrieval in negative entitlement tests | 0 |
| Ability to rebuild an index from an immutable release | demonstrated |
| Ability to roll back a consumer to a prior approved release | demonstrated |
| Improvement in benchmark answer groundedness over current baseline | measurable and approved during pilot |

## 11. Decision and funding request

Authorize discovery and a bounded pilot with architecture, platform, knowledge
management, security, privacy, records management, risk, YODA, RACK, and two
domain representatives. The pilot should produce evidence for a subsequent
production decision; it should not be interpreted as approval for bank-wide
migration or autonomous publication.
