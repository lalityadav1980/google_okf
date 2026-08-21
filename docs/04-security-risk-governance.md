# Security, Risk, and Governance

## 1. Control objective

The OKF capability must improve knowledge portability without weakening any
source-system control. A user, workload, or agent must never gain knowledge
access merely because content has been exported, linked, indexed, summarized,
or placed in the same bundle as content it can access.

OKF frontmatter is descriptive metadata. Fields such as `classification` or
`acl_ref` may inform policy enforcement, but the file format is not an
authorization mechanism. Enforcement belongs to identity, policy, repository,
release, serving, retrieval, model, and application controls.

## 2. Trust boundaries

Treat each of the following as a separate trust boundary:

1. source system to producer;
2. deterministic extractor to AI enrichment;
3. producer workspace to controlled Git repository;
4. reviewed repository to immutable release store;
5. release store to each search or relationship index;
6. index to retrieval gateway;
7. retrieval gateway to model context;
8. model output to user or downstream tool; and
9. feedback/write-back path to the production repository.

Authentication, authorization, integrity, audit, and data-loss controls must be
defined at every boundary.

## 3. Information security controls

### 3.1 Data minimization

- Prefer metadata, summaries, definitions, and source references over full
  duplication of sensitive documents.
- Prohibit credentials, keys, secrets, authentication tokens, and private-key
  material from bundles.
- Prohibit raw customer, employee, or transaction data in the initial profile.
- Use synthetic examples unless a separately approved pattern allows otherwise.
- Scan both frontmatter and Markdown bodies before merge and before release.

### 3.2 Classification and handling

Every production concept must carry an organisation-approved classification. The initial
profile proposes `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, and `RESTRICTED` as
placeholder values; the adopting organisation's authoritative classification policy prevails.

Classification determines, at minimum:

- eligible repository and storage zone;
- encryption and key requirements;
- permitted regions;
- producer and reviewer roles;
- eligible models and agent runtimes;
- logging and redaction behavior;
- retrieval and output controls; and
- retention and disposal.

Bundles should not mix materially different access populations simply because
the concepts belong to the same business domain. Partition first by enforceable
access boundary, then by domain and scale.

### 3.3 Entitlement preservation

The producer must capture a stable reference to source authorization policy or
entitlement groups. The publication pipeline must fail closed when the policy
cannot be resolved.

At consumption time:

1. authenticate the user and calling workload;
2. evaluate current authorization, not a model-generated interpretation;
3. apply filters before lexical, vector, or graph candidates reach the model;
4. protect relationship expansion and backlinks with the same policy;
5. prevent snippets, titles, embeddings, and logs from leaking unauthorized
   information; and
6. run negative tests for direct, inferred, and cross-concept disclosure.

Copying source ACL strings into YAML is insufficient. Group membership changes,
conditional access, legal restrictions, and source removals must propagate to
the serving policy within an approved service-level objective.

### 3.4 Integrity and supply-chain controls

- Use protected repositories and approved workload identities.
- Require verified provenance for producer builds.
- Generate deterministic output where feasible.
- Record source version and source checksum.
- Sign or otherwise attest the release manifest and bundle digest.
- Verify signatures/digests before indexing and serving.
- Retain compiler, extractor, model, prompt, policy, and dependency versions in
  build evidence.
- Scan executable references and never execute code merely because a Markdown
  document links to it.
- Separate publisher, approver, and production operator privileges.

### 3.5 Prompt-injection and content-safety controls

Source documents are untrusted input even when they originate inside the adopting organisation.
They may contain obsolete instructions, malicious content, copied third-party
text, or language that an agent incorrectly treats as system direction.

Consumers must:

- distinguish retrieved data from system and developer instructions;
- neutralize active content and unsupported URI schemes;
- restrict tool use through deterministic policy;
- allowlist outbound network destinations where tools can navigate links;
- limit relationship traversal and context size;
- scan and classify outputs;
- cite retrieved concepts and source resources; and
- require confirmation or approval before material actions.

### 3.6 Privacy and residency

Privacy assessment must cover extraction, enrichment, embedding, prompts, model
telemetry, logs, cached contexts, feedback, and support access—not only the Git
files. Cross-border movement of derived data or embeddings must follow the same
analysis as source content.

## 4. Knowledge governance

### 4.1 Source authority

Each concept must identify one accountable owner and one or more sources. A
domain policy must establish precedence when sources conflict. The producer
must not silently combine incompatible statements into an apparently
authoritative summary.

Recommended conflict outcomes are:

- block publication pending owner resolution;
- publish both concepts with a visible conflict status in non-critical use
  cases; or
- publish the designated authoritative concept and link the superseded source.

### 4.2 Generation and verification

OKF v0.2 separates `generated` from `verified`. The adopting organisation should use that
separation as follows:

- `generated.by` records the human, process, tool, and version that last made a
  meaningful content change.
- `verified` records independent confirmations against sources or the underlying
  resource.
- An AI producer cannot verify its own output.
- A `human:` verification must correspond to an authenticated, attributable
  reviewer event.
- A `process:` verification must point to an approved deterministic control and
  retained evidence.
- Verification requirements are determined by concept type, classification,
  criticality, and use case.

### 4.3 Lifecycle and freshness

Use `status: draft | stable | deprecated` according to the OKF specification.
Use an absolute `stale_after` timestamp. VerityKF profile extensions may add
`effective_from`, `effective_to`, and `supersedes` where business validity is
different from knowledge freshness.

Consumer policy should distinguish:

- **draft:** available only to explicitly approved development or review uses;
- **stable/current:** eligible subject to authorization and verification;
- **deprecated:** retained for history but excluded from normal answers; and
- **stale:** blocked or visibly warned according to use-case criticality.

Deleting a source, revoking an entitlement, or discovering material error may
require emergency withdrawal before the normal release cycle.

### 4.4 Records management

The records-management owner must determine whether an OKF concept, pull-request
approval, release manifest, retrieval log, or agent output is a business record.
The design must then apply the relevant retention, legal hold, deletion, and
disposition schedule.

Git history is not automatically a compliant records-management solution, and
the right to erase or correct data may conflict with indefinite repository
retention. Restricted personal data should therefore be excluded unless a
specific lifecycle architecture is approved.

## 5. AI and model risk controls

The format does not remove model risk. Each consuming use case still requires:

- use-case classification and accountable business owner;
- benchmark questions and expected sources;
- groundedness, completeness, citation, and refusal evaluation;
- testing for stale, conflicting, poisoned, and unauthorized content;
- model and prompt change control;
- human oversight appropriate to impact;
- explainability and trace evidence;
- hallucination and over-reliance controls;
- fallback and service-degradation behavior; and
- periodic revalidation.

Knowledge release ID, retrieval policy version, concept IDs, source references,
model version, prompt/policy version, tool calls, and output disposition should
be traceable for material interactions, subject to privacy and retention policy.

## 6. Threat and risk register

| Risk | Example consequence | Primary mitigations | Owner class |
|---|---|---|---|
| Unauthorized aggregation | A user infers restricted information through links or snippets | Access-aligned bundles, pre-retrieval authorization, negative tests | Security/platform |
| Stale knowledge | An agent applies superseded guidance | `stale_after`, effective dates, owner alerts, policy gates | Domain owner |
| Incorrect AI enrichment | A generated summary changes meaning | Source citations, deterministic extraction, independent review, benchmark tests | Producer/domain |
| Source drift | The source changes without a new bundle | Webhook/polling reconciliation, checksums, SLOs, fail-closed critical use | Source owner |
| Conflicting authority | Two platforms publish different current concepts | Source-precedence registry and conflict workflow | Governance/domain |
| Prompt injection | Retrieved text redirects an agent or tool | Content isolation, tool policy, output controls, adversarial testing | Agent platform |
| Release tampering | A modified bundle is indexed | Signed manifest, digest verification, protected artifact store | Platform/security |
| Path identity instability | A file rename breaks references and history | Stable-ID extension, redirects/aliases, rename checks | Profile owner |
| Sensitive logging | Context or snippets appear in telemetry | Classification-aware redaction and approved log stores | Platform/privacy |
| Spec immaturity | Future OKF changes disrupt consumers | Profile versioning, compatibility tests, adapters, pinning | Architecture |
| Scale degradation | Large Git trees or indexes slow publication | Domain partitioning, incremental builds, release catalog | Platform |
| Orphaned ownership | Concepts remain published after team changes | Owner-directory validation and escalation | Governance |
| Excessive agent autonomy | Knowledge write-back becomes unreviewed truth | PR-only feedback, separation of duties, no direct production writes | Risk/platform |

## 7. Mandatory production gates

A production release must not be created unless:

- OKF syntax and VerityKF Enterprise Profile validation pass;
- classification, owner, source, lifecycle, and authorization references exist;
- required verification is present and current;
- secret, sensitive-data, malware, and link scans pass;
- source versions and checksums are recorded;
- broken-link policy passes for the release tier;
- domain and control-owner approvals are recorded;
- release manifest and digest are created;
- compatibility tests pass for supported consumers; and
- rollback and emergency-withdrawal mechanisms are operational.

## 8. Assurance evidence

The pilot should retain:

- approved architecture and threat model;
- data-flow and access-control design;
- source-to-concept lineage samples;
- producer and validator test evidence;
- pull-request review evidence;
- release manifest and integrity verification;
- positive and negative entitlement tests;
- retrieval and answer evaluation results;
- stale/deprecated/conflict test results;
- rollback and index-rebuild exercise results; and
- residual risks with named acceptance authorities.
