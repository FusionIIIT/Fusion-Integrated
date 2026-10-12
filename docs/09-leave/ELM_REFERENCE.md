---
owner: platform
status: reviewed
last-reviewed: 2026-10-12
---

# Employee Leave Management reference

This is the implementation index for the synchronized ELM baseline. The source of truth is the
repository-level `ELM_Specifications_Bundle_v1.4_FINAL`; the legacy ERP apps are historical context,
not a template. ELM is a fresh domain module in `modules/leave` and follows the platform's module
boundaries.

## Scope

ELM supports Faculty and Staff, the six leave categories CL, RH, SCL, EL, COL, VL, and Station Leave
details embedded in the relevant application. It owns employee leave requests, workflow, calendars,
account entries, and audit history. User IDs are references; no ELM table has a cross-module foreign
key. Vacation periods are a read-only projection of the external Academic Calendar.

The system validates before submission, freezes submitted applications, assigns workflow actions,
and records every balance effect in `LeaveAccountEntry`. Cancellation, extension, and resumption are
follow-up requests. Offline-sanctioned leave is synchronized with evidence and does not start another
sanction workflow.

## Rule index

| Rule | Required behavior | Implementation location |
|---|---|---|
| BR-EL-001 | Only CL, RH, SCL, EL, COL, and VL are supported; category eligibility follows employee kind. | `domain/validation.py`; `domain/eligibility.py` |
| BR-EL-002 | CL is 8 days yearly and unused balance lapses. | `domain/eligibility.py`; `services/accounting.py` |
| BR-EL-003 | RH is 2 days yearly, limited to dates in the effective published RH calendar; unused balance lapses. | `services/requests.py`; `services/accounting.py` |
| BR-EL-004 | SCL is up to 15 days; its admissibility is decided by the authority, not an encoded purpose list. | `domain/eligibility.py`; `services/requests.py` |
| BR-EL-005 | Non-faculty staff receive 30 EL days yearly; unused EL carries forward. | `domain/eligibility.py`; `services/accounting.py` |
| BR-EL-006 | Faculty receive 60 VL days, usable only during a supplied vacation period. | `domain/eligibility.py`; `VacationPeriod`; `services/requests.py` |
| BR-EL-007 | At year end, unused faculty VL converts to EL at 2 VL : 1 EL, with fractional credit. | `services/accounting.py` |
| BR-EL-008 | Converted credit is ordinary EL and may carry forward or be used. | `LeaveAccountEntry`; `services/accounting.py` |
| BR-EL-009 | COL is 20 days yearly for eligible employees, balance controlled, with configurable medical evidence; unused balance carries forward. | `LeavePolicy`; `services/accounting.py` |
| BR-EL-010 | Approved half-day CL consumes 0.5 day. | `LeaveRequest.cl_portion`; `domain/validation.py` |
| BR-EL-011 | EL/COL/VL count every calendar day in the approved interval, including weekends and closed holidays. | `domain/validation.py` |
| BR-EL-012 | Active pending/approved overlaps are rejected; distinct first-half and second-half CL on one date may coexist. | `domain/validation.py`; `services/requests.py` |
| BR-EL-013 | Station Leave is captured with the leave application, including destination and departure/return. | `LeaveRequest`; `domain/validation.py` |
| BR-EL-014 | A substitute is another active employee, not the applicant, and has no overlapping pending/approved leave. | `services/requests.py` |
| BR-EL-015 | Required consent is accepted before routing; a decline permits one replacement or withdrawal. | `SubstituteResponse`; `services/requests.py` |
| BR-EL-016 | Unit Head is final for CL/RH. | `domain/state_machine.py`; `services/requests.py` |
| BR-EL-017 | Unit Head records Recommended / Not Recommended on higher-sanction leave; neither is a final decision. | `WorkflowTask.decision_kind`; `services/requests.py` |
| BR-EL-018 | Higher-sanction requests follow the current configured hierarchy. | `LeaveRouteConfiguration`; `domain/state_machine.py` |
| BR-EL-019 | Establishment verification is optional when configured; authority resolution uses current employee and route data. | `LeaveRouteConfiguration`; `services/requests.py` |
| BR-EL-020 | Director leave follows the Director self-sanction route. | `EmployeeProfile.is_director`; `domain/state_machine.py` |
| BR-EL-021 | Retired: pending submitted applications are not modified in place. | No update endpoint for submitted requests. |
| BR-EL-022 | Pending withdrawal is immediate and terminates remaining workflow tasks. | `services/requests.py` |
| BR-EL-023 | Pre-start cancellation follows the original hierarchy; approval reverses debits, rejection preserves the approval. | `services/requests.py` |
| BR-EL-024 | A changed leave period after cancellation requires a fresh application. | Follow-up request model and API. |
| BR-EL-025 | Ongoing EL/COL/VL extension validates and posts only the incremental days. | `services/requests.py` |
| BR-EL-026 | Retired identifier. | No behavior. |
| BR-EL-027 | EL/COL/VL resumption is reviewed by the original final authority. | `services/requests.py` |
| BR-EL-028 | Normal resumption changes no balance; early/late resumption posts the reviewed actual-period adjustment. | `domain/state_machine.py`; `services/requests.py` |
| BR-EL-029 | Offline leave requires sanction reference and evidence, consistency validation, and a balance entry; it does not route for a second approval. | `services/requests.py` |
| BR-EL-030 | Current policy and route values are used; no policy publication lifecycle exists. | `LeavePolicy`; `LeaveRouteConfiguration` |
| BR-EL-031 | Validation uses the currently published holiday/RH calendar until its replacement is published. | `HolidayCalendar`; `services/requests.py` |
| BR-EL-032 | Reminders run only while a task remains pending and are logged. | `tasks.process_leave_sla_thresholds` |
| BR-EL-033 | Escalation runs only while pending, notifies/reassigns to configured responsibility, and is logged. | `tasks.process_leave_sla_thresholds` |
| BR-EL-034 | Submitted requests cannot be edited. | Draft creation only; follow-up requests for later actions. |
| BR-EL-035 | Actionable task assignment sends a notification; final decisions notify the employee. | `services/notifications.py` |
| BR-EL-036 | Role and permission checks gate employee, processing, sanction, and administrator actions. | `api/views.py`; `registry/permissions.json` |
| BR-EL-037 | Record maintenance/offline entry does not confer sanction authority. | Separate `records.manage` permission and offline service. |
| BR-EL-038 | Reminder and escalation thresholds are configurable per workflow role. | `LeaveSLAConfiguration`; `api/serializers.py` |

## Use-case coverage

The API covers apply/submit, substitute response and replacement, Unit Head review, higher sanction,
withdrawal, cancellation, extension, resumption, balances and account history, printable application,
policy/calendar/routing/SLA administration, offline entry, account correction, and the scheduled
year-end and SLA triggers. The state machine and counting documents describe the sequencing and
arithmetic in detail.

## External dependencies and operational boundaries

- `EmployeeProfile` is populated from the HR/IAM employment and hierarchy projection.
- `VacationPeriod` is supplied by the Academic Calendar; ELM does not create vacation periods.
- The Celery beat schedule checks the configured year-end boundary daily and delivers notification
  outbox messages. A year-end run is idempotent by account-entry source key.
- API requests authenticate through IAM and use the server-side `leave_management` grant and
  fine-grained permissions.
