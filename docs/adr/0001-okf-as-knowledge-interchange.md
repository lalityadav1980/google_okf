# ADR-0001: Adopt OKF as the Enterprise Knowledge Interchange and Release Format

- **Status:** Proposed
- **Date:** 2026-08-21
- **Decision owners:** To be assigned by the adopting organisation
- **Scope:** Enterprise agent-ready knowledge architecture

## Context

The adopting organisation's knowledge is distributed across Confluence, SharePoint, YODA, RACK,
code repositories, catalogs, records systems, and other domain platforms.
Agentic consumers need consistent context, but direct source-specific
integrations create duplicated parsing, metadata, indexing, and governance.
Mutable copies also make authority, freshness, provenance, reproducibility, and
rollback difficult.

OKF v0.2 is an open representation of knowledge as Markdown documents with YAML
frontmatter and links. It supports portable bundles, Git-based distribution,
provenance, verification, lifecycle, freshness, and optional attested-computation
contracts. It deliberately does not prescribe authoring, storage, authorization,
retrieval, or execution infrastructure.

## Decision

The adopting organisation will pilot OKF v0.2 as the canonical **interchange and controlled
release format** for agent-ready knowledge.

The decision includes these constraints:

1. Existing platforms remain authoritative according to established ownership
   and records policy.
2. OKF is not designated as the universal authoring platform or legal system of
   record.
3. The adopting organisation will define the stricter VerityKF Enterprise Profile for production.
4. Bundles will be aligned to enforceable authorization boundaries.
5. Production knowledge will be reviewed and published as immutable releases.
6. Search, vector, and relationship indexes will be reproducible derived views.
7. Consumers will authorize before retrieval and retain release/concept trace.
8. Agent-generated changes will use a governed proposal and approval workflow.
9. Autonomous actions and production attested computations are outside the
   initial decision.

## Consequences

### Positive

- Knowledge becomes portable across YODA, RACK, and future consumers.
- Git-style review, versioning, comparison, and rollback become available.
- Provenance, lifecycle, freshness, and verification can be evaluated before
  retrieval.
- Source and consumer platforms can evolve independently.
- Multiple consumers can reuse one approved representation.
- Knowledge-related agent incidents become more reproducible.

### Negative and costs

- The adopting organisation must build or select producer, validation, release, serving, and
  authorization-aware retrieval capabilities.
- Domain owners must accept ongoing curation and freshness responsibilities.
- The permissive base format requires an enterprise profile and compatibility process.
- Path-based concept identity and untyped links need organizational conventions.
- Existing platforms may require new APIs, change feeds, and entitlement mapping.
- A new controlled representation creates retention, privacy, and operational
  responsibilities.

## Alternatives rejected

- **Continue platform-specific integrations:** retains duplication and weak
  portability.
- **Centralize all content in one existing platform:** requires high-risk
  migration and increases product lock-in.
- **Build a new end-to-end knowledge platform:** duplicates strategic services
  and has greater cost and delivery risk.
- **Use vector indexes as the source of truth:** embeddings and chunks are not a
  human-reviewable, portable, or sufficient version contract.

## Validation

The decision remains proposed until a controlled pilot demonstrates:

- source-to-concept provenance and deterministic rebuild;
- entitlement-preserving retrieval with zero unauthorized negative-test results;
- immutable release, index rebuild, and rollback;
- acceptable quality and operational metrics;
- sustainable domain ownership; and
- architecture, security, privacy, records, AI risk, and business approval.

## References

- [OKF v0.2 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
- [Google Cloud OKF introduction](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- [Google Cloud OKF v0.2 trust signals](https://cloud.google.com/blog/products/data-analytics/okf-v0-2-adds-trust-signals/)
