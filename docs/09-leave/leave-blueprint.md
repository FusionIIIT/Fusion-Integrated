# Employee Leave Management (ELM) — Technical Blueprint

**Module Name:** Employee Leave Management (ELM)  
**Module Code:** `leave`  
**Base Path:** `/api/v1/leave/`  
**Specification Bundle:** `ELM_Specifications_Bundle_v1.4_FINAL` (PS v1.4, CFR/AFR v1.5, UC v1.4, BR v1.4, WF v1.6, RTM v1.5)  
**Status:** Phase 2 Blueprint — Awaiting Mentor Approval  

---

## 1. Traceability Table

### 1.1 Business Rules Traceability (36 Active Rules)

| Rule ID | Rule Name | Layer | Enforcement Point (Planned) | Notes |
|:---|:---|:---|:---|:---|
| **BR-EL-001** | Supported leave-category eligibility | `domain/` | `domain/validation.py::validate_category_eligibility` | Only CL, RH, SCL, EL, COL, VL supported; validates faculty vs non-faculty rules |
| **BR-EL-002** | Casual Leave entitlement and lapse | `domain/`, `services/` | `domain/ledger.py`, `services/year_end.py` | 8 days/year entitlement; lapses at year-end with no carry-forward |
| **BR-EL-003** | Restricted Holiday entitlement & applicability | `domain/`, `selectors/` | `domain/validation.py::validate_rh_dates` | 2 days/year; date must match active published RH in calendar; lapses at year-end |
| **BR-EL-004** | Special Casual Leave entitlement & admissibility | `domain/`, `services/` | `domain/validation.py`, `services/sanction.py` | 15 days/year max; admissibility judged by Sanctioning Authority; lapses at year-end |
| **BR-EL-005** | Non-faculty Earned Leave credit & carry-forward | `domain/`, `services/` | `domain/ledger.py`, `services/year_end.py` | 30 days/year credited to non-faculty; carries forward up to policy cap (e.g. 300) |
| **BR-EL-006** | Faculty Vacation Leave entitlement & vacation-period applicability | `domain/`, `selectors/` | `domain/validation.py::validate_vl_dates` | 60 days/year for faculty; requested interval must fall inside vacation periods from Academic Calendar |
| **BR-EL-007** | VL-to-EL year-end conversion | `domain/`, `services/` | `domain/year_end.py::convert_vl_to_el` | Unused faculty VL converts to EL at 2 VL : 1 EL including fractional days; VL does not carry forward |
| **BR-EL-008** | Treatment of EL created by VL conversion | `services/` | `services/year_end.py` | Converted EL credited to employee's EL ledger; carries forward and can be availed |
| **BR-EL-009** | Commuted Leave entitlement and treatment | `domain/`, `services/` | `domain/validation.py`, `services/year_end.py` | 20 days/year; medical evidence attached; unused balance carries forward |
| **BR-EL-010** | Half-day CL treatment | `domain/`, `models/` | `domain/counting.py::calculate_days_count` | First-half and second-half supported for CL only; counts as 0.5 day |
| **BR-EL-011** | Continuous-day counting | `domain/` | `domain/counting.py::calculate_days_count` | EL, COL, VL count continuously (including weekends & closed holidays). CL, SCL, RH count only working days |
| **BR-EL-012** | Applicant non-overlap with half-day CL exception | `selectors/`, `domain/` | `selectors/requests.py::check_applicant_overlap` | Disallow overlapping pending/approved requests, except different halves of CL on same date |
| **BR-EL-013** | Station Leave coupling | `domain/`, `models/` | `models/requests.py::LeaveRequest` | Station leave captured within same application (station address, departure/return dates) |
| **BR-EL-014** | Substitute eligibility | `selectors/`, `domain/` | `domain/validation.py::validate_substitute` | Exactly 1 substitute; must be another employee; != applicant; no overlapping pending/approved leave |
| **BR-EL-015** | Substitute consent gate and decline recovery | `domain/`, `services/` | `domain/state_machine.py`, `services/substitute.py` | Required consent blocks approval routing until accepted. Decline transitions to applicant action required |
| **BR-EL-016** | Unit Head final scope for CL/RH | `domain/`, `services/` | `domain/state_machine.py`, `services/review.py` | Unit Head is final approve/reject authority for CL/RH, including station leave (except Director) |
| **BR-EL-017** | Unit Head recommendation for higher-sanction leave | `domain/`, `services/` | `domain/state_machine.py`, `services/review.py` | SCL, EL, COL, VL: Unit Head records Recommended/Not Recommended; both route to higher authority |
| **BR-EL-018** | Higher-sanction routing | `services/` | `services/routing.py::resolve_next_authority` | SCL, EL, COL, VL route through hierarchy to resolved Sanctioning Authority |
| **BR-EL-019** | Authority resolution and optional Establishment step | `services/` | `services/routing.py::resolve_route` | Resolved by applicant kind, unit, designation, category, and config; Establishment step included if configured |
| **BR-EL-020** | Director self-sanction | `domain/`, `services/` | `domain/state_machine.py`, `services/requests.py` | If applicant is Director, routes to `Awaiting Director Self-Sanction` directly (after substitute if needed) |
| **BR-EL-022** | Immediate withdrawal of pending request | `domain/`, `services/` | `domain/state_machine.py`, `services/requests.py` | Applicant may withdraw from any pending state prior to final approval; halts workflow immediately |
| **BR-EL-023** | Cancellation of approved leave before start | `domain/`, `services/` | `domain/state_machine.py`, `services/cancellation.py` | Available only before start date; routes through same hierarchy; approved cancellation restores deducted balance |
| **BR-EL-024** | Fresh application after cancellation | `domain/` | `domain/validation.py` | Cancelled leaves cannot be edited or revived; new leave requires fresh application |
| **BR-EL-025** | Extension of ongoing EL/COL/VL | `domain/`, `services/` | `domain/state_machine.py`, `services/extension.py` | Available during ongoing EL/COL/VL; posts only incremental additional days; rejection leaves base unchanged |
| **BR-EL-027** | Resumption applicability and review authority | `domain/`, `services/` | `domain/state_machine.py`, `services/resumption.py` | Applicable to EL, COL, VL; employee declares actual date; reviewed by Sanctioning Authority |
| **BR-EL-028** | Normal, early, and late resumption outcome | `domain/`, `services/` | `domain/resumption.py`, `services/resumption.py` | Normal: no adjustment; Early: restores unavailed days to ledger; Late: deducts extra days from balance |
| **BR-EL-029** | Offline-sanctioned leave synchronization | `services/` | `services/offline.py::record_offline_leave` | Admin creates pre-sanctioned leave with reference details; writes immediate debit to ledger; no approval workflow |
| **BR-EL-030** | Current configured policy and hierarchy | `domain/`, `selectors/` | `selectors/policy.py` | Validation and routing use current active policy/hierarchy records without draft/publish lifecycle |
| **BR-EL-031** | Effective published holiday/RH calendar | `selectors/` | `selectors/calendar.py` | Date/RH validation uses active published calendar for current calendar year |
| **BR-EL-032** | SLA reminder on still-pending task | `services/`, `tasks/` | `services/sla.py::process_sla_reminders` | Generates reminder notification for assigned actor if task remains pending at reminder threshold |
| **BR-EL-033** | SLA escalation on still-pending task | `services/`, `tasks/` | `services/sla.py::process_sla_escalations` | Generates escalation notification and optional route advance if task exceeds escalation threshold |
| **BR-EL-034** | No post-submission modification | `domain/`, `api/` | `domain/state_machine.py`, `api/views.py` | Replaces retired BR-EL-021; pending requests cannot be patched; must withdraw and reapply |
| **BR-EL-035** | Actionable task assignment notification | `services/` | `services/notifications.py` | System creates in-app notification record when task is assigned to substitute, reviewer, or sanctioner |
| **BR-EL-036** | Role-based authorization | `api/` | `fusion_auth/permissions.py` | All endpoints gated by `HasModuleGrant("leave")` and `HasPermission(...)` |
| **BR-EL-037** | Administrative maintenance is not sanctioning | `services/` | `services/admin_records.py` | Admin balance adjustments and offline records are marked with audit distinction from workflow sanctions |
| **BR-EL-038** | Configurable SLA thresholds | `models/`, `api/` | `models/sla.py::SlaThreshold` | Configurable reminder and escalation hours per task type and role |

*Note: BR-EL-021 and BR-EL-026 are retired in the specification and are not cited in active code.*

---

### 1.2 Use Cases Traceability (20 Active Use Cases)

| Use Case ID | Use Case Name | Primary Actor | Layer | Enforcement Point |
|:---|:---|:---|:---|:---|
| **EL-UC-001** | Apply for Leave | Employee | `api/`, `services/` | `services/requests.py::apply_for_leave` |
| **EL-UC-002** | Respond to Substitute Request | Substitute | `api/`, `services/` | `services/substitute.py::respond_to_substitute` |
| **EL-UC-003** | Review Leave-Related Request at Unit Head | Unit Head | `api/`, `services/` | `services/review.py::review_unit_head` |
| **EL-UC-004** | Verify & Route Higher-Sanction Request | Establishment | `api/`, `services/` | `services/review.py::route_establishment` |
| **EL-UC-005** | Make Final Sanctioning Decision | Sanctioning Authority | `api/`, `services/` | `services/sanction.py::sanction_request` |
| **EL-UC-007** | Withdraw Pending Request | Employee | `api/`, `services/` | `services/requests.py::withdraw_request` |
| **EL-UC-008** | Request Cancellation of Approved Leave | Employee | `api/`, `services/` | `services/cancellation.py::request_cancellation` |
| **EL-UC-009** | Request Extension of Ongoing Leave | Employee | `api/`, `services/` | `services/extension.py::request_extension` |
| **EL-UC-010** | Submit Resumption of Duty | Employee | `api/`, `services/` | `services/resumption.py::submit_resumption` |
| **EL-UC-011** | Review Resumption | Sanctioning Authority | `api/`, `services/` | `services/resumption.py::review_resumption` |
| **EL-UC-012** | View Leave Balances and History | Employee | `api/`, `selectors/` | `selectors/balances.py`, `selectors/history.py` |
| **EL-UC-013** | Obtain Printable/Exportable Application | Employee | `api/`, `selectors/` | `selectors/exports.py::generate_application_summary` |
| **EL-UC-014** | Maintain Policy & Hierarchy Configuration | Leave Administrator | `api/`, `services/` | `services/policy.py::update_policy` |
| **EL-UC-015** | Maintain & Publish Holiday/RH Calendar | Leave Administrator | `api/`, `services/` | `services/calendar.py::publish_calendar` |
| **EL-UC-016** | Record Already-Sanctioned Offline Leave | Leave Administrator | `api/`, `services/` | `services/offline.py::record_offline_leave` |
| **EL-UC-017** | Maintain Authorized Leave Records | Leave Administrator | `api/`, `services/` | `services/admin_records.py::adjust_balance` |
| **EL-UC-018** | Configure Workflow SLA Thresholds | Leave Administrator | `api/`, `services/` | `services/sla.py::configure_sla_thresholds` |
| **EL-UC-019** | Nominate Replacement Substitute After Decline | Employee | `api/`, `services/` | `services/substitute.py::nominate_replacement` |
| **EL-UC-020** | Execute Year-End Leave Processing | System (Scheduler) | `tasks/`, `services/` | `services/year_end.py::execute_year_end_processing` |
| **EL-UC-021** | Process SLA Threshold Event | System (Scheduler) | `tasks/`, `services/` | `services/sla.py::process_sla_events` |

*Note: EL-UC-006 (Modify Pending Request) is retired.*

---

## 2. Domain Model

### 2.1 Core Entities & Database Invariants

```
+--------------------------------------------------------------------------------+
|                                  LeavePolicy                                   |
|  - id, academic_year, cl_entitlement (8), rh_entitlement (2),                 |
|    scl_entitlement (15), faculty_vl_entitlement (60), nonfaculty_el_credit (30), |
|    col_entitlement (20), vl_to_el_ratio (2.0), max_el_carry_forward (300),     |
|    max_col_carry_forward (240), establishment_step_enabled (bool)             |
+--------------------------------------------------------------------------------+

+-------------------------------------+    +------------------------------------+
|           HolidayCalendar           |    |            HolidayItem             |
|  - id, year, is_published,          |--->|  - id, calendar_id, date, name,   |
|    published_at, published_by_user |    |    is_restricted_holiday (bool)    |
+-------------------------------------+    +------------------------------------+

+--------------------------------------------------------------------------------+
|                                LeaveLedgerEntry                                |
|  - id, user_id (int), category (CL/RH/SCL/EL/COL/VL), delta_days (Decimal),    |
|    transaction_type (CREDIT/DEBIT/LAPSE/CONVERSION/RESTORATION/ADJUSTMENT),    |
|    reason, reference_id (e.g. request_id), created_at, created_by_user_id      |
|  -> INVARIANT: Append-only ledger; balance = SUM(delta_days)                   |
+--------------------------------------------------------------------------------+

+--------------------------------------------------------------------------------+
|                                  LeaveRequest                                  |
|  - id, user_id (int), category, start_date, end_date, half_day, days_count,    |
|    purpose, station_leave_applied, station_details (json), status (StateEnum),|
|    substitute_user_id (int?), substitute_status (PENDING/ACCEPTED/DECLINED),  |
|    unit_head_recommendation (RECOMMENDED/NOT_RECOMMENDED/NONE),                |
|    current_assignee_role, current_assignee_user_id (int?),                     |
|    department (str snapshot), is_offline_record (bool),                        |
|    created_at, updated_at                                                      |
+--------------------------------------------------------------------------------+
       |                                              |
       v 1..*                                         v 0..*
+-----------------------------+               +----------------------------------+
|       LeaveAuditEvent       |               |          LeaveExtension          |
|  - id, request_id, event,   |               |  - id, request_id, extend_from,  |
|    from_state, to_state,    |               |    extend_to, incremental_days,  |
|    actor_user_id, role,     |               |    reason, substitute_user_id,   |
|    remarks, timestamp       |               |    status (StateEnum)            |
+-----------------------------+               +----------------------------------+
                                                      |
                                                      v 0..*
                                              +----------------------------------+
                                              |         LeaveResumption          |
                                              |  - id, request_id, actual_date,  |
|                                             |    resumption_type, adj_days,    |
|                                             |    status, reviewed_by_user_id   |
+---------------------------------------------+----------------------------------+
```

### 2.2 Database Constraints & Integrity Rules
1. **User References:** Plain integer `user_id` (`UserScopedModel`). Absolutely no ForeignKeys to auth tables or cross-module boundaries (`ADR-0013`).
2. **Append-Only Ledger:** `LeaveLedgerEntry` does not support `update` or `delete`. Balances are dynamically calculated or aggregated using `SUM(delta_days)`.
3. **No Overlapping Leave:** Enforced at validation time and backed by database integrity indices.
4. **Audit Immutability:** `LeaveAuditEvent` rows are strictly append-only.

---

## 3. State Machine (Declarative Transitions)

Movement through request lifecycles (CW-EL-01 to CW-EL-04) is governed by an explicit declarative transition registry.

### 3.1 Composite Workflow 1: New Leave Processing & Pending Withdrawal (CW-EL-01)

| Transition # | From State | Event | Actor | Guard / Condition | Resulting State |
|:---|:---|:---|:---|:---|:---|
| **T01** | `DRAFT` | `SUBMIT` | Employee | Valid submission; substitute required | `AWAITING_SUBSTITUTE_RESPONSE` |
| **T02** | `DRAFT` | `SUBMIT` | Employee | Valid submission; no substitute; applicant is Director | `AWAITING_DIRECTOR_SELF_SANCTION` |
| **T03** | `DRAFT` | `SUBMIT` | Employee | Valid submission; no substitute; applicant is not Director | `AWAITING_UNIT_HEAD_REVIEW` |
| **T04** | `AWAITING_SUBSTITUTE_RESPONSE` | `SUBSTITUTE_ACCEPT` | Substitute | Applicant is Director | `AWAITING_DIRECTOR_SELF_SANCTION` |
| **T05** | `AWAITING_SUBSTITUTE_RESPONSE` | `SUBSTITUTE_ACCEPT` | Substitute | Applicant is not Director | `AWAITING_UNIT_HEAD_REVIEW` |
| **T06** | `AWAITING_SUBSTITUTE_RESPONSE` | `SUBSTITUTE_DECLINE` | Substitute | — | `APPLICANT_ACTION_REQUIRED` |
| **T07** | `APPLICANT_ACTION_REQUIRED` | `NOMINATE_REPLACEMENT` | Employee | Valid replacement substitute nominated | `AWAITING_SUBSTITUTE_RESPONSE` |
| **T08** | `AWAITING_UNIT_HEAD_REVIEW` | `APPROVE` | Unit Head | Category is CL or RH | `APPROVED` |
| **T09** | `AWAITING_UNIT_HEAD_REVIEW` | `REJECT` | Unit Head | Category is CL or RH | `REJECTED` |
| **T10** | `AWAITING_UNIT_HEAD_REVIEW` | `RECOMMEND` | Unit Head | Higher-sanction (SCL/EL/COL/VL); Establishment enabled | `AWAITING_ESTABLISHMENT_ROUTING` |
| **T11** | `AWAITING_UNIT_HEAD_REVIEW` | `RECOMMEND` | Unit Head | Higher-sanction; Establishment disabled | `AWAITING_FINAL_SANCTION_DECISION` |
| **T12** | `AWAITING_UNIT_HEAD_REVIEW` | `NOT_RECOMMEND` | Unit Head | Higher-sanction; Establishment enabled | `AWAITING_ESTABLISHMENT_ROUTING` |
| **T13** | `AWAITING_UNIT_HEAD_REVIEW` | `NOT_RECOMMEND` | Unit Head | Higher-sanction; Establishment disabled | `AWAITING_FINAL_SANCTION_DECISION` |
| **T14** | `AWAITING_ESTABLISHMENT_ROUTING` | `ROUTE` | Establishment | Routing verified | `AWAITING_FINAL_SANCTION_DECISION` |
| **T15** | `AWAITING_FINAL_SANCTION_DECISION` | `APPROVE` | Sanctioning Authority | — | `APPROVED` |
| **T16** | `AWAITING_FINAL_SANCTION_DECISION` | `REJECT` | Sanctioning Authority | — | `REJECTED` |
| **T17** | `AWAITING_DIRECTOR_SELF_SANCTION` | `APPROVE` | Director | Self-sanction | `APPROVED` |
| **T18** | `AWAITING_DIRECTOR_SELF_SANCTION` | `REJECT` | Director | Self-sanction | `REJECTED` |
| **T19** | `ANY_PENDING_STATE`* | `WITHDRAW` | Employee | Request is still pending final decision | `WITHDRAWN` |

*\*`ANY_PENDING_STATE` includes: `AWAITING_SUBSTITUTE_RESPONSE`, `APPLICANT_ACTION_REQUIRED`, `AWAITING_UNIT_HEAD_REVIEW`, `AWAITING_ESTABLISHMENT_ROUTING`, `AWAITING_FINAL_SANCTION_DECISION`, `AWAITING_DIRECTOR_SELF_SANCTION`.*

---

### 3.2 Composite Workflow 2: Approved Leave Cancellation (CW-EL-02)

| Transition # | From State | Event | Actor | Guard / Condition | Resulting State |
|:---|:---|:---|:---|:---|:---|
| **T20** | `APPROVED` | `REQUEST_CANCELLATION` | Employee | Leave not yet started | `CANCELLATION_PENDING_UNIT_HEAD` |
| **T21** | `CANCELLATION_PENDING_UNIT_HEAD` | `APPROVE_CANCELLATION` | Unit Head | Original was Unit-Head-final (CL/RH) | `CANCELLED` |
| **T22** | `CANCELLATION_PENDING_UNIT_HEAD` | `REJECT_CANCELLATION` | Unit Head | Original was Unit-Head-final (CL/RH) | `APPROVED` (Unchanged) |
| **T23** | `CANCELLATION_PENDING_UNIT_HEAD` | `RECOMMEND_CANCELLATION` | Unit Head | Higher-sanction; Establishment enabled | `CANCELLATION_PENDING_ESTABLISHMENT` |
| **T24** | `CANCELLATION_PENDING_UNIT_HEAD` | `RECOMMEND_CANCELLATION` | Unit Head | Higher-sanction; Establishment disabled | `CANCELLATION_PENDING_FINAL_DECISION` |
| **T25** | `CANCELLATION_PENDING_ESTABLISHMENT` | `ROUTE_CANCELLATION` | Establishment | Context verified | `CANCELLATION_PENDING_FINAL_DECISION` |
| **T26** | `CANCELLATION_PENDING_FINAL_DECISION` | `APPROVE_CANCELLATION` | Sanctioning Authority | — | `CANCELLED` |
| **T27** | `CANCELLATION_PENDING_FINAL_DECISION` | `REJECT_CANCELLATION` | Sanctioning Authority | — | `APPROVED` (Unchanged) |

---

### 3.3 Composite Workflow 3: Ongoing Leave Extension (CW-EL-03)

| Transition # | From State | Event | Actor | Guard / Condition | Resulting State |
|:---|:---|:---|:---|:---|:---|
| **T28** | `APPROVED` (Ongoing) | `REQUEST_EXTENSION` | Employee | EL/COL/VL ongoing; substitute required | `EXT_AWAITING_SUBSTITUTE` |
| **T29** | `APPROVED` (Ongoing) | `REQUEST_EXTENSION` | Employee | EL/COL/VL ongoing; no substitute required | `EXT_AWAITING_UNIT_HEAD` |
| **T30** | `EXT_AWAITING_SUBSTITUTE` | `SUBSTITUTE_ACCEPT` | Substitute | — | `EXT_AWAITING_UNIT_HEAD` |
| **T31** | `EXT_AWAITING_SUBSTITUTE` | `SUBSTITUTE_DECLINE` | Substitute | — | `EXT_APPLICANT_ACTION_REQUIRED` |
| **T32** | `EXT_APPLICANT_ACTION_REQUIRED` | `NOMINATE_REPLACEMENT` | Employee | Replacement nominated | `EXT_AWAITING_SUBSTITUTE` |
| **T33** | `EXT_AWAITING_UNIT_HEAD` | `RECOMMEND` | Unit Head | Establishment enabled | `EXT_PENDING_ESTABLISHMENT` |
| **T34** | `EXT_AWAITING_UNIT_HEAD` | `RECOMMEND` | Unit Head | Establishment disabled | `EXT_PENDING_FINAL_DECISION` |
| **T35** | `EXT_PENDING_ESTABLISHMENT` | `ROUTE` | Establishment | — | `EXT_PENDING_FINAL_DECISION` |
| **T36** | `EXT_PENDING_FINAL_DECISION` | `APPROVE` | Sanctioning Authority | Incremental days posted to ledger | `EXTENDED` |
| **T37** | `EXT_PENDING_FINAL_DECISION` | `REJECT` | Sanctioning Authority | Original leave unchanged | `EXTENSION_REJECTED` |
| **T38** | `ANY_EXT_PENDING_STATE` | `WITHDRAW` | Employee | Extension pending | `EXTENSION_WITHDRAWN` |

---

### 3.4 Composite Workflow 4: Resumption Review (CW-EL-04)

| Transition # | From State | Event | Actor | Guard / Condition | Resulting State |
|:---|:---|:---|:---|:---|:---|
| **T39** | `APPROVED` / `EXTENDED` | `SUBMIT_RESUMPTION` | Employee | Returned from EL/COL/VL | `RESUMPTION_REVIEW_PENDING` |
| **T40** | `RESUMPTION_REVIEW_PENDING` | `REVIEW_NORMAL` | Sanctioning Authority | Actual date == Approved end date | `RESUMPTION_REVIEWED_NORMAL` |
| **T41** | `RESUMPTION_REVIEW_PENDING` | `REVIEW_EARLY` | Sanctioning Authority | Actual date < Approved end date; restores unavailed days | `RESUMPTION_REVIEWED_EARLY` |
| **T42** | `RESUMPTION_REVIEW_PENDING` | `REVIEW_LATE` | Sanctioning Authority | Actual date > Approved end date; debits extra days | `RESUMPTION_REVIEWED_LATE` |

---

## 4. Permission List (`registry.py`)

```python
MODULE = {
    "code": "leave",
    "label": "Leave Management",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Services",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # Employee self-service
    {"code": "leave.apply", "label": "Apply for Leave", "icon": "CalendarPlus", "to": "/leave/apply", "required_permission": "leave.request.create", "sort_order": 10},
    {"code": "leave.mine", "label": "My Requests", "icon": "ClockCounterClockwise", "to": "/leave/mine", "required_permission": "leave.request.view_self", "sort_order": 20},
    {"code": "leave.balances", "label": "My Balances", "icon": "ChartPieSlice", "to": "/leave/balances", "required_permission": "leave.balance.view_self", "sort_order": 30},
    {"code": "leave.substitute", "label": "Substitute Requests", "icon": "UserSwitch", "to": "/leave/substitute-requests", "required_permission": "leave.substitute.respond", "sort_order": 40},
    
    # Reviewer / Approver roles
    {"code": "leave.unit_head", "label": "Unit Head Approvals", "icon": "Checks", "to": "/leave/unit-head-review", "required_permission": "leave.request.review", "sort_order": 50},
    {"code": "leave.establishment", "label": "Establishment Routing", "icon": "GitFork", "to": "/leave/establishment-queue", "required_permission": "leave.request.route", "sort_order": 60},
    {"code": "leave.sanctions", "label": "Sanctioning Approvals", "icon": "Stamp", "to": "/leave/sanction-queue", "required_permission": "leave.request.sanction", "sort_order": 70},
    {"code": "leave.resumptions", "label": "Resumption Reviews", "icon": "CalendarCheck", "to": "/leave/resumption-reviews", "required_permission": "leave.resumption.review", "sort_order": 80},
    
    # Department Head / Admin balance visibility
    {"code": "leave.department_balances", "label": "Department Balances", "icon": "Users", "to": "/leave/department-balances", "required_permission": "leave.balance.view", "sort_order": 85},

    # Administrative maintenance
    {"code": "leave.offline", "label": "Record Offline Leave", "icon": "NotePencil", "to": "/leave/offline-entry", "required_permission": "leave.offline.create", "sort_order": 90},
    {"code": "leave.calendar", "label": "Holiday Calendar", "icon": "Calendar", "to": "/leave/holiday-calendar", "required_permission": "leave.calendar.manage", "sort_order": 95},
    {"code": "leave.policy", "label": "Leave Policy & SLA", "icon": "Sliders", "to": "/leave/policy-config", "required_permission": "leave.policy.manage", "sort_order": 100},
]

PERMISSIONS = [
    ("leave.request.create", "Submit a leave application"),
    ("leave.request.view_self", "View own leave applications"),
    ("leave.request.delete", "Withdraw own pending leave application"),
    ("leave.request.cancel", "Request cancellation of approved leave"),
    ("leave.request.extend", "Request extension of ongoing leave"),
    ("leave.substitute.respond", "Accept or decline substitute requests"),
    ("leave.request.review", "Unit Head recommendation or CL/RH approval"),
    ("leave.request.route", "Establishment verification and routing"),
    ("leave.request.sanction", "Sanctioning Authority approval or rejection"),
    ("leave.resumption.submit", "Submit resumption of duty"),
    ("leave.resumption.review", "Review resumption of duty"),
    ("leave.balance.view_self", "View own leave balances and ledger history"),
    ("leave.balance.view", "View scoped employee leave balances"),
    ("leave.balance.update", "Adjust leave balance manually"),
    ("leave.offline.create", "Retrospectively record offline-sanctioned leave"),
    ("leave.calendar.manage", "Manage and publish holiday and RH calendar"),
    ("leave.policy.manage", "Configure leave policy parameters"),
    ("leave.sla.manage", "Configure SLA thresholds"),
    ("leave.export.view", "Export printable leave application summary"),
]

SYSTEM_PERMISSIONS = [
    "leave.year_end.execute",
    "leave.sla.process",
]

# Role mapping against globals_designation and basic kinds
_EMPLOYEE = [
    "leave.request.create",
    "leave.request.view_self",
    "leave.request.delete",
    "leave.request.cancel",
    "leave.request.extend",
    "leave.substitute.respond",
    "leave.resumption.submit",
    "leave.balance.view_self",
    "leave.export.view",
]

_UNIT_HEAD = [
    *_EMPLOYEE,
    "leave.request.review",
    "leave.balance.view",
]

_ESTABLISHMENT = [
    *_EMPLOYEE,
    "leave.request.route",
    "leave.balance.view",
]

_SANCTIONING_AUTHORITY = [
    *_EMPLOYEE,
    "leave.request.sanction",
    "leave.resumption.review",
    "leave.balance.view",
]

_LEAVE_ADMIN = [
    *_EMPLOYEE,
    "leave.offline.create",
    "leave.calendar.manage",
    "leave.policy.manage",
    "leave.sla.manage",
    "leave.balance.view",
    "leave.balance.update",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "HOD": _UNIT_HEAD,
    "Head of Department": _UNIT_HEAD,
    "Deputy Registrar (Estt.)": _ESTABLISHMENT,
    "Dean": _SANCTIONING_AUTHORITY,
    "Registrar": _SANCTIONING_AUTHORITY,
    "Director": _SANCTIONING_AUTHORITY,
    "Leave Administrator": _LEAVE_ADMIN,
}
```

---

## 5. API Endpoints (`/api/v1/leave/`)

| Method | Endpoint | Module Gate | Permission Gate | Return Shape | Rules Enforced |
|:---|:---|:---|:---|:---|:---|
| `POST` | `/api/v1/leave/requests/` | `leave` | `leave.request.create` | `LeaveRequestDetailSerializer` | BR-EL-001..015, 030, 031, 034 |
| `GET` | `/api/v1/leave/requests/mine/` | `leave` | `leave.request.view_self` | `Paginated[LeaveRequestListSerializer]` | BR-EL-036 |
| `GET` | `/api/v1/leave/requests/{id}/` | `leave` | `leave.request.view_self` | `LeaveRequestDetailSerializer` | BR-EL-036 (Owner or authorized role) |
| `POST` | `/api/v1/leave/requests/{id}/withdraw/` | `leave` | `leave.request.delete` | `LeaveRequestDetailSerializer` | BR-EL-022, 034 |
| `POST` | `/api/v1/leave/requests/{id}/cancel/` | `leave` | `leave.request.cancel` | `LeaveRequestDetailSerializer` | BR-EL-023, 024 |
| `POST` | `/api/v1/leave/requests/{id}/extend/` | `leave` | `leave.request.extend` | `LeaveExtensionSerializer` | BR-EL-025 |
| `GET` | `/api/v1/leave/substitute-requests/` | `leave` | `leave.substitute.respond` | `List[SubstituteRequestSerializer]` | BR-EL-014, 015 |
| `POST` | `/api/v1/leave/substitute-requests/{id}/respond/` | `leave` | `leave.substitute.respond` | `SubstituteResponseSerializer` | BR-EL-015 |
| `POST` | `/api/v1/leave/requests/{id}/replace-substitute/` | `leave` | `leave.request.create` | `LeaveRequestDetailSerializer` | BR-EL-014, 015 |
| `GET` | `/api/v1/leave/review-queue/` | `leave` | `leave.request.review` | `Paginated[ReviewQueueItemSerializer]` | BR-EL-016, 017 |
| `POST` | `/api/v1/leave/review-queue/{id}/review/` | `leave` | `leave.request.review` | `LeaveRequestDetailSerializer` | BR-EL-016, 017 |
| `GET` | `/api/v1/leave/establishment-queue/` | `leave` | `leave.request.route` | `Paginated[ReviewQueueItemSerializer]` | BR-EL-018, 019 |
| `POST` | `/api/v1/leave/establishment-queue/{id}/route/` | `leave` | `leave.request.route` | `LeaveRequestDetailSerializer` | BR-EL-018, 019 |
| `GET` | `/api/v1/leave/sanction-queue/` | `leave` | `leave.request.sanction` | `Paginated[ReviewQueueItemSerializer]` | BR-EL-004, 018, 019, 020 |
| `POST` | `/api/v1/leave/sanction-queue/{id}/sanction/` | `leave` | `leave.request.sanction` | `LeaveRequestDetailSerializer` | BR-EL-004, 018, 019, 020 |
| `POST` | `/api/v1/leave/requests/{id}/resumption/` | `leave` | `leave.resumption.submit` | `LeaveResumptionSerializer` | BR-EL-027 |
| `POST` | `/api/v1/leave/resumptions/{id}/review/` | `leave` | `leave.resumption.review` | `LeaveResumptionSerializer` | BR-EL-027, 028 |
| `GET` | `/api/v1/leave/balances/mine/` | `leave` | `leave.balance.view_self` | `LeaveBalancesSerializer` | BR-EL-002..009 |
| `GET` | `/api/v1/leave/balances/` | `leave` | `leave.balance.view` | `Paginated[ScopedBalancesSerializer]` | BR-EL-036 (Scoped by dept) |
| `GET` | `/api/v1/leave/requests/{id}/export/` | `leave` | `leave.export.view` | `PrintableLeaveApplicationSerializer` | BR-EL-036 |
| `POST` | `/api/v1/leave/offline-records/` | `leave` | `leave.offline.create` | `OfflineLeaveRecordSerializer` | BR-EL-029, 037 |
| `GET` | `/api/v1/leave/calendar/` | `leave` | `IsAuthenticated` | `HolidayCalendarSerializer` | BR-EL-031 |
| `POST` | `/api/v1/leave/calendar/` | `leave` | `leave.calendar.manage` | `HolidayCalendarSerializer` | BR-EL-031 |
| `GET` | `/api/v1/leave/policy/` | `leave` | `leave.policy.manage` | `LeavePolicySerializer` | BR-EL-030 |
| `PUT` | `/api/v1/leave/policy/` | `leave` | `leave.policy.manage` | `LeavePolicySerializer` | BR-EL-030 |
| `GET` | `/api/v1/leave/sla/thresholds/` | `leave` | `leave.sla.manage` | `List[SlaThresholdSerializer]` | BR-EL-038 |
| `PUT` | `/api/v1/leave/sla/thresholds/` | `leave` | `leave.sla.manage` | `List[SlaThresholdSerializer]` | BR-EL-038 |

**Fusion-client `INTEGRATED_MODULES` Sidebar Entry:**
```javascript
{
  id: "leave",
  label: "Leave",
  icon: "CalendarBlank",
  to: "/leave",
  section: "Services",
}
```

---

## 6. Contracts (`modules/leave/contracts.py`)

### 6.1 Public Surface Exposed by `leave`
All cross-module getters are plural (`ops/checks/contracts_are_plural.py` compliant):

```python
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from dataclasses import dataclass

@dataclass(frozen=True)
class LeaveStatusDTO:
    user_id: int
    is_on_leave: bool
    category: str | None = None
    start_date: date | None = None
    end_date: date | None = None

@dataclass(frozen=True)
class UserLeaveBalancesDTO:
    user_id: int
    balances: dict[str, Decimal]

def get_active_leaves(user_ids: Sequence[int], on_date: date) -> dict[int, LeaveStatusDTO]:
    """Returns active leave status for given user IDs on a specific date."""
    ...

def get_leave_balances(user_ids: Sequence[int]) -> dict[int, UserLeaveBalancesDTO]:
    """Returns calculated balances across all categories for given user IDs."""
    ...
```

### 6.2 External Dependencies Needed by `leave`
1. `modules.directory.contracts.get_users(user_ids)`: Batched user projection for employee kind (`faculty` vs `staff`), display name, and department/unit.
2. `Academic Calendar` (EXT-01): Vacation periods for faculty Vacation Leave (VL) validation (via mockable external service adapter or configured calendar entries).

---

## 7. Scheduled Work (`modules/leave/schedule.py`)

Celery beat configuration for background jobs:

| Task Name | Schedule | Function | Real-World Impact if Not Running |
|:---|:---|:---|:---|
| `leave_year_end_processing` | Annually on Jan 1 (`0 0 1 1 *`) | `tasks.year_end_processing` | CL/RH/SCL fail to lapse; Faculty VL not converted to EL; balances drift indefinitely |
| `leave_sla_escalation` | Every 30 minutes (`*/30 * * * *`) | `tasks.process_sla_clocks` | Pending tasks get no reminders or escalations; bottlenecks stall approval pipelines |

---

## 8. Open Questions & Environment Clarifications

1. **Academic Calendar Vacation Periods (EXT-01):** The ERP does not currently ship a standalone `academic_calendar` service in `module-only` mode. We will provide a clean database-backed vacation period adapter in `leave` models with sensible default vacation periods so VL validation works completely offline and standalone.
2. **Designation Mapping:** Standard IIITDMJ designations in `globals_designation` (e.g., `HOD`, `Dean`, `Registrar`, `Director`, `Deputy Registrar (Estt.)`) are used for approval routing. If a designation is absent in testing, tests use `fake_iam` with exact designation strings.
3. **No Auth Tables in Business DB:** RBAC is strictly handled through `registry.py` -> `registry/permissions.json` -> IAM sync. No local `Role` or `UserRole` models are introduced.
