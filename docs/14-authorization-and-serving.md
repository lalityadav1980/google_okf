# Authorization-Before-Retrieval and Serving Contract

## 1. Status and scope

The portable authorization port, deny-by-default reference evaluator, immutable
release catalog, lifecycle controls, lexical reference retrieval, and OpenAPI
consumer contract are implemented and tested locally.

The local ACL evaluator exists only to prove ordering and negative behavior. A
production deployment must replace it with the adopting organisation's approved policy decision
point (PDP) and must construct the API with a resolver that validates an
enterprise-issued human or workload identity. Raw caller headers are not an
identity source.

## 2. Security invariant

For every concept candidate, the serving layer performs this sequence:

```text
resolve admitted release digest/channel
  -> reject withdrawn release
  -> inspect non-content release metadata
  -> apply lifecycle/freshness eligibility
  -> request PDP decision for principal + action + concept
  -> only when allowed, read concept bytes
  -> produce body/snippet/citations
  -> authorize every internal link target independently
```

The invariant applies to discovery, search, snippets, direct body retrieval,
and link expansion. Future embeddings and graph expansion must use the same
port and ordering. They are not exempt because they are derived data.

Denied and nonexistent concepts return the same public `404` response. This
prevents direct concept probing from becoming an entitlement oracle. A
withdrawn release addressed by exact digest returns `410`; its content remains
unavailable while its manifest, admission, and withdrawal evidence is retained.

## 3. Authorization contract

`authorization.py` defines provider-neutral models:

- `PrincipalContext`: stable subject, human/workload type, exact groups, and
  classification clearance;
- `ResourceContext`: bundle, immutable release digest, concept UID/path,
  classification, ACL reference, and requested action;
- `AuthorizationDecision`: allow/deny, stable decision ID, policy version, and
  machine-readable reason codes; and
- `PolicyDecisionPoint`: the adapter protocol implemented by the adopting organisation's PDP.

Supported actions are `discover`, `search`, `read`, and `follow_link`. Exact
subject/group matching, action allowlists, principal-type constraints, and the
classification ceiling are tested independently. Missing ACLs and unknown
principals deny by default.

`ReferencePolicyDecisionPoint` is deterministic and suitable for unit tests and
synthetic demonstrations. It must not become an embedded production
authorization database. Production policy ownership, identity-to-attribute
mapping, decision caching, revocation, availability, and fail-closed behavior
belong to the adopting organisation's IAM and security architecture.

## 4. Release catalog and lifecycle

The catalog accepts an archive only when all of the following are supplied:

- immutable OCI-style `sha256:<digest>` registry identity;
- successful signature verification evidence;
- successful archive/inventory verification evidence;
- an allowed release-admission policy decision and version; and
- the expected OKF artifact media type.

The catalog verifies the archive itself before indexing. OCI manifest digest
and archive-layer digest remain separate evidence values.

An admitted release begins as `candidate`. Promotion changes a protected
channel pointer to that same digest and marks it active; it does not rebuild or
copy concept bytes. Rollback repoints the channel to a previously admitted,
non-withdrawn digest. Withdrawal removes all channel pointers immediately,
denies exact-digest retrieval, and retains immutable actor/time/reason evidence.

The in-memory catalog is a behavioral reference. The production catalog should
use the approved transactional store and registry, with retention, legal hold,
multi-region recovery, channel ownership, and an agreed withdrawal SLO.

## 5. Consumer OpenAPI

The committed contract is
[`serving-api-v1.openapi.json`](../schemas/serving-api-v1.openapi.json). It is
generated from Pydantic/FastAPI models and compared byte-for-structure in tests
to prevent unreviewed drift.

| Endpoint | Behavior |
|---|---|
| `GET /healthz` | Liveness only; exposes no catalog or content data |
| `GET /v1/releases` | Lists only releases containing at least one discoverable concept |
| `POST /v1/search` | Release/channel-pinned lexical reference search with authorized snippets and citations |
| `GET /v1/releases/{release}/concepts/{uid}` | Authorized concept body, hashes, lifecycle, citations, links, release/profile, and PDP evidence |

Retrieval responses use `Cache-Control: no-store`. The OpenAPI contract declares
enterprise OpenID Connect bearer authentication. Application construction
requires both an HTTPS discovery URL and an explicit principal resolver; the
framework does not ship a permissive default identity implementation.
Freshness is evaluated with the server-owned aware clock; callers cannot supply
an earlier time or opt into stale/draft/deprecated content through the public
API. Any future exception requires a separate policy-controlled endpoint.

The reference search deliberately remains simple and deterministic. OpenSearch
or an existing YODA/RACK retrieval capability is adopted only after the pilot
benchmark demonstrates a gap and proves authorization filtering, citation
preservation, rebuild behavior, latency, operations, and cost.

## 6. Evidence and tests

Automated tests prove:

- exact subject/group, principal-type, action, and classification decisions;
- unknown ACL and unauthorized principal denial;
- zero body-store reads for unauthorized search and direct retrieval;
- citations and release/profile/digest/hash evidence on allowed results;
- independent authorization of internal link targets;
- freshness and deprecated-status filtering before body access;
- admission rejection when signature/archive/policy evidence is incomplete;
- same-digest promotion, rollback, withdrawal, and retained evidence;
- indistinguishable `404` responses for denied and missing concepts;
- immediate `410` behavior for an exact withdrawn digest; and
- generated OpenAPI equality and OpenID Connect declaration.

The core contract uses FastAPI `>=0.141,<0.142`. API tests use HTTPX2
`>=2,<3`, matching the current Starlette test-client direction. Exact resolved
versions and transitive dependencies are retained in `uv.lock`.

## 7. Production inputs still required

1. Enterprise OpenID Connect discovery URL, token audiences, issuer, assurance,
   human/workload claim mapping, and resolver library.
2. PDP endpoint/library, request/decision schema, reason taxonomy, policy
   distribution, cache/revocation rules, timeout, and fail-closed SLO.
3. Authoritative meaning and ownership of each `acl_ref` emitted by Confluence,
   SharePoint, YODA, RACK, and other producers.
4. OCI registry digest/signature/admission evidence integration.
5. Catalog persistence, channel owners, retention, withdrawal authority,
   rollback/withdrawal SLO, legal hold, and recovery design.
6. Selected YODA or RACK pilot interface and benchmark workload.

No production identity, authorization, or content-serving claim is made until
these inputs are approved and integration/assurance evidence passes.
