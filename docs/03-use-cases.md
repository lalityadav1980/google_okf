# Enterprise Use-Case Catalog

## 1. Selection criteria

An OKF use case is attractive when several consumers need the same curated
knowledge, the current content has identifiable authoritative sources, and
versioning, provenance, freshness, or portability is material.

Use cases should be scored against:

- business and customer impact;
- regulatory, operational, or technology risk;
- source authority and ownership maturity;
- entitlement complexity;
- change frequency and freshness requirements;
- number of consumers and duplicated integrations;
- ability to measure answer or task quality;
- content sensitivity and residency;
- feasibility of human verification; and
- reversibility of an incorrect answer or action.

OKF is less suitable where content is primarily transactional, requires
millisecond state, lacks an authoritative source, or must be executed as a
workflow rather than described as knowledge.

## 2. Prioritized use cases

### UC-01: Enterprise policy and procedure navigation

**Problem:** Policies, standards, procedures, controls, FAQs, and local guidance
are spread across SharePoint, Confluence, and specialist repositories. Users and
agents can retrieve a relevant document but struggle to determine applicability,
effective version, controlling policy, or required procedure.

**OKF application:** Publish one concept per policy, standard, procedure, control,
exception process, or supporting definition. Link hierarchy, applicability,
jurisdiction, legal entity, owner, source record, effective date, verification,
and supersession.

**Consumers:** Employee assistants, policy portals, control teams, service desks,
and compliance tooling.

**Value:** Better navigation, source citation, consistent effective-version
selection, and reduced duplication.

**Guardrail:** The source records system remains authoritative. Legal or
compliance conclusions must follow the approved human-review policy.

### UC-02: Technology service and application knowledge

**Problem:** Service ownership, architecture, dependencies, APIs, data flows,
support arrangements, recovery requirements, and lifecycle information live in
different platforms.

**OKF application:** Represent applications, services, APIs, events, dependencies,
business capabilities, owners, support groups, architecture decisions, and
authoritative catalog links as connected concepts.

**Consumers:** Engineering assistants, solution architects, change teams,
operations, service management, and technology risk.

**Value:** Faster impact analysis, onboarding, architecture discovery, and
ownership resolution.

**Guardrail:** Runtime configuration and live health remain in operational
systems; OKF provides curated context and links.

### UC-03: Operational runbooks and incident support

**Problem:** Alerts and service records are often disconnected from the latest
runbook, dependency map, known-error guidance, escalation route, and recovery
evidence.

**OKF application:** Link alert types, services, failure modes, runbooks,
dashboards, escalation paths, recovery objectives, dependencies, and post-incident
learning.

**Consumers:** Operations assistants, service desks, site reliability teams, and
incident coordinators.

**Value:** Reduced discovery time and more consistent use of approved recovery
procedures.

**Guardrail:** Agents should recommend or navigate before they are permitted to
execute. Any automated action remains subject to operational authorization,
change, and safety controls outside OKF.

### UC-04: Engineering standards and software-delivery knowledge

**Problem:** Development standards, approved patterns, examples, platform
capabilities, reusable libraries, and exception routes are difficult to discover
and become inconsistent across repositories.

**OKF application:** Publish standards, reference architectures, API conventions,
secure-coding requirements, platform capabilities, templates, examples, and
architecture decisions with links to immutable source versions.

**Consumers:** Coding agents, developer portals, architecture assistants, CI
checks, and engineering teams.

**Value:** Consistent agent context, better standards adoption, and reduced
reinvention.

**Guardrail:** Executable artifacts remain in signed source or package
repositories. OKF references rather than replaces them.

### UC-05: Data-product and business-definition catalog

**Problem:** Data ownership, meaning, lineage, quality expectations, permissible
use, schemas, and business definitions are distributed across catalogs,
documents, and implementation code.

**OKF application:** Represent data products, datasets, schemas, terms, metrics,
quality rules, owners, lineage summaries, usage policy, and examples. Reference
authoritative catalog and schema resources.

**Consumers:** Data assistants, analysts, governance teams, engineers, and
reporting platforms.

**Value:** Shared definitions, source transparency, and portable agent context.

**Guardrail:** Do not copy production data into the knowledge bundle. Entitlements
to metadata and examples must be preserved.

### UC-06: Regulatory obligation and control traceability

**Problem:** Regulatory publications, internal obligations, policies, controls,
procedures, systems, evidence requirements, owners, and assessments are connected
through platform-specific or manual mappings.

**OKF application:** Publish curated obligation and control concepts with links
to official sources, applicability, interpretations, policies, controls,
procedures, owners, and evidence locations.

**Consumers:** Compliance research assistants, control owners, risk assessment,
audit preparation, and change-impact analysis.

**Value:** Navigable provenance and more consistent traceability across systems.

**Guardrail:** Regulatory interpretation requires accountable legal/compliance
review. OKF is not the official evidence store unless separately designated.

### UC-07: Customer-service knowledge distribution

**Problem:** Customer-facing guidance changes across products, jurisdictions,
channels, and effective dates. Multiple channel systems can hold inconsistent
copies.

**OKF application:** Publish approved product guidance, eligibility explanations,
service procedures, disclosures, escalation paths, and channel applicability as
versioned concepts.

**Consumers:** Staff assistants, customer-service tooling, digital support, and
quality assurance.

**Value:** Reuse of one approved representation across channels and improved
effective-version control.

**Guardrail:** This is a high-impact use case. Suitability, advice, complaints,
vulnerability, privacy, and jurisdiction controls must be enforced outside the
format. Begin only after lower-risk use cases prove the control plane.

### UC-08: Enterprise agent context interoperability

**Problem:** Every agent team creates its own prompt library, document chunks,
metadata, and source connectors. Knowledge cannot move safely between YODA,
RACK, and future agent platforms.

**OKF application:** Standardize the approved knowledge contract while allowing
each consumer to build a retrieval index optimized for its tasks.

**Consumers:** YODA, RACK where applicable, enterprise agent platforms, coding
agents, and specialist copilots.

**Value:** Reduced integration duplication and lower platform lock-in.

**Guardrail:** Sharing a format does not imply sharing an authorization scope.
Consumers receive only authorized bundles and concepts.

### UC-09: Knowledge lifecycle and remediation

**Problem:** Organizations often know how much content they store but not how much
has an owner, source, freshness deadline, approval state, or active consumer.

**OKF application:** Use frontmatter and release telemetry to create dashboards
for ownership, source health, staleness, deprecation, verification, broken links,
and consumption.

**Consumers:** Knowledge managers, domain owners, platform operations, risk, and
records management.

**Value:** A measurable knowledge-control process and targeted remediation.

### UC-10: Controlled, attested enterprise computations

**Problem:** Agents can paraphrase or rewrite a calculation and present a result
without proof that an approved definition was executed.

**OKF application:** Use an `Attested Computation` concept to reference a
sanctioned computation, controlled executor, required receipt, and deterministic
attester.

**Consumers:** Approved analytics or reporting assistants.

**Value:** Separation of approved definition, execution evidence, and displayed
result.

**Guardrail:** Treat as a later-stage use case. The bank must define and assure
the execution sandbox, parameter binding, receipt integrity, attester ABI,
authorization, segregation of duties, and record retention.

## 3. Recommended pilot use cases

Use a two-domain pilot:

1. **Technology service and runbook knowledge** sourced primarily from
   Confluence and a structured service/catalog source. This provides clear
   concepts, relationships, owners, and operational benchmarks without customer
   data.
2. **Enterprise policy and procedure navigation** sourced from a controlled
   SharePoint collection. This tests document versions, effective dates,
   accountable verification, lifecycle, and entitlement preservation.

Select one controlled YODA or RACK consumer after validating their current
roles. The pilot should remain read-only and advisory.

## 4. Use cases explicitly deferred

- Autonomous customer decisions or communications.
- Legal or regulatory conclusions without human review.
- Agent-originated production changes.
- Storage of credentials, authentication material, or raw customer data.
- Real-time operational state as OKF documents.
- Replacement of workflow, records, case-management, or transaction systems.
- Attested computations used for material reporting before the runtime control
  model is approved.
