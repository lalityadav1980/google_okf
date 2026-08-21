# ADR-0006: Authorize Before Every Content Retrieval

- **Status:** Proposed
- **Date:** 2026-08-21
- **Owners:** Identity and Access Management, Information Security, Platform Engineering
- **Related actions:** OKF-403, OKF-502, OKF-601

## Context

OKF releases preserve source classifications and ACL references, but the format
does not authenticate a caller or evaluate current bank entitlements. Searching
an unauthorized body, returning a snippet, exposing a link, computing an
embedding, or expanding a relationship can leak content even when the final
body endpoint later denies access. Release channels and derived indexes also
create mutable routing state around immutable knowledge artifacts.

## Decision

1. Serve only archives that pass signature, integrity, artifact-type, and OPA
   release-admission evidence and are identified by immutable OCI digest.
2. Keep OCI manifest digest and exact archive-layer digest as separate values.
3. Resolve a human or workload through an explicit enterprise identity adapter;
   never treat unverified request headers as principal attributes.
4. Invoke the enterprise PDP for every concept and action before reading bodies
   or derived content. Apply this to discovery, search, snippets, direct reads,
   links, embeddings, and graph expansion.
5. Deny missing ACLs, unknown principals/actions, PDP failures, and
   classification-clearance violations by default.
6. Return the same public not-found response for an absent and unauthorized
   concept. Retain the internal decision ID and reasons in protected telemetry.
7. Promote and roll back by atomically changing a protected channel-to-digest
   pointer. Never rebuild a release during promotion.
8. Withdrawal removes channel pointers and denies exact-digest retrieval while
   retaining release, admission, and withdrawal evidence.
9. Publish the consumer boundary as versioned OpenAPI so YODA, RACK, and other
   consumers are not coupled to the Python implementation.

## Consequences

- Authorization metadata must be present in the signed release manifest.
- Search/index adapters must preserve ACL and classification metadata and prove
  filter-before-content behavior with negative entitlement tests.
- PDP latency and availability enter the serving SLO; caching is allowed only
  under approved TTL/revocation rules and must fail closed.
- Returning authorized link targets requires additional PDP decisions.
- The local reference PDP and in-memory catalog demonstrate the contract but do
  not satisfy production identity, policy, persistence, retention, or recovery.
- YODA/RACK integration can replace either adapter without changing the OKF
  bundle or public retrieval schema.

## Rejected alternatives

- **Authorize after search:** snippets, scores, and existence signals may leak.
- **Trust classification alone:** classification is not a current entitlement.
- **Embed source ACL membership in a release:** user membership changes faster
  than immutable releases and would create stale authorization copies.
- **Use mutable tags as release identity:** signatures, traces, and rollback
  could no longer prove exactly which artifact was served.
- **Return all graph/link targets then filter bodies:** relationship existence
  can itself be sensitive.
