# RACK Capability and OKF Integration Map

Status: product-owner input required. This document makes no claim about RACK's
current implementation.

For each row use one state: `owned`, `integrated`, `planned`, `absent`, or
`unknown`. An `owned`, `integrated`, or `planned` claim requires an accountable
owner and evidence/roadmap reference.

| Capability | Current state | Accountable owner | Interface/evidence | Target OKF responsibility | Gap/decision |
|---|---|---|---|---|---|
| Knowledge authoring/approval | unknown | TBD | TBD | Source system or none | TBD |
| Source/catalog aggregation | unknown | TBD | TBD | Producer or none | TBD |
| Source identity/version/delete | unknown | TBD | TBD | Producer mapping | TBD |
| Classification/ACL preservation | unknown | TBD | TBD | Producer + enterprise PDP | TBD |
| OKF parsing/profile validation | unknown | TBD | TBD | Reuse framework contract | TBD |
| Immutable OCI release ingestion | unknown | TBD | TBD | Consumer input | TBD |
| Release catalog/channel pinning | unknown | TBD | TBD | Integrate or reuse gateway | TBD |
| Lexical/vector/hybrid indexing | unknown | TBD | TBD | Benchmark before selection | TBD |
| User/workload authentication | unknown | TBD | TBD | Enterprise identity adapter | TBD |
| Authorization before retrieval | unknown | TBD | TBD | Enterprise PDP/PEP | TBD |
| Citations/release trace | unknown | TBD | TBD | Consumer requirement | TBD |
| Agent runtime/tool control | unknown | TBD | TBD | Consumer responsibility | TBD |
| User experience/feedback | unknown | TBD | TBD | Consumer/feedback workflow | TBD |
| Audit/telemetry/SLO/support | unknown | TBD | TBD | Shared operations contract | TBD |
| Hosting/residency/recovery | unknown | TBD | TBD | Approved platform boundary | TBD |
| Product roadmap/exit strategy | unknown | TBD | TBD | Architecture decision | TBD |

Decision output: `producer`, `consumer`, `both with named boundaries`, or `no
pilot role`. Record chosen pilot interface, identity, data flow, release pinning,
PDP enforcement point, citations, telemetry, SLO, owner, and rollback.
