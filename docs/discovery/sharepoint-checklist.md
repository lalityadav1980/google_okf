# SharePoint Pilot Discovery Checklist

Status: input required from the SharePoint source owner. Do not place
credentials, tokens, content, user lists, restricted site/library names, sharing
URLs, or unredacted tenant identifiers in this file.

## Ownership and scope

| Evidence | Required value/reference |
|---|---|
| Product owner | Role and approved contact route |
| Pilot content owner | Role and approval reference |
| IAM, records/privacy, engineering owners | Roles and approval references |
| Deployment and exact product/API version | Online/Server/other and Graph/API version |
| Pilot collection | One approved site/library or list, referenced indirectly |
| Purpose and exclusions | Intended concepts; excluded folders/types/labels |
| Volume and size | Items, versions, folders, largest file, daily changes |
| Classification/residency ceiling | Approved values and regional boundary |

## API and change behavior to prove in sandbox

- Stable site/list/drive/item identities and canonical resource URI.
- Rename, folder move, cross-library move, copy, restore, and recycle behavior.
- Exact version identity and relationship among list item, drive item, file, and
  metadata fields.
- Initial enumeration, `nextLink`/`deltaLink` or approved equivalent, replay,
  token expiry, resynchronization, and latest-state-versus-event semantics.
- Delete/recycle/purge facets and safe folder deletion ordering.
- Whether metadata-only, permission-only, retention, record, and sharing changes
  appear in the selected change mechanism.
- Deterministic extraction for supported Office/PDF/text formats, pages, lists,
  columns, renditions, attachments, links, and unsupported/protected files.
- Throttling headers, `Retry-After`, concurrency, timeout, payload, and page limits.

## Identity and entitlements to prove

- Approved workload identity, tenant/app boundary, least-privilege application
  access, and selected-site/library scoping.
- Network/TLS/CA route and secret-free runtime credential method.
- Site/library/folder/item inheritance and unique permission behavior.
- Direct users/groups, nested/dynamic groups, guests, sharing links, and external
  sharing policy.
- Stable entitlement/ACL identity emitted as `entitlement_refs` without copying
  mutable user membership into the release.
- ACL-only change signal and maximum revocation lag.
- Fail-closed behavior for incomplete permissions, protected/encrypted files,
  missing renditions, and unsupported sensitivity/records metadata.

## Records, privacy, and operations

- Sensitivity/classification mapping owner and precedence.
- Retention label, record declaration, disposition, legal hold, and deletion
  authority; OKF must not become the legal record by accident.
- Personal data handling for authors, sharing principals, version history, and audit.
- Residency, backup, staging, logging, and support-access boundaries.
- Backfill/incremental schedule, checkpoint store, retry budget, source SLO, and
  token-expiry/partial-failure recovery.

## Exit evidence

- Approved `source-discovery-v1` instance with every capability evidenced.
- Redacted identity/API/delta/ACL/delete/record/rate-limit evidence pack.
- Generic connector certification report plus SharePoint-specific contract tests.
- Source, IAM, records/privacy, security, and engineering sign-off.
