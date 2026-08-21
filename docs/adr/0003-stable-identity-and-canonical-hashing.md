# ADR-0003: Stable Identity and Canonical Hashing

- **Status:** Accepted for framework implementation; control review pending
- **Date:** 21 August 2026
- **Action:** OKF-202
- **Decision owners:** Knowledge Architecture and Platform Engineering

## Context

OKF v0.2 defines a Concept ID as the concept file path with the `.md` suffix
removed. That identity is portable and directly resolvable, but it changes when
a concept moves. The upstream specification does not define a permanent
location-independent identity, an initial path-allocation grammar, or canonical
content hashing.

XYZ Bank requires stable lineage across title changes, reorganizations, source
revisions, releases, indexes, citations, and audit evidence. It also requires a
way to distinguish an exact released byte sequence from semantically equivalent
frontmatter serialized with different YAML formatting.

## Decision

### Three identifiers have distinct meanings

1. **OKF Concept ID:** bundle-relative path without `.md`, as defined by OKF.
2. **`concept_uid`:** immutable XYZ Bank extension identifying the conceptual
   record independently of its current path.
3. **Content digest:** SHA-256 over either exact bytes or a named canonical form;
   it identifies a version, not the conceptual record.

Consumers must not substitute one identifier for another.

### Stable UID allocation

New UIDs use UUIDv5 with the versioned namespace in
`profiles/xyz-bank-identity.yaml`. The UUID name is canonical JSON containing:

- lowercase controlled `source_system`;
- the source system's immutable `record_id`; and
- a stable `fragment` when one source record produces multiple concepts.

Mutable source version, URI, title, owner, classification, and output path are
excluded. The published form is
`urn:xyz-bank:okf:concept:<uuid>`. Source fragments must be durable semantic keys,
not section ordinals or generated array positions.

The namespace UUID and UID prefix must not change after IDs are issued. A future
identity scheme requires a new policy version and explicit migration mapping.

### Path allocation and rename rules

An initial path contains a controlled type directory, an ASCII-safe title slug,
and the first 12 hexadecimal UUID characters. The suffix avoids collisions and
prevents title-only paths from becoming implicit identity.

After allocation, a title or type change retains the approved path by default.
An intentional move requires review, keeps `concept_uid` unchanged, updates
inbound links, and is recorded in the release identity index. A split allocates
new fragment-based UIDs; a merge allocates or selects one surviving UID and
records explicit `supersedes` relationships. Deleted UIDs are never reused.

### Canonical hashes

All digests use lowercase SHA-256 hexadecimal values and a named, versioned
canonicalization profile.

- **Exact file digest:** SHA-256 of the released UTF-8 bytes. This is the
  authoritative integrity value for manifests, signatures, and retrieval.
- **`xyz-okf-concept-c14n-v1`:** parses YAML frontmatter, normalizes Unicode to
  NFC, sorts mapping keys, preserves sequence order, tags scalar types, rejects
  non-string mapping keys and non-finite numbers, normalizes timestamps to UTC,
  and normalizes body line endings/final newlines. It detects semantic concept
  changes while ignoring YAML key order and quoting style.
- **`xyz-okf-source-c14n-v1`:** applies the same typed canonical encoding to all
  `SourceRecord` contract fields, source metadata, and body; entitlement
  references are sorted and de-duplicated. Its digest is retained as
  `source_hash` in rendered frontmatter.

Each canonical byte stream starts with its profile name and newline as a domain
separator. Canonicalization profile behavior is immutable. Any rule change
creates `v2`; existing digests remain verifiable with `v1`.

The canonical concept digest supplements but never replaces the exact file
digest in an immutable release.

## Consequences

- Paths remain human-readable and OKF-compatible.
- Stable citations and audit correlation survive reviewed file moves.
- Source replay and no-op detection do not rely solely on source version labels.
- Exact release verification remains byte-for-byte and unambiguous.
- The bank owns an extension profile and must govern namespace/policy versions.
- YAML values outside the canonical profile fail explicitly instead of receiving
  implementation-dependent hashes.

## Alternatives considered

- **Use path as the only identity:** rejected because an organizational move
  changes identity and complicates citations and audit history.
- **Use a content hash as the UID:** rejected because any edit would create a new
  conceptual identity.
- **Use title/resource URI as the UUID name:** rejected because both can change
  and may expose sensitive source structure.
- **Hash normalized YAML text:** rejected because emitter versions and style
  choices can change bytes without changing meaning.
- **Adopt JSON Canonicalization Scheme directly:** deferred because OKF input is
  YAML and its scalar type system requires an explicit lossless mapping first.

## References

- [Open Knowledge Format v0.2 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
- [RFC 4122 UUID namespaces](https://www.rfc-editor.org/rfc/rfc4122)
- [FIPS 180-4 Secure Hash Standard](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)

