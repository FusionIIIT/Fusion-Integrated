# Employee Leave Management Phase 2 Traceability

## Baseline and scope

Phase 1 is preserved at `4e40661` on the original branch. Phase 2 work is on
the local `phase2-elm-hardening` branch. This document records the current
implementation state against the final ELM specification package; it does not
claim that unimplemented requirements are satisfied.

| CFR | Required behavior | Status | Evidence or next priority |
| --- | --- | --- | --- |
| CFR-EL-001 | Role-based ELM access | Partial, tested | Module and permission gates exist; processing/sanction/admin roles are absent. |
| CFR-EL-002 | Submit CL, RH, SCL, EL, COL, VL application | Partial, tested | API supports CL/RH and coupled Station Leave only. |
| CFR-EL-003 | Validate eligibility, balance, calendar, and overlap | Partial, tested | Dates, CL halves, request fields, and active-overlap checks exist; policy, balance, and calendar validation are missing. |
| CFR-EL-004 | CL entitlement and half-day treatment | Partial | Half-day representation exists; annual balance and lapse are missing. |
| CFR-EL-005 | RH entitlement and applicable calendar | Missing | No balance or RH calendar. |
| CFR-EL-006 | SCL entitlement and authority judgment | Missing | Category and workflow absent. |
| CFR-EL-007 | EL entitlement and carry-forward | Missing | Category, account, and year-end logic absent. |
| CFR-EL-008 | Faculty VL and VL-to-EL conversion | Missing | Calendar integration and conversion absent. |
| CFR-EL-009 | COL entitlement and evidence treatment | Missing | Category, balance, and evidence absent. |
| CFR-EL-010 | Continuous-day counting | Missing | No chargeable-day calculation. |
| CFR-EL-011 | Nominate eligible substitute | Missing | No substitute data or validation. |
| CFR-EL-012 | Substitute consent gate | Missing | No task/consent workflow. |
| CFR-EL-013 | Unit Head final CL/RH decision | Missing | Requests remain pending until withdrawn. |
| CFR-EL-014 | Higher-sanction routing and decision | Missing | No hierarchy or approval tasks. |
| CFR-EL-015 | Director self-sanction | Missing | No hierarchy integration. |
| CFR-EL-016 | Final decision, account update, communication | Missing | No approval, account, or notifications. |
| CFR-EL-017 | No in-place pending modification | Implemented, tested | API exposes no update; withdrawal is the change path. |
| CFR-EL-018 | Immediate pending withdrawal | Implemented, partially tested | Service transitions only pending requests to withdrawn; notification remains absent. |
| CFR-EL-019 | Pre-start approved leave cancellation | Missing | No cancellation request/state/routing. |
| CFR-EL-020 | Ongoing EL/COL/VL extension | Missing | No supported categories or extension model. |
| CFR-EL-021 | Resumption review and adjustments | Missing | No resumption model or leave account. |
| CFR-EL-022 | View balances and history | Partial | Employee can list own requests; balances are absent. |
| CFR-EL-023 | Printable/exportable application | Missing | No output endpoint. |
| CFR-EL-024 | Policy and hierarchy administration | Missing | No configuration model/UI. |
| CFR-EL-025 | Published holiday/RH calendar | Missing | No calendar model/UI. |
| CFR-EL-026 | Authorized record maintenance | Missing | No administrative service or audit controls. |
| CFR-EL-027 | Offline-sanctioned leave synchronization | Missing | No evidence, synchronization, or record path. |
| CFR-EL-028 | Year-end leave-account processing | Missing | No account or scheduled processing. |
| CFR-EL-029 | Configure SLA thresholds | Missing | No task or configuration model. |
| CFR-EL-030 | Notify task assignee | Missing | No workflow task/notification implementation. |
| CFR-EL-031 | Remind still-pending SLA task | Missing | No task/SLA processor. |
| CFR-EL-032 | Escalate still-pending SLA task | Missing | No task/SLA processor. |

## Phase 2 hardening increment

The initial correctness increment addresses three concrete defects found in the
read-only review:

| Defect | Root cause | Change | Verification |
| --- | --- | --- | --- |
| Invalid CL half value accepted outside HTTP | Domain validation accepted every CL half string | Domain validation and a database constraint restrict values to `full`, `first`, or `second`. | Domain and service regression tests pass. |
| Station Leave rule only enforced by serializer | Direct service callers could persist missing details | Shared domain validation rejects blank reason and Station Leave details; a database constraint rejects an empty persisted detail. | Domain and service regression tests pass. |
| Overlap ignored approved leave and concurrent empty sets | Query filtered only pending rows; row locks do not protect an empty result | Active status query includes approved rows. PostgreSQL writes take a transaction-scoped employee advisory lock before checking. | Unit tests cover the lock path; database/API integration tests await PostgreSQL. |

The advisory lock is intentionally PostgreSQL-specific because PostgreSQL is
the configured project database. A non-PostgreSQL backend retains row locking
but does not provide the empty-set race guarantee; it is not a supported
production deployment for this module.

## Verification limitations

`manage.py check` and the non-database domain/service regression tests pass.
The project has no Docker executable or accessible PostgreSQL service in this
environment, so migration, API, full-suite, and concurrency integration tests
cannot be completed here. Client type checking passes; Vitest worker execution
and production build need a less restricted filesystem process environment.

The generated OpenAPI contract must be regenerated with `manage.py spectacular
--fail-on-warn --file openapi/fusion-integrated.v1.yaml` once PostgreSQL-backed
checks can complete. It is deliberately not manually edited.
