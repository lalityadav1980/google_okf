# ADR-0004: Producer Transaction and Replay Boundary

- **Status:** Accepted for framework implementation; control review pending
- **Date:** 21 August 2026
- **Action:** OKF-203
- **Decision owners:** Platform Engineering and Source Integration Engineering

## Context

Enterprise source APIs expose paged change feeds, mutable records, deletions,
throttling, and transient failures. Publication to a review branch or release
workspace is a separate system from the source cursor. A failure between those
systems can lose a change or publish it more than once unless the boundary is
explicit.

Dry-run operation must demonstrate the proposed effect without advancing state.
Deleting source content must not require fetching content that no longer exists,
and an absent source must never be interpreted as authorization to delete an
unrelated concept.

## Decision

The producer SDK uses **at-least-once replay with idempotent publication**, not a
claim of distributed exactly-once processing.

For one source page the engine performs:

1. load the `(source_system, collection)` checkpoint;
2. request changes after its cursor with bounded retry;
3. fetch each upsert at the event's exact version;
4. create deterministic upsert, delete, or no-op operations;
5. publish all actionable operations atomically and idempotently;
6. verify the receipt acknowledges exactly the submitted operation IDs; and
7. compare-and-set the next checkpoint generation.

Any discovery, fetch, planning, or publication failure leaves the checkpoint
unchanged. A compare-and-set conflict after publication is reported; replay is
safe because each operation ID is a SHA-256 digest over its source identity,
version, kind, output path, and exact content digest.

### Change and deletion contract

`SourceChange` contains source system, immutable record ID, source version,
change kind, and aware timestamp. An upsert is fetched and must match the event
identity and version. A delete is planned from the retained identity/path index
without fetching removed content. If no published identity exists, the planner
returns an auditable no-op. The core does not invent a non-standard OKF
tombstone document; release-manifest deletion evidence is handled by `OKF-401`.

### Retry contract

Only `RetryableOperationError` is retried. Adapters must translate throttling,
bounded transport failures, and explicitly retryable server responses into that
type. Authentication, authorization, schema, mapping, and validation failures
remain permanent. Attempts and delays are bounded, and a source-provided retry
delay is honored up to the configured maximum.

### Checkpoint stores

All stores implement atomic compare-and-set. The framework provides an
in-memory reference store and a durable SQLite store for local/single-runner
operation. A production multi-runner deployment must implement the same port on
an approved transactional service; it must not place SQLite on shared network
storage.

### Dry run

Dry run performs source reads and deterministic planning, returns the complete
operation report, and performs no publication or checkpoint write. Connectors
and planners used by dry run must themselves be read-only.

## Consequences

- A crash may cause replay, but cannot silently skip an uncommitted source page.
- Publishers must retain operation IDs long enough to de-duplicate replay.
- Source versions and cursors are opaque strings; the core never orders them.
- A page is the publication/checkpoint unit, bounding memory and recovery work.
- Concurrent runners are detected through checkpoint generation conflicts.
- End-to-end exactly-once claims are prohibited unless one transactional system
  owns both source acknowledgement and publication, which is not assumed here.

## Alternatives considered

- **Advance before publication:** rejected because publication failure would
  permanently skip changes.
- **Advance after each record:** rejected because it breaks atomic page review
  and makes partial dependency changes visible.
- **Retry every exception:** rejected because authorization and mapping defects
  would loop and could amplify incidents.
- **Delete on fetch-not-found:** rejected because permissions and transient
  source behavior can also appear as not found.

