# Confluence Pilot Discovery Checklist

Status: input required from the Confluence source owner. Do not place
credentials, cookies, content, user lists, restricted space/page names, or
unredacted tenant URLs in this file.

## Ownership and scope

| Evidence | Required value/reference |
|---|---|
| Product owner | Role and approved contact route |
| Pilot content owner | Role and approval reference |
| IAM, records/privacy, engineering owners | Roles and approval references |
| Deployment and exact product version | Cloud/Data Center/other plus version |
| Pilot collection | One approved space or bounded page tree, referenced indirectly |
| Purpose and exclusions | Intended concepts; excluded labels/content/types |
| Volume and size | Pages, versions, attachments, largest page/file, daily changes |
| Classification/residency ceiling | Approved values and regional boundary |

## API and change behavior to prove in sandbox

- Stable space/page/attachment identifiers and canonical resource URI.
- Page title/move behavior without identity churn.
- Exact page and attachment version fields and ordering.
- Initial enumeration, incremental change method, pagination/cursor replay, and
  cursor expiry/backfill behavior.
- Delete, trash, archive, restore, and purge signals.
- Whether permission-only, label-only, comment, and attachment changes appear.
- Body representations available and deterministic conversion for headings,
  tables, code, links, images, macros, includes, and unsupported extensions.
- Attachment download/version limits, malware/scanning boundary, and exclusions.
- Rate/quota headers, `Retry-After`, concurrency, timeout, payload, and page limits.

## Identity and entitlements to prove

- Approved workload identity/authentication method and least-privilege scopes.
- Network/TLS/CA route and secret-free runtime credential method.
- Space permission, page restriction, inheritance/override, user/group, guest,
  anonymous/public-link, and app-access-rule behavior.
- Stable entitlement/ACL identity emitted as `entitlement_refs` without copying
  mutable user membership into the release.
- Group source and nested/dynamic group responsibility.
- ACL-only change signal and maximum revocation lag.
- Behavior when the connector can enumerate an object but cannot read body,
  attachment, author, or restriction data: fail closed and report a gap.

## Records, privacy, and operations

- Authoritative record and retention/legal-hold responsibilities.
- Personal data handling for authors, comments, mentions, history, and audit.
- Residency, backup, staging, logging, and support-access boundaries.
- Backfill/incremental schedule, checkpoint store, retry budget, source SLO, and
  recovery from expired cursors or partial failure.
- Redacted audit evidence retained for source version, mapping version,
  operation ID, result, lag, and errors without content.

## Exit evidence

- Approved `source-discovery-v1` instance with every capability evidenced.
- Redacted API/ACL/change/delete/attachment/rate-limit evidence pack.
- Generic connector certification report plus Confluence-specific contract tests.
- Source, IAM, records/privacy, security, and engineering sign-off.
