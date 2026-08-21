---
type: Runbook
title: Identity Service Degradation
description: Synthetic diagnostic guidance for reduced enterprise identity service availability.
resource: https://confluence.example.invalid/runbooks/identity-service-degradation
tags:
- identity
- operations
- runbook
sources:
- id: confluence
  resource: https://confluence.example.invalid/runbooks/identity-service-degradation
  title: Identity Service Degradation
  author: team:identity-platform
  last_modified: '2026-08-20T02:35:00Z'
generated:
  by: xyz-okf-confluence-producer/0.1.0
  at: '2026-08-20T02:35:00Z'
verified:
- by: human:service-owner-id
  at: '2026-08-20T09:00:00Z'
status: stable
stale_after: '2027-08-20T02:35:00Z'
xyz_profile_version: '0.1'
concept_uid: kb:runbook:identity-service-degradation-rendered
domain: enterprise-platforms
owner: team:identity-platform
classification: INTERNAL
acl_ref: authz-policy:technology-runbook-readers
criticality: high
source_system: confluence
source_record_id: confluence:pilot:identity-service-degradation
source_version: '29'
producer_mapping:
  id: confluence-runbook-v1
  version: 1.0.0
relationships:
- type: applies-to
  target: /services/enterprise-identity.md
- type: operated-by
  target: /runbooks/identity-service-degradation.md
jurisdictions:
- global
---

# Scope

This synthetic runbook applies to the enterprise identity service.

# Diagnostic sequence

1. Confirm the authenticated monitoring signal and affected region.
2. Confirm the authorized incident coordinator and service owner.
3. Follow the authoritative source linked in `resource`.

# Safety

This knowledge is advisory. It does not authorize an agent to change a system.
