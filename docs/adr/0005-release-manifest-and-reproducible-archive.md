# ADR-0005: Release Manifest and Reproducible Archive

- **Status:** Accepted for framework implementation; control review pending
- **Date:** 21 August 2026
- **Action:** OKF-401
- **Decision owners:** Platform Engineering, Knowledge Architecture, and Platform Security

## Context

A Git commit is useful review history but is not sufficient as the sole unit of
distribution to multiple runtime platforms. Consumers require an immutable
inventory, exact file digests, the validation/profile context, authorization
metadata, prior-release lineage, and a byte-reproducible artifact that can later
be signed and transported through an OCI registry.

Archive tools normally retain filesystem timestamps, owners, modes, traversal
order, and gzip timestamps. Those ambient values make two builds from identical
knowledge differ and weaken provenance evidence.

## Decision

The release builder validates the complete bundle against a pinned profile and
explicit aware clock before reading it into a release. Validation errors prevent
all packaging.

The archive contains the bundle plus a canonical JSON manifest at
`META-INF/verity-kf-release-manifest.json`. Manifest schema `1.0` records:

- bundle and release IDs;
- explicit creation/validation time and source Git commit;
- active OKF and VerityKF Enterprise Profile versions;
- optional prior exact release-archive digest;
- highest concept classification in the bundle; and
- a sorted file inventory with byte size and exact SHA-256.

Concept entries also record canonical concept SHA-256, stable `concept_uid`,
type, classification, `acl_ref`, criticality, lifecycle/freshness, source and
verification counts, and canonical source digest when present. The manifest
declares its consumer-contract version for compatibility admission.

Exact file/archive digests are authoritative integrity values. Canonical hashes
are semantic comparison evidence and never replace exact digests for signature
or retrieval verification.

The deterministic `tar.gz` profile fixes:

- lexicographic POSIX member order;
- regular-file entries only;
- modification time, user ID, and group ID to zero;
- empty owner/group names;
- file mode `0644`;
- gzip modification time to zero; and
- compression level nine on the repository-pinned Python runtime.

Symlinks, path traversal, duplicate paths, non-file archive members, uncontrolled
concept classifications, missing ACL/UID fields, non-canonical manifests,
inventory differences, and exact/canonical digest mismatches fail closed.
Verification bounds uncompressed input size before parsing tar content.

## Consequences

- Identical bundle bytes and release inputs produce byte-identical archives.
- Creation time is an input, not wall-clock state hidden inside the builder.
- The source commit and prior digest form explicit release lineage.
- Classification and authorization references are available before indexing.
- Rebuilding on a different runtime version must use the pinned toolchain until
  cross-runtime reproducibility is certified.
- Signing, OCI transport, promotion, retention, and withdrawal are separate
  stages; this decision does not claim they are complete.

## Alternatives considered

- **Distribute Git working trees:** rejected because runtime consumers should
  not depend on Git history, branch mutability, or repository credentials.
- **Use ZIP:** rejected for the reference build because normalized tar metadata
  maps more directly to OCI artifact conventions and Unix tooling.
- **Include the archive digest inside its manifest:** rejected because that
  creates a recursive digest. The registry/catalog records the outer digest.
- **Sign individual concept files:** deferred; signing the immutable release
  digest is simpler while the manifest retains per-file verification evidence.
