# OKF Control and Resilience Incident Playbooks

Status: reference procedures for owner review and exercises. Replace role names,
systems, communications, evidence stores, and approved commands during production
design. Never paste credentials, user lists, content, or restricted source names.

## Common safety rules

1. Authenticate through approved human/workload identity and record incident/change ID.
2. Confirm exact registry digest, archive digest, bundle/release/profile, channel,
   environment, and current admission/signature evidence before mutation.
3. Use two-person/separation-of-duty approval where policy requires it.
4. Prefer channel removal/repointing and access denial over artifact deletion.
5. Preserve registry, manifest, signature, OPA, catalog, PDP, audit, and telemetry evidence.
6. Check all caches, indexes, regions, consumers, and direct-digest paths.
7. Do not restore service by bypassing signature, admission, authorization,
   classification, freshness, or audit controls.

Every exercise/incident records detect, acknowledge, decision, control effective,
consumer verification, recovery, and close timestamps.

## Emergency release withdrawal

Trigger: integrity/signature/admission issue, unsafe/stale knowledge, unauthorized
exposure, source-owner/legal request, or material consumer harm.

1. Incident commander validates digest/scope and invokes withdrawal authority.
2. Mark digest withdrawn in the transactional catalog with actor/time/reason evidence.
3. Remove every channel pointer; deny exact-digest retrieval before cache/index cleanup.
4. Invalidate gateway/body/index/consumer caches and stop new context assembly.
5. Verify authorized and unauthorized synthetic probes in every region/consumer.
6. Preserve artifact/evidence under retention/hold; do not delete unless separately approved.
7. Notify source, IAM/security, consumer, records/privacy, risk, and support owners by severity.
8. Select rollback/corrected-release path; require normal signing/admission for a correction.

Exit: all access paths deny the withdrawn digest within SLO, evidence is retained,
affected consumers are identified, and recovery/follow-up has named ownership.

## Rollback protected channel

1. Identify the previously admitted, signed, non-withdrawn digest and compatibility.
2. Verify its archive/signature/admission, freshness, ACL mapping, and retention state.
3. Atomically repoint the protected channel to the prior digest; never rebuild it.
4. Rebuild or select derived indexes for that exact digest and invalidate caches.
5. Run entitlement, citation, lifecycle, health, and critical synthetic probes.
6. Record old/new channel digest, approvals, timings, consumers, and outcome.

Exit: channel and all consumers report the same prior digest and rollback tests pass.

## PDP or identity failure

1. Detect timeout/error/issuer/key/revocation/distribution failure and declare scope.
2. Confirm gateway fails closed; no cached allow may exceed approved TTL/revocation policy.
3. Do not switch to local ACL files, caller headers, anonymous access, or stale identity claims.
4. If approved, serve a pre-defined non-sensitive public-only path isolated from protected data.
5. Engage IAM/PDP owner, monitor denied/error aggregates, and protect telemetry from identity data.
6. After recovery, verify issuer/audience/key/policy version and positive/negative fixtures.

Exit: fresh policy/identity decisions succeed, negative tests deny, cache state is safe,
and no unauthorized retrieval occurred.

## Source entitlement, deletion, or classification drift

1. Source owner identifies affected stable record IDs/versions through protected evidence.
2. Pause the affected producer collection without stopping unrelated sources.
3. If exposure or unsafe content is possible, withdraw affected release(s) immediately.
4. Re-evaluate source ACL/classification/delete/hold evidence and mapping version.
5. Produce deterministic correction/tombstone, validate, review, sign, admit, and promote.
6. Prove no old digest/channel/cache/index remains served; preserve required record evidence.

Exit: source and OKF state reconcile by stable identity/version, ACL negative tests pass,
and records/privacy owners approve disposition.

## Derived index rebuild

1. Resolve one admitted, signed, non-withdrawn immutable digest.
2. Create a clean index namespace keyed by digest/profile/index configuration/model version.
3. Verify release archive before ingest; preserve ACL/classification/lifecycle/citations per record.
4. Run document counts, digest inventory, entitlement-negative, relevance, freshness, and latency tests.
5. Atomically switch the consumer index pointer only after evidence passes.
6. Retain/expire the prior derived index under approved rollback and data-retention rules.

Exit: every indexed record maps to the exact release manifest, unauthorized candidates
cannot produce content/score/snippet, and rebuild metrics/SLO are recorded.

## Registry or signature verification failure

1. Stop promotion and new ingestion; continue serving only already verified/admitted
   local releases if policy and recovery design permit it.
2. Distinguish network/availability, trust-root/key, referrer, digest, artifact-type,
   archive-integrity, and authorization failures without bypassing verification.
3. Preserve failed descriptor/verification evidence through the approved secure store.
4. Engage registry/platform-security owner; rotate/restore only under key/trust procedures.
5. Re-pull by immutable digest into a clean workspace and rerun Cosign, archive, and OPA checks.

Exit: verification succeeds against approved trust, no mutable tag was used for a control
decision, and backlog/consumer consistency is reconciled.
