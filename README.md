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
