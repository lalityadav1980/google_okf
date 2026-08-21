# VerityKF Enterprise Profile

## 1. Purpose and status

This document proposes an enterprise profile layered on top of OKF v0.2.
It is a design input, not an approved enterprise standard. Field names, classifications,
identity conventions, and concept types must be reconciled with existing enterprise
taxonomies before implementation.

The base OKF specification intentionally requires only `type`. The adopting organisation requires
additional metadata for production use. A document may therefore be valid OKF
but fail the stricter VerityKF Enterprise Profile.

## 2. Compatibility rules

1. Preserve the meaning of all standard OKF v0.2 fields.
2. Preserve unknown fields when reading and writing a document.
3. Represent human-readable relationships with normal Markdown links even when
   typed relationship extensions are also present.
4. Do not redefine `verified` as authorization or formal policy approval.
5. Do not redefine `stale_after` as the legal effective-until date.
6. Declare `okf_version: "0.2"` only in the root `index.md` frontmatter.
7. Carry Enterprise Profile and bundle release information in the release manifest,
   not by changing the meaning of `okf_version`.
8. Consumers must degrade gracefully when they do not understand a VerityKF
   extension; enterprise production consumers may reject content that does not meet
   the Enterprise Profile.

## 3. Controlled concept types

The pilot should use a small vocabulary and expand only through profile change
control.

| Type | Intended meaning |
|---|---|
| `Policy` | Mandatory principles and management intent |
| `Standard` | Mandatory requirements supporting policy |
| `Procedure` | Approved steps for performing an activity |
| `Control` | Activity or mechanism that mitigates a risk or meets an obligation |
| `Regulatory Obligation` | Curated statement linked to an authoritative regulatory source |
| `Business Term` | Approved definition used across one or more domains |
| `Business Capability` | Stable description of what the organization does |
| `Application` | Governed application or system concept |
| `Technology Service` | Consumable technology service and operating context |
| `API` | API purpose and context, referencing the canonical contract |
| `Event` | Business or technology event definition |
| `Data Product` | Governed data product context and usage policy |
| `Dataset` | Dataset metadata and context, without copying production data |
| `Metric` | Approved definition and interpretation of a measure |
| `Pipeline` | Knowledge about a processing or delivery pipeline, not its execution |
| `Runbook` | Approved operational diagnostic or recovery guidance |
| `Architecture Decision` | Decision, context, consequences, and supersession |
| `Reference` | Mirrored or summarized supporting material |
| `Attested Computation` | OKF v0.2 sanctioned-computation contract; later-stage use only |

Consumers must still tolerate unknown types to remain OKF-compatible. Production
publication of a new enterprise type requires profile-owner approval.

## 4. Metadata requirements

### 4.1 Standard OKF fields

| Field | Pilot requirement | Purpose |
|---|---|---|
| `type` | Required | Routing, validation and presentation |
| `title` | Required | Stable human-readable name |
| `description` | Required | One-sentence discovery summary |
| `resource` | Required unless abstract and approved | Canonical source/asset URI |
| `tags` | Recommended | Cross-cutting discovery labels |
| `sources` | Required for production concepts | Provenance and per-source credibility signals |
| `generated` | Required | Identity/version and time of meaningful content generation |
| `verified` | Risk-based | Independent confirmation against sources or resource |
| `status` | Required | `draft`, `stable`, or `deprecated` |
| `stale_after` | Required for production concepts | Absolute freshness deadline |

### 4.2 Proposed VerityKF extensions

These fields are extensions, not part of the base OKF v0.2 vocabulary.

| Field | Pilot requirement | Purpose |
|---|---|---|
| `verity_profile_version` | Required | VerityKF Enterprise Profile used to validate the concept |
| `concept_uid` | Required | Enterprise-stable identity resilient to path changes |
| `domain` | Required | Accountable knowledge domain |
| `owner` | Required | Group or role accountable for meaning and freshness |
| `classification` | Required | Enterprise information-classification label |
| `acl_ref` | Required | Reference to enforceable authorization policy; not an ACL itself |
| `criticality` | Required | `low`, `moderate`, `high`, or organisation-approved equivalent |
| `jurisdictions` | Conditional | Geographic applicability |
| `legal_entities` | Conditional | Legal-entity applicability |
| `effective_from` | Conditional | Start of business or policy applicability |
| `effective_to` | Conditional | End of business or policy applicability |
| `supersedes` | Conditional | Prior concept ID or source resource replaced |
| `source_record_id` | Required for managed source content | Stable upstream record identity |
| `source_version` | Required | Upstream document, page, schema, or commit version |
| `relationships` | Optional | Machine-readable typed relationship extension |

The adopting organisation should consider using an extension namespace if shared tooling risks
collisions with future OKF fields. That decision belongs in profile v1.0.

Per-concept digests should normally live in the release manifest. This avoids a
self-referential hash inside the content it protects and allows integrity to be
verified before parsing a concept.

## 5. Actor convention

Follow OKF v0.2 actor syntax:

- tools and agents: `<producer>/<version>`, for example
  `verity-kf-sharepoint-producer/1.2.0`;
- people: `human:<stable-id>`; and
- automated processes: `process:<stable-id>`.

Avoid names, email addresses, or other unnecessary personal data where a stable
enterprise subject identifier or role can provide accountability.

## 6. Typed relationship extension

OKF links are intentionally untyped. An adopting organisation may add a `relationships` list for
machine routing while retaining a normal Markdown link in the body:

```yaml
relationships:
  - type: governed-by
    target: /policies/change-management-policy.md
  - type: operated-by
    target: /teams/platform-operations.md
  - type: depends-on
    target: /services/enterprise-identity.md
```

Initial relationship vocabulary:

- `governed-by`
- `implements`
- `supersedes`
- `depends-on`
- `produces`
- `consumes`
- `operated-by`
- `owned-by`
- `evidenced-by`
- `applies-to`

Direction and inverse semantics must be defined centrally. A producer must not
create a typed relationship merely because an LLM inferred a plausible link.

## 7. Illustrative concept

The following is an example of structure only. It is not a policy or
approved control statement.

```markdown
---
type: Standard
title: Enterprise Production Change Standard
description: Illustrative requirements for controlled changes to production technology services.
resource: https://sharepoint.example.invalid/records/standards/production-change
tags: [technology, change-management, operations]
sources:
  - id: source-standard
    resource: https://sharepoint.example.invalid/records/standards/production-change
    title: Authoritative production change standard
    author: team:technology-risk
    last_modified: 2026-08-18T09:00:00Z
generated:
  by: verity-kf-sharepoint-producer/0.2.0
  at: 2026-08-18T09:05:00Z
verified:
  - by: human:standard-owner-id
    at: 2026-08-18T12:00:00Z
status: stable
stale_after: 2027-08-18T00:00:00Z
verity_profile_version: "0.2"
concept_uid: kb:standard:production-change
domain: technology-risk
owner: team:technology-risk
classification: INTERNAL
acl_ref: authz-policy:technology-standards-readers
criticality: high
jurisdictions: [global]
source_record_id: sharepoint:illustrative-site:illustrative-item
source_version: "12.0"
relationships:
  - type: governed-by
    target: /policies/change-management-policy.md
  - type: applies-to
    target: /services/production-technology-services.md
---

# Applicability

This illustrative standard applies to
[production technology services](/services/production-technology-services.md).

# Requirements

Consult the authoritative source for approved requirements.[^source-standard]

# Related knowledge

- [Change Management Policy](/policies/change-management-policy.md)
- [Emergency Change Procedure](/procedures/emergency-change.md)

[^source-standard]: Source mapped to `sources[id=source-standard]`.
```

## 8. Bundle layout

Partition repositories and bundles by access boundary, domain, ownership, and
scale. An illustrative non-production layout is:

```text
global-technology-internal/
├── index.md
├── log.md
├── applications/
│   ├── index.md
│   └── identity-platform.md
├── services/
│   ├── index.md
│   └── enterprise-identity.md
├── standards/
│   ├── index.md
│   └── production-change.md
├── procedures/
│   └── emergency-change.md
├── runbooks/
│   └── identity-service-degradation.md
└── references/
    └── approved-source-summary.md
```

Root `index.md`:

```markdown
---
okf_version: "0.2"
---

# Global Technology Internal Knowledge

- [Applications](applications/) - Governed application concepts.
- [Services](services/) - Technology service concepts.
- [Standards](standards/) - Approved technology standards.
- [Procedures](procedures/) - Approved procedures.
- [Runbooks](runbooks/) - Operational guidance.
```

### 8.1 Release manifest

The release manifest is a VerityKF control artifact, not part of OKF v0.2. An
illustrative shape is:

```yaml
manifest_version: "1.0"
bundle_id: global-technology-internal
release_id: global-technology-internal-2026.08.21.1
okf_version: "0.2"
verity_profile_version: "0.2"
git_commit: 0123456789abcdef0123456789abcdef01234567
created_at: 2026-08-21T10:00:00Z
created_by: process:verity-kf-release
previous_release: global-technology-internal-2026.08.14.1
classification: INTERNAL
artifact:
  uri: artifact://knowledge/global-technology-internal/2026.08.21.1
  digest_algorithm: sha256
  digest: illustrative-bundle-digest
concepts:
  - id: standards/production-change
    digest: illustrative-concept-digest
    acl_ref: authz-policy:technology-standards-readers
```

The production manifest format must define canonical hashing, signature or
attestation, artifact identity, supported consumer/profile ranges, retention,
and rollback semantics.

## 9. Validation tiers

### Tier 1: Base OKF conformance

- Every non-reserved Markdown document has parseable YAML frontmatter.
- `type` is non-empty.
- `index.md` and `log.md` follow reserved-file rules.
- Unknown fields and types are preserved.

### Tier 2: VerityKF Enterprise Profile conformance

- All required enterprise fields are present and valid.
- Concept type, relationship type, classification, criticality, and domain are
  approved values.
- Source entries contain valid resources and required source metadata.
- Actor and timestamp syntax are valid.
- Concept UID and resource identity are unique in the release scope.
- Effective, lifecycle, and supersession dates are coherent.

### Tier 3: Production-release policy

- Required verification and approvals exist.
- Source versions and checksums reconcile.
- Authorization policy reference resolves.
- Secrets and prohibited data scans pass.
- Links satisfy the release-tier policy.
- No unresolved source conflict exists.
- Consumer compatibility and regression tests pass.
- Manifest, digest, retention, and rollback evidence exist.

## 10. Change management for the profile

- Profile changes require an architecture decision and compatibility assessment.
- Additive optional fields use a minor profile version.
- Breaking required-field or semantic changes use a major profile version.
- Consumers declare supported profile ranges.
- Producers validate against the target and previous supported profile during
  migration.
- Production releases retain the exact validator and profile artifact used.
- Changes to the base OKF specification are assessed separately from VerityKF profile
  changes.
