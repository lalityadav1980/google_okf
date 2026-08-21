# Release Admission Policy

## 1. Purpose

Release admission is a deny-by-default policy decision over already verified,
signed release evidence. It is not a replacement for bundle validation,
signature verification, registry authorization, or retrieval authorization.

The Rego package is
`data.verity.kf.release_admission`. Its stable outputs are:

- `allow`: true only when no denial exists; and
- `deny`: a set of `{code, message}` objects suitable for evidence and operator
  remediation.

Policy callers rely on denial codes, not message wording.

## 2. Input boundary

The input contains three objects:

| Object | Evidence |
|---|---|
| `manifest` | Parsed, exact-digest-verified release manifest |
| `artifact` | OCI type/digest, archive verification, and Cosign verification result |
| `policy` | Environment-owned allowlists and enforcement switches |

The caller verifies the archive and signature before invoking OPA and records
the command/tool versions and raw evidence separately. Boolean fields such as
`signature_verified` are evidence assertions from a trusted pipeline identity,
not values accepted from an end user.

Environment policy contains:

- approved profile ID/version pairs;
- allowed classifications and lifecycle states;
- approved signature identity/issuer pairs;
- supported consumer-contract versions;
- explicit evaluation time;
- whether a prior release is mandatory; and
- whether canonical source hashes are mandatory.

The evaluation time is supplied explicitly so replay and audit produce the same
freshness decision.

## 3. Denial catalog

| Code | Condition |
|---|---|
| `SIGNATURE_NOT_VERIFIED` | Cosign verification did not succeed |
| `ARCHIVE_NOT_VERIFIED` | Embedded inventory/digest verification did not succeed |
| `REGISTRY_DIGEST_INVALID` | OCI evidence is not an immutable SHA-256 digest |
| `ARTIFACT_TYPE_INVALID` | OCI artifact type is not the OKF release media type |
| `SIGNER_NOT_ALLOWED` | Verified identity/issuer is not approved |
| `PROFILE_NOT_ALLOWED` | Manifest profile ID/version is not approved |
| `BUNDLE_CLASSIFICATION_NOT_ALLOWED` | Bundle exceeds environment classification |
| `CONSUMER_CONTRACT_UNSUPPORTED` | Target consumer cannot read this contract |
| `PRIOR_RELEASE_REQUIRED` | Promoted release lacks predecessor lineage |
| `CONCEPT_ACL_MISSING` | Concept has no authorization policy reference |
| `CONCEPT_CLASSIFICATION_NOT_ALLOWED` | Concept classification is not admitted |
| `CONCEPT_STATUS_NOT_ALLOWED` | Lifecycle state is not admitted |
| `CONCEPT_SOURCE_MISSING` | Source provenance is absent |
| `CONCEPT_SOURCE_HASH_MISSING` | Required canonical source digest is absent |
| `CONCEPT_VERIFICATION_REQUIRED` | High-criticality concept has no verification |
| `CONCEPT_FRESHNESS_MISSING` | Freshness boundary is absent |
| `CONCEPT_STALE` | Freshness boundary has passed at evaluation time |

## 4. Lifecycle use

Candidate environments may admit `draft` or allow legacy concepts without a
source hash only through a versioned environment policy. Protected channels
should allow only `stable`, require source hashes, require predecessor lineage
after the first release, and restrict signer/profile/classification values.

The full decision input, deny/allow output, OPA version, policy commit, release
digest, signature identity, and decision time are immutable release evidence.

## 5. Tests and CI

The policy uses Rego v1 and is tested with OPA 1.17.0:

```bash
opa fmt --fail --list policies
opa check --strict policies
opa test policies --fail-on-empty --verbose
```

Tests include one complete allow case and negative cases for every denial family,
including unsigned, mutable-reference, unapproved signer/profile/classification,
missing ACL/source/hash/freshness, high-criticality verification, stale content,
draft lifecycle, and consumer incompatibility.

OPA CI installation is pinned to the official setup action commit and an exact
OPA release. See the [OPA policy-testing documentation](https://www.openpolicyagent.org/docs/policy-testing).

