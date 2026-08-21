---
type: Runbook
title: Identity Service Degradation
description: Illustrative diagnostic guidance for reduced enterprise identity service availability.
resource: https://confluence.example.invalid/runbooks/identity-service-degradation
tags: [identity, operations, runbook]
sources:
  - id: confluence-runbook
    resource: https://confluence.example.invalid/runbooks/identity-service-degradation
    title: Identity Service Degradation Runbook
    author: team:identity-platform
    last_modified: 2026-08-19T08:00:00Z
generated:
  by: xyz-okf-confluence-producer/0.1.0
  at: 2026-08-19T08:05:00Z
verified:
  - by: human:service-owner-id
    at: 2026-08-19T09:00:00Z
status: stable
stale_after: 2030-09-19T00:00:00Z
xyz_profile_version: "0.1"
concept_uid: kb:runbook:identity-service-degradation
domain: enterprise-platforms
owner: team:identity-platform
classification: INTERNAL
acl_ref: authz-policy:technology-runbook-readers
criticality: high
source_record_id: confluence:pilot:identity-service-degradation
source_version: "28"
relationships:
  - type: applies-to
    target: /services/enterprise-identity.md
---

# Scope

This illustrative runbook applies to the
[Enterprise Identity Service](/services/enterprise-identity.md).

# Diagnostic sequence

1. Confirm the authenticated monitoring signal and affected region.
2. Confirm the authorized incident coordinator and service owner.
3. Follow the authoritative runbook linked in `resource`.

# Safety

This knowledge is advisory. It does not authorize an agent to change a system.

