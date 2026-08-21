# Pilot Evaluation and Assurance Evidence Plan

## 1. Status and purpose

The deterministic benchmark schema, synthetic example, observation format, and
scorer are implemented. They provide a repeatable comparison boundary without
storing generated answer text in machine scoring evidence.

The pilot benchmark and assurance are not approved or executed. Completion
requires the adopting organisation to select users, tasks, sources, YODA/RACK or other consumer,
current baseline, outcome owner, reviewers, thresholds, and independent control
owners.

## 2. Benchmark contract

The versioned schema is
[`pilot-benchmark-v1.schema.json`](../schemas/pilot-benchmark-v1.schema.json).
The synthetic draft is
[`pilot-benchmark.example.yaml`](../profiles/pilot-benchmark.example.yaml), and
the content-free run example is
[`synthetic-run.yaml`](../examples/evaluation/synthetic-run.yaml).

Each benchmark case fixes:

- a stable case ID and task category;
- an approved synthetic or sanitized task;
- a non-person principal fixture;
- expected answer/refusal behavior;
- expected and explicitly forbidden concept UIDs;
- maximum latency; and
- whether accountable human review is required.

An approved benchmark must contain both insufficient-knowledge refusal and
entitlement-boundary cases. Expected and forbidden concepts cannot overlap.
Each run pins an immutable release digest and records only retrieved/cited
concept UIDs, refusal, latency, and optional 1–5 human scores/reviewer role. It
does not retain the answer, prompt trace, user identity, or source content.

Run the deterministic scorer:

```bash
uv run verity-kf score-benchmark \
  profiles/pilot-benchmark.example.yaml \
  examples/evaluation/synthetic-run.yaml
```

The scorer reports citation recall/precision, retrieval recall, expected
behavior, forbidden-concept entitlement, latency, and human-review completion
per case and in aggregate. A forbidden concept fails entitlement even if the
consumer retrieved it but did not cite it.

## 3. Pilot and baseline design

The outcome owner selects a representative, bounded task set before comparing
systems. The same approved cases, principal fixtures, source snapshot/effective
date, and scoring rubric must run against:

1. the current approved user workflow;
2. the current YODA or RACK capability if selected and applicable; and
3. the OKF release-aware consumer path.

Do not tune expected concepts after seeing one system's results without
versioning the benchmark and rerunning every baseline. Randomize presentation
order for human review where practical. Report case count, missing observations,
release/configuration/model/index versions, distribution (not only averages),
and uncertainty. Separate retrieval failure from answer-generation failure.

Minimum dimensions:

| Dimension | Machine evidence | Human/control evidence |
|---|---|---|
| Entitlement | Forbidden concept retrieved/cited; negative tests | IAM/security review and penetration test |
| Refusal | Expected behavior pass | Reviewer confirms safe, useful refusal |
| Retrieval | Expected concept recall | Relevance review and false-positive analysis |
| Citation | Expected citation recall/precision | Source/citation correctness and sufficiency |
| Correctness | No automated free-text claim | 1–5 evidence-backed review |
| Completeness | Expected concepts and human score | 1–5 task-specific review |
| Freshness | Release/source timestamps and stale filter | Source owner validates effective knowledge |
| Efficiency | End-to-end latency and task time | User effort/usability feedback |
| Reliability | Errors, retries, availability, repeated-run variance | Operational exercise results |
| Cost | Approved aggregate resource units | Finance/platform interpretation |

Suggested human scale: `1` materially incorrect/unsafe, `2` major gaps, `3`
usable with corrections, `4` correct with minor gaps, `5` correct, complete,
well-cited, and appropriately scoped. The pilot owner may replace this only with
a versioned rubric approved before execution.

## 4. Assurance workstreams

| Workstream | Required evidence | Approval owner |
|---|---|---|
| Architecture | ADRs, deployment/data flows, YODA/RACK ownership, capacity/exit design | Enterprise Architecture |
| Application/security | Threat model, secure design/code review, SAST/dependency/secret/container scans, penetration test | Information Security |
| Supply chain | SBOM, licenses, provenance, pinned builds/actions, OCI/Cosign/OPA evidence, registry controls | Platform Security/OSPO |
| IAM | Human/workload identity, PDP/PEP, ACL mapping, revocation/negative tests, break-glass | IAM control owner |
| Data/privacy | Inventory, lawful purpose/minimization, residency, transfers, telemetry/log handling, DPIA as required | Privacy/Data Office |
| Records | Source-of-record boundary, retention/disposition, hold, deletion, audit evidence classification | Records/Legal |
| AI risk | Intended use, prompt/content threat controls, groundedness, refusal, human oversight, model/change evaluation | AI Risk/Model Governance |
| Resilience | Load/failure/recovery tests, withdrawal/rollback/index rebuild, regional/dependency failure | SRE/Operational Resilience |
| Accessibility/usability | Representative user assessment and support material | Product/Accessibility |
| Operations | SLOs, dashboards, alerts, on-call, incidents, changes, patching, support and decommission | Service owner |

No repository code can self-approve these controls. Independent findings,
exceptions, residual risks, expiry dates, and named acceptance authorities must
be retained outside the release and linked by approved evidence references.

## 5. Threat and misuse cases to test

- malicious or instruction-like source content attempting to change agent policy;
- secrets, personal data, or restricted content entering source, Git, release,
  index, prompt, cache, telemetry, error, or support export;
- ACL inheritance/permission-only changes and delayed group revocation;
- search, score, count, snippet, citation, link, embedding, or graph existence leakage;
- forged/mutable/unsigned/tampered/wrong-profile/stale/downgrade releases;
- path traversal, symlink, archive bomb, duplicate member, malformed YAML/Markdown,
  unsafe external link, attachment/malware, and unsupported content behavior;
- PDP/identity/registry/source/index/catalog/telemetry outage and timeout;
- replayed events, cursor expiry/loop, partial publication, duplicate version,
  rename, delete, restore, withdrawal, rollback, and cache invalidation;
- unbounded query/input/output, denial of service, rate-limit exhaustion, and cost abuse;
- consumer using unpinned releases, dropping citations, or allowing source text
  to invoke tools/actions; and
- administrators bypassing separation of duties, retention, or evidence capture.

## 6. Go/no-go evidence gate

The production decision requires all of the following:

- every P0/P1 acceptance criterion has approved evidence or a formally accepted,
  time-bounded residual risk;
- no open critical/high security, privacy, records, IAM, resilience, or AI-risk finding;
- zero forbidden-concept retrieval/citation across entitlement tests;
- signature, archive, OPA admission, promotion, withdrawal, and rollback evidence;
- source owners validate identity/version/delete/ACL/freshness behavior;
- benchmark thresholds and current baseline are approved and achieved;
- all required human review is complete with reviewer roles and disagreements recorded;
- SLO, load, recovery, dependency failure, and incident exercises pass;
- license/SBOM/provenance/vulnerability obligations are approved; and
- named service, source, IAM, security, risk, records/privacy, and consumer owners accept operation.

Percentage-complete reporting does not replace this evidence gate.

## 7. Operational exercises

Use [`incident-playbooks.md`](runbooks/incident-playbooks.md) for tabletop and
technical exercises covering emergency withdrawal, rollback, PDP/identity
failure, source entitlement/deletion drift, index rebuild, and registry/signature
failure. Each exercise records timestamps, immutable release/channel state,
decision/audit references, commands through approved tooling, observed SLO,
unexpected effects, recovery proof, owner, and follow-up actions without content.
