# ADR-0007: Verity Knowledge Fabric project identity

- **Status:** Accepted as the working project identity
- **Date:** 2026-08-22
- **Decision owners:** Enterprise Architecture and Knowledge Platform Engineering

## Context

The framework needs a distinctive, organisation-neutral identity that describes
its purpose without implying that it replaces existing authoring, retrieval, or
agent platforms. Its identifiers must also be coherent across source code,
packages, commands, profiles, schemas, and release artifacts.

The project implements an enterprise framework around Google Cloud's Open
Knowledge Format (OKF). Google Cloud OKF remains the upstream interchange
standard; this repository provides the additional governance, validation,
release, authorization, observability, and assurance capabilities needed for
enterprise agentic use.

## Decision

The project brand is **Verity Knowledge Fabric**, abbreviated **VerityKF**.
“Verity” signals trustworthy, evidence-backed knowledge; “Knowledge Fabric”
describes the governed connective layer across existing sources, pipelines,
release services, consumers, and agents.

The canonical identifiers are:

| Surface | Identifier |
|---|---|
| Project and product name | `Verity Knowledge Fabric` |
| Short name | `VerityKF` |
| GitHub repository | `verity-knowledge-fabric` |
| Python distribution | `verity-knowledge-fabric` |
| Python import package | `verity_kf` |
| Command-line interface | `verity-kf` |
| Enterprise profile ID | `verity-kf` |
| Media-type namespace | `application/vnd.verity.kf.*` |
| Stable identifier namespace | `urn:verity-kf:*` |
| Documentation schema host | `schemas.verity-kf.example.invalid` |

Documentation uses “the adopting organisation” or “the enterprise” when
describing deployment-specific responsibilities. It does not invent an
institution name or claim that an unapproved control exists.

## Migration

This is a breaking pre-release migration from framework version 0.2.0 to
0.2.0. Import paths, the CLI command, artifact names, media types, schema IDs,
the release-manifest location, the profile field namespace, the profile ID, and
the URN prefix move to the canonical identifiers above.

The identity policy advances to version 2.0. Its opaque UUID namespace remains
unchanged, so the UUID component generated from an unchanged source anchor
remains stable. The full concept URN changes because its human-readable prefix
is part of the public identifier.

No compatibility alias is retained for the former project identity. The
framework is pre-release, and retaining that name would make contracts and
documentation ambiguous. Any pilot artifact produced with the earlier
namespace must be regenerated and revalidated before promotion.

## Name validation and approval

A preliminary technical collision scan on 2026-08-22 found no exact project
name in GitHub repository/code search and no matching distribution registered
on PyPI. This is not trademark or legal clearance. Before external launch,
DEC-001 requires Legal and the Open Source Program Office to approve the name,
repository license, distribution boundary, and contribution model.

## Consequences

- Contributors and automation have one naming map across every public surface.
- The project remains clearly attributed to, but distinct from, Google Cloud
  OKF.
- Existing Confluence, SharePoint, YODA, RACK, and other enterprise platforms
  retain their validated producer or consumer roles.
- Pre-0.2.0 pilot artifacts are intentionally incompatible and must not be
  admitted as VerityKF 0.2 releases.

## Rollback

Before an externally approved release, the working brand can be replaced by
accepting a superseding ADR and applying another coordinated namespace
migration. After external release, a rename requires a deprecation and
compatibility plan rather than an in-place substitution.
