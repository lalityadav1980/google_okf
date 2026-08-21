---
type: Policy
title: Change Management Policy
description: Illustrative governance principles for controlled changes to technology services.
resource: https://sources.example.invalid/policies/change-management
tags: [technology, governance, change-management]
sources:
  - id: authoritative-policy
    resource: https://sources.example.invalid/policies/change-management
    title: Authoritative Change Management Policy
    author: team:technology-governance
    last_modified: 2026-08-18T09:00:00Z
generated:
  by: xyz-okf-sharepoint-producer/0.1.0
  at: 2026-08-18T09:05:00Z
verified:
  - by: human:policy-owner-id
    at: 2026-08-18T12:00:00Z
status: stable
stale_after: 2030-08-18T00:00:00Z
xyz_profile_version: "0.1"
concept_uid: kb:policy:change-management
domain: technology-governance
owner: team:technology-governance
classification: INTERNAL
acl_ref: authz-policy:technology-policy-readers
criticality: high
jurisdictions: [global]
source_record_id: sharepoint:pilot:change-management
source_version: "12.0"
relationships:
  - type: applies-to
    target: /services/enterprise-identity.md
---

# Purpose

This illustrative concept demonstrates how a controlled policy can be published
without making the OKF copy the legal system of record.[^authoritative-policy]

# Applicability

The policy applies to the
[Enterprise Identity Service](/services/enterprise-identity.md) in this example.

[^authoritative-policy]: Source mapped to `sources[id=authoritative-policy]`.

