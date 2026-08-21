---
type: Technology Service
title: Enterprise Identity Service
description: Illustrative service providing workforce authentication and identity context.
resource: https://catalog.example.invalid/services/enterprise-identity
tags: [identity, security, platform]
sources:
  - id: service-catalog
    resource: https://catalog.example.invalid/services/enterprise-identity
    title: Enterprise Service Catalog
    author: team:service-management
    last_modified: 2026-08-17T10:00:00Z
generated:
  by: verity-kf-catalog-producer/0.2.0
  at: 2026-08-17T10:05:00Z
verified:
  - by: process:catalog-owner-reconciliation
    at: 2026-08-17T11:00:00Z
status: stable
stale_after: 2030-09-17T00:00:00Z
verity_profile_version: "0.2"
concept_uid: kb:service:enterprise-identity
domain: enterprise-platforms
owner: team:identity-platform
classification: INTERNAL
acl_ref: authz-policy:technology-service-readers
criticality: moderate
source_record_id: catalog:service:enterprise-identity
source_version: "41"
relationships:
  - type: governed-by
    target: /policies/change-management-policy.md
  - type: operated-by
    target: /runbooks/identity-service-degradation.md
---

# Purpose

Provides illustrative identity context for the OKF pilot.

# Operations

Use the
[Identity Service Degradation Runbook](/runbooks/identity-service-degradation.md)
when an approved monitoring signal indicates reduced availability.

# Governance

Changes are governed by the
[Change Management Policy](/policies/change-management-policy.md).

