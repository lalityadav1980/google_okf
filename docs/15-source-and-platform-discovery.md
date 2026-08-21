# Source and Internal Platform Discovery Kit

## 1. Purpose

This kit turns the blocked Confluence, SharePoint, YODA, and RACK actions into
bounded evidence requests. It does not infer product capabilities, request real
credentials, or authorize production access.

Every source discovery produces four review artifacts:

1. an approved `source-discovery-v1` profile for the selected collection;
2. API, identity, ACL, records, residency, and rate-limit evidence referenced
   from that profile;
3. a connector certification report with no content or raw record IDs; and
4. owner sign-off for the source mapping and residual gaps.

The JSON Schema is
[`source-discovery-v1.schema.json`](../schemas/source-discovery-v1.schema.json),
and a deliberately unapproved synthetic example is
[`source-discovery.example.yaml`](../profiles/source-discovery.example.yaml).
The model refuses `approved` status while a required capability is unknown/a
gap or a blocking decision remains open. Credentials are prohibited.

## 2. Common discovery sequence

| Gate | Required evidence | Exit condition |
|---|---|---|
| Scope | Named collection, purpose, content owner, classification ceiling, item estimate, residency | One bounded pilot collection is approved |
| Product/API | Product/deployment/version, supported API, stable identity/version, pagination/change/delete semantics | Reproducible sandbox calls exist |
| Identity | Workload identity, least privilege, token/secret handling, network/TLS route | IAM and source owner approve the identity |
| Entitlements | Container/item inheritance, users/groups/links, ACL-change detection, deprovisioning | No source access can be widened by mapping |
| Content | Body formats, tables/macros, attachments, comments, links, size limits, unsupported cases | Deterministic mapping and exclusions are approved |
| Governance | Classification, retention, record/legal hold, deletion, privacy/residency, audit | Records/privacy/security owners approve |
| Operations | Rate limit, `Retry-After`, page size, timeout, availability, backfill, incremental schedule | Load/retry/recovery plan is approved |
| Certification | Version, replay, change, delete, entitlement, canonicalization, and no-content report | Generic connector contract reports conformant |

Evidence references point to approved internal tickets, decision records,
redacted API captures, or product documentation. They do not embed tokens,
cookies, confidential URLs, user membership lists, document bodies, or record
names.

## 3. Confluence evidence checklist

Use [`confluence-checklist.md`](discovery/confluence-checklist.md). The product
owner first declares Cloud, Data Center, or another deployment and exact
version; connector design must not mix their API assumptions.

For Confluence Cloud, current official REST v2 documentation demonstrates
version resources and attachment APIs with explicit view permissions, while
current rate-limit guidance describes points/quota limits and `Retry-After`.
These are discovery inputs, not proof of the adopting organisation's tenant configuration:

- [Atlassian Confluence REST API v2 version resources](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-version/)
- [Atlassian Confluence REST API v2 attachments](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-attachment/)
- [Atlassian Confluence Cloud rate limiting](https://developer.atlassian.com/cloud/confluence/rate-limiting/)

The sandbox must prove page/space identity, version ordering, delete/archive
signals, restricted-page inheritance, direct restrictions, group resolution,
ACL-only change behavior, unsupported macro handling, attachment versions, and
cursor/retry semantics for the selected deployment.

## 4. SharePoint evidence checklist

Use [`sharepoint-checklist.md`](discovery/sharepoint-checklist.md). The product
owner declares SharePoint Online versus Server and exact supported API. The
pilot must choose one site/library and prove the relationship among site, list,
drive, item, version, record, and permission identities.

For SharePoint Online, Microsoft Graph v1.0 documents drive-item delta paging
with `nextLink`/`deltaLink` and a deleted facet, and Microsoft publishes general
Graph throttling guidance. The list-item delta documentation warns that a feed
contains the latest state rather than every intermediate change. These facts
must be tested against the selected library and do not replace tenant evidence:

- [Microsoft Graph driveItem delta](https://learn.microsoft.com/en-us/graph/api/driveitem-delta?view=graph-rest-1.0)
- [Microsoft Graph listItem delta](https://learn.microsoft.com/en-us/graph/api/listitem-delta?view=graph-rest-1.0)
- [Microsoft Graph throttling guidance](https://learn.microsoft.com/en-us/graph/throttling)

The sandbox must prove least-privilege application access, stable IDs across
rename/move, version and deletion behavior, folder/item ACL inheritance,
sharing links, group expansion responsibility, permission-only changes,
retention labels, record declaration/hold behavior, attachments/renditions, and
delta-token expiration/recovery.

## 5. YODA and RACK capability discovery

Complete the separate, assumption-free maps:

- [`YODA-capability-map.md`](discovery/YODA-capability-map.md)
- [`RACK-capability-map.md`](discovery/RACK-capability-map.md)

Each capability must be marked `owned`, `integrated`, `planned`, `absent`, or
`unknown` and supported by an owner/evidence reference. The maps cover authoring,
source/catalog aggregation, immutable release ingestion, search/indexing,
identity/PDP enforcement, citations, agent runtime, user experience, audit,
feedback, hosting/SLO, and roadmap.

Architecture governance then assigns exactly one target owner for each mutable
capability. Possible outcomes are producer, consumer, both with explicit
boundaries, or no pilot role. The framework does not require YODA or RACK to be
replaced and does not label either platform authoritative without evidence.

## 6. Connector certification contract

`certify_connector` exercises any `KnowledgeSource` adapter against the same
contract. It checks:

- replayable page/cursor behavior and bounded page size;
- terminal cursor, cursor advance, and loop behavior;
- unique, ordered, source-consistent change events;
- version-exact and repeatable record fetches;
- delete events without fetching removed content;
- controlled classification and non-empty entitlement references;
- HTTPS/URN source identity and non-empty body;
- deterministic source-record canonicalization; and
- content-minimized reports containing only hashed record fingerprints.

The generic suite is necessary but not sufficient. A Confluence or SharePoint
producer remains blocked until it passes this suite with an approved sandbox,
source-specific ACL/deletion/attachment tests, load/retry testing, and source/IAM/
records owner review.
