# OCI Publication, Signing, and Promotion Contract

## 1. Status

The local command/validation contract is implemented and tested. Remote
publication is deliberately blocked until XYZ Bank supplies an approved OCI
repository, publisher workload identity, and signature trust decision.

This stage never sends credentials on command arguments. ORAS and Cosign use
the approved ambient workload identity, credential helper, or KMS integration.

## 2. Open-source tools and versions

The reference boundary supports:

- ORAS CLI `>=1.3,<2` for OCI 1.1 artifact publication and digest output; and
- Cosign `>=3.1,<4` for digest signing and identity/KMS verification.

Version ranges are recorded in
[`profiles/supply-chain.example.yaml`](../profiles/supply-chain.example.yaml).
Production pipelines pin an exact reviewed binary digest and verify its release
provenance before installation.

Authoritative documentation:

- [ORAS push command](https://oras.land/docs/commands/oras_push/)
- [ORAS formatted JSON output](https://oras.land/docs/how_to_guides/format_output/)
- [Cosign container signing](https://docs.sigstore.dev/cosign/signing/signing_with_containers/)
- [Cosign signature verification](https://docs.sigstore.dev/cosign/verifying/verify/)

## 3. Media types

| Object | Media type |
|---|---|
| OCI artifact | `application/vnd.xyz-bank.okf.release.v1+tar+gzip` |
| Release layer | `application/vnd.xyz-bank.okf.release.layer.v1+tar+gzip` |
| Embedded manifest | `application/vnd.xyz-bank.okf.manifest.v1+json` |

The outer OCI manifest digest is distinct from the exact archive-layer digest.
Both are retained. The layer digest proves the bytes built under `OKF-401`; the
OCI digest is the immutable registry/signature/promotion reference.

## 4. Publication sequence

```text
validated reproducible archive
  -> ORAS push to candidate tag with typed media and annotations
  -> parse JSON descriptor
  -> verify repository, artifact type and sha256 manifest digest
  -> address artifact only as repository@sha256:<digest>
  -> Cosign sign immutable digest
  -> Cosign verify with explicit bank trust policy
  -> ORAS pull by digest into a clean workspace
  -> verify embedded manifest and exact/canonical file digests
  -> record registry/layer/manifest/signature evidence
```

Tags are discovery aliases only. Signing, verification, policy admission,
promotion, rollback, and consumers use a digest reference.

`supply_chain.py` emits argument arrays, not shell strings, and validates
repository, tag, annotation, media-type, digest, and trust-policy inputs. It
rejects schemes, whitespace, path traversal, mutable references for signing,
and verification without an explicit key or certificate identity/issuer.

## 5. Required OCI annotations

- `org.opencontainers.image.created`
- `org.opencontainers.image.revision`
- `org.opencontainers.image.title`
- `xyz.bank.okf.archive.sha256`
- `xyz.bank.okf.bundle.id`
- `xyz.bank.okf.profile`

Annotations contain routing and integrity metadata only. They must not contain
knowledge content, entitlements, user identifiers, credentials, or secrets.

## 6. Signature trust options

### KMS-backed Cosign key — initial technical recommendation

Use an approved non-exportable KMS/HSM signing key when the bank already has a
managed key lifecycle, separation of duties, audit logging, and workload
identity. Verification pins the approved KMS/public-key reference. Rotation
creates a controlled overlap period; it does not rewrite old release evidence.

### Identity-based/keyless Cosign

Use only when the OIDC issuer, certificate identity, Fulcio trust root, Rekor or
private transparency service, availability model, and metadata-disclosure risk
are approved. Verification must specify both certificate identity and issuer;
"any valid Sigstore identity" is not an acceptable bank policy.

Private Sigstore services remain an option but introduce operated platform
components. The framework does not assume that public transparency logging of
internal repository metadata is acceptable.

## 7. Registry controls required

- dedicated repository and environment boundaries;
- TLS with approved private/public CA and no production `plain-http` bypass;
- workload identity with push-only candidate permissions;
- immutable or protected tags;
- consumer pull by digest;
- publisher denied delete in protected environments;
- retention/legal-hold and malware/scanning behavior agreed;
- OCI 1.1 referrer support certified for signatures; and
- audit events exported to the bank monitoring platform.

## 8. Promotion and rollback

Promotion copies the already signed OCI manifest digest between approved
repositories or assigns a protected channel to that digest. It never rebuilds
the archive. Rollback resolves the channel to a previously admitted digest;
withdrawal denies new retrieval while preserving manifest, signature, decision,
and audit evidence.

`OKF-403` remains incomplete until registry retention, channel ownership,
withdrawal authority, rollback SLO, and environment topology are supplied.

## 9. Inputs required to unblock remote evidence

1. Candidate and protected OCI repository names.
2. Registry product/version and confirmed OCI 1.1/referrer behavior.
3. Publisher and verifier workload identities.
4. Approved KMS key URI or certificate identity/OIDC issuer and trust root.
5. Network/TLS/CA and registry credential-helper method.
6. Retention, deletion, promotion, withdrawal, and audit-log owners.

No real publication or signature is attempted before these inputs are approved.

