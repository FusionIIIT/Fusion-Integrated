# ELM Phase 2 — Issue and Improvement Log

This log records material findings from comparing the inherited Phase-1 ELM
against the supplied specification package and the changes made during Phase 2.

## Addressed in Phase 2

| ID | Finding | Improvement | Evidence |
|---|---|---|---|
| ELM-P2-01 | The inherited module exposed only minimal request API behavior and lacked employee-facing client workflow. | Added Fusion-registered ELM routes and a self-service form/list for employees to submit and inspect their own requests. | `client/src/modules/elm/`; `client/src/app/registry.ts` |
| ELM-P2-02 | Submitted requests could be edited or deleted instead of following the specified withdraw-and-resubmit lifecycle. | Rejects update/delete; employees can immediately withdraw only their own pending request. | `modules/elm/api/views.py`; `modules/elm/services/leave_requests.py` |
| ELM-P2-03 | No durable request transition history was exposed. | Records submission and withdrawal events and returns them with the request. | `modules/elm/models/leave.py`; `modules/elm/tests/test_leave_api.py` |
| ELM-P2-04 | There was no protection against overlapping pending or approved leave. | Rejects overlapping active requests and implements the specified opposite-half exception for single-day CL. | `modules/elm/services/leave_requests.py`; migrations 0004–0005 |
| ELM-P2-05 | Half-day data had no explicit representation or integrity rule. | Adds a `day_part` field, validates that half-day applies only to single-day CL, and enforces the rule at the database layer. | `modules/elm/models/leave.py`; `modules/elm/api/serializers.py` |
| ELM-P2-06 | Employees could not obtain a printable representation of an application. | Adds a print view containing request details, status, submission time, and recorded history. | `client/src/modules/elm/pages/LeaveRequestsPage.tsx`; `LeaveRequestsPage.css` |
| ELM-P2-07 | Permission, navigation, schema, and migration artifacts did not describe the Phase-2 surface. | Updates ELM registry grants, client route registration, OpenAPI, generated permissions, and migration history. | `modules/elm/registry.py`; `registry/permissions.json`; `openapi/fusion-integrated.v1.yaml` |

## Open specification gaps

| ID | Unresolved area | Why it remains open / required next input |
|---|---|---|
| ELM-P2-08 | Entitlement, balance, category eligibility, year-end lapse/carry-forward, and VL-to-EL conversion | Requires a leave-account ledger, policy/configuration rules, and auditable year-end processing. These are not implemented. |
| ELM-P2-09 | Holiday/RH calendar and faculty vacation-period validation | No authoritative effective published holiday/RH calendar or Academic Calendar vacation-period contract was identified. |
| ELM-P2-10 | Unit Head, Establishment, and higher-sanction approval routing/decisions | The Administration package provides department/designation data, but no authoritative Unit Head assignment or workflow route. Guessing from role names would risk misrouting decisions. |
| ELM-P2-11 | Substitute nomination, eligibility, consent, decline, and replacement | No assignment/consent workflow is implemented. |
| ELM-P2-12 | Approved-leave cancellation, extension, and resumption | These are multi-step lifecycle workflows requiring authority routing, balance adjustments, and (for resumption) attendance synchronization. |
| ELM-P2-13 | Leave administration, offline-sanctioned entries, SLA reminders/escalations, and notifications | Administrative authorization/configuration and task/notification infrastructure are not implemented for ELM. |
| ELM-P2-14 | Authenticated local end-to-end runtime | The local Fusion app is configured for IAM on `127.0.0.1:8001`; no compatible IAM service was running during verification. The Administration operator console is not the ERP-user IAM. |

## Readiness conclusion

Phase 2 improved and tested a bounded self-service slice, but the open items
above include central business rules and workflows. ELM must not be described
as deployment-ready against the full specification until these gaps are
resolved and integration-tested.
