# Assumptions, Decisions, and Open Questions

## 1. Working assumptions

These assumptions prevent the proposal from inventing facts about the adopting organisation.
They must be validated during discovery.

| ID | Assumption | Design consequence if true | Consequence if false |
|---|---|---|---|
| A-01 | Confluence and SharePoint contain overlapping but independently governed knowledge | Both require producers and source-precedence policy | Simplify source landscape and ownership model |
| A-02 | YODA and RACK provide one or more internal knowledge, search, catalog, retrieval, orchestration, or agent capabilities | Integrate them as producers/consumers rather than replace them | Reassign the integration roles to validated platforms |
| A-03 | Existing identity and authorization services can evaluate user/workload access centrally | Use policy references and pre-retrieval checks | A new authorization integration becomes a critical dependency |
| A-04 | Approved enterprise Git and artifact services are available | Use protected review and immutable releases | Select equivalent controlled version/release services |
| A-05 | Source APIs expose stable record IDs, versions, and usable entitlement metadata | Support incremental, traceable publishing | Some sources require reconciliation, export, or restricted scope |
| A-06 | The initial pilot can exclude customer data and restricted information | Reduce pilot risk and accelerate evidence | Expand privacy, residency, and control work before build |
| A-07 | The initial consumer can remain read-only and advisory | Focus on retrieval and knowledge controls | Action authorization and safety become pilot blockers |
| A-08 | Domain owners can review critical knowledge | Use federated curation and verification | Pilot cannot establish accountable production knowledge |

## 2. Architecture decisions proposed

| ID | Decision | Status | Rationale |
|---|---|---|---|
| D-01 | Use OKF as interchange and controlled release format, not the universal authoring system | Proposed | Complements existing platforms and reduces lock-in |
| D-02 | Keep source systems authoritative for records and operational facts | Proposed | Avoids ambiguous authority and uncontrolled migration |
| D-03 | Add the stricter VerityKF Enterprise Profile | Proposed | Base OKF conformance is insufficient for regulated production use |
| D-04 | Partition bundles by authorization boundary before domain convenience | Proposed | Prevents entitlement widening and unsafe aggregation |
| D-05 | Publish immutable releases; treat indexes as reproducible derivatives | Proposed | Enables audit, rollback, and consumer reproducibility |
| D-06 | Require governed pull requests for production knowledge changes | Proposed | Provides accountable review and separation of duties |
| D-07 | Keep AI enrichment optional and independently reviewed | Proposed | Limits semantic drift and unsupported authority |
| D-08 | Use authorization-aware hybrid retrieval outside OKF | Proposed | OKF is a representation, not a retrieval or ACL system |
| D-09 | Defer autonomous write-back and material actions | Proposed | Establish evidence and controls before increasing autonomy |
| D-10 | Defer production attested computations | Proposed | OKF v0.2 does not provide the complete runtime assurance model |
| D-11 | Use Verity Knowledge Fabric (VerityKF) as the organisation-neutral project identity | Accepted | Creates one coherent brand and namespace across packages, profiles, artifacts, and documentation |

Formal rationale for D-01 is recorded in
[ADR-0001](adr/0001-okf-as-knowledge-interchange.md).
The project identity and namespace decision is recorded in
[ADR-0007](adr/0007-verity-knowledge-fabric-project-identity.md).

## 3. Discovery questions

### YODA and RACK

1. What business capabilities does each platform own today?
2. Which is an authoring system, catalog, search/index, retrieval service, agent
   runtime, orchestration layer, or user experience?
3. What content does each store, copy, transform, or reference?
4. Which platform is authoritative for each knowledge type?
5. What identity, entitlement, source citation, version, and audit capabilities
   already exist?
6. Which integrations and indexes are duplicated between them?
7. What strategic roadmaps or decommissioning constraints apply?

### Confluence and SharePoint

1. Which spaces/sites/libraries are in pilot scope?
2. Are pages/documents records, working material, or published knowledge?
3. How are versions, owners, approvals, classification, retention, and ACLs
   represented?
4. Are webhooks/change feeds available and reliable?
5. What content must not be exported, embedded, summarized, or logged?

### Security, privacy, and records

1. What is the authoritative classification vocabulary?
2. Can the entitlement service evaluate access at concept retrieval time?
3. What regional and legal-entity restrictions apply to content and embeddings?
4. Are Git history and release artifacts records for any pilot knowledge type?
5. What deletion, legal-hold, and emergency-withdrawal objectives apply?
6. Which models and processing locations are approved for enrichment and
   consumption?

### Product and operations

1. Which user tasks currently fail or require excessive discovery time?
2. What benchmark questions and expected sources can measure improvement?
3. What are acceptable source-change, entitlement-change, and withdrawal SLOs?
4. Which team owns knowledge incidents and consumer rollback?
5. What volume, change rate, concept count, and concurrency should be designed
   for?
6. What are the acceptable unit costs for publication, storage, indexing, and
   retrieval?

## 4. Decisions required before pilot build

- Named executive sponsor and accountable product owner.
- Confirmed YODA and RACK capability map.
- Approved source collections and source owners.
- Approved read-only consumer and user group.
- Authoritative classification and entitlement patterns.
- Pilot repository, artifact, model, and regional deployment choices.
- VerityKF profile v0.2 field and taxonomy approval.
- Benchmark, success thresholds, and risk-acceptance authorities.
- Content exclusions and incident/escalation process.

## 5. Decisions intentionally deferred

- Enterprise-wide repository topology.
- Full regulatory and customer-service use cases.
- Autonomous knowledge maintenance or production action.
- Production attested-computation runtime.
- Long-term OKF registry or federation protocol beyond the pilot release catalog.
- Migration or retirement of any existing platform.
- Organization-wide profile v1.0 until pilot evidence is available.
