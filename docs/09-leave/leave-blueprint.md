# Employee Leave Management (ELM) — Blueprint

Module Code: `leave`
Status: Synchronized Baseline v1.4
Architecture Reference: `modules/placement`

---

## Step 3.1 (a) — Traceability Table

| ID | Specification Requirement | Layer | Planned Enforcement Point | Notes |
|---|---|---|---|---|
| BR-EL-001 | Supported leave categories (CL, RH, SCL, EL, COL, VL) & applicability | Domain | `domain/rules.py::validate_category_applicability` | Enforced at application |
| BR-EL-002 | CL entitlement (8 days/yr) & lapses without carry forward | Domain/Services | `domain/rules.py`, `services/yearend.py` | Lapses at year end |
| BR-EL-003 | RH entitlement (2 days/yr) & calendar applicability | Domain/Services | `domain/rules.py::validate_rh`, `services/yearend.py` | Must match published RH |
| BR-EL-004 | SCL entitlement (up to 15 days/yr) & admissibility | Domain/Services | `domain/rules.py::validate_scl`, `services/yearend.py` | Authority judged, no carry-forward |
| BR-EL-005 | Non-faculty EL (30 days/yr) credit and carry forward | Domain/Services | `services/yearend.py::credit_annual_el` | Carries forward |
| BR-EL-006 | Faculty VL (60 days/yr) & academic vacation period applicability | Domain | `domain/rules.py::validate_vl_vacation` | Only during vacation periods |
| BR-EL-007 | VL-to-EL year-end conversion at 2 VL : 1 EL including fractions | Domain/Services | `services/yearend.py::convert_vl_to_el` | VL itself does not carry forward |
| BR-EL-008 | Converted EL credited to EL balance and usable | Models/Services | `services/yearend.py`, `models/ledger.py` | Credited via append-only ledger |
| BR-EL-009 | Commuted Leave (COL, 20 days/yr) & medical evidence | Domain/Services | `domain/rules.py::validate_col`, `services/apply.py` | Carries forward, evidence ref |
| BR-EL-010 | Half-day CL (first-half / second-half) consumes 0.5 day | Domain | `domain/counting.py::calculate_days` | 0.5 day deducted |
| BR-EL-011 | Continuous-day counting for EL, COL, VL across weekends/holidays | Domain | `domain/counting.py::calculate_days` | Intervening weekends/holidays count |
| BR-EL-012 | Applicant non-overlap; same-day CL different halves allowed | Domain/Selectors | `selectors/requests.py::check_overlap` | Half-day CL exception supported |
| BR-EL-013 | Station Leave details captured inside same application | Models/Services | `models/requests.py`, `services/apply.py` | Not a separate process |
| BR-EL-014 | Substitute eligibility: 1 employee, not applicant, no leave overlap | Domain/Services | `domain/rules.py::validate_substitute` | Verified at nomination |
| BR-EL-015 | Substitute consent gate and decline recovery | Domain/Services | `domain/state_machine.py`, `services/substitute.py` | Routing waits on accept |
| BR-EL-016 | Unit Head final scope for CL/RH | Domain/Services | `domain/rules.py`, `services/review.py` | Unit Head final approve/reject |
| BR-EL-017 | Unit Head recommendation for SCL, EL, COL, VL | Domain/Services | `domain/rules.py`, `services/review.py` | Rec/Not-Rec both route upward |
| BR-EL-018 | Higher-sanction routing to competent authority | Services | `services/routing.py::route_request` | Routed per hierarchy config |
| BR-EL-019 | Authority resolution & optional Establishment step | Domain/Services | `domain/rules.py::resolve_route` | Resolved by designation/unit |
| BR-EL-020 | Director self-sanction path | Domain/Services | `domain/rules.py`, `services/sanction.py` | Direct self-sanction |
| BR-EL-021 | RETIRED — Modify Pending Request | N/A | N/A | Replaced by BR-EL-034 |
| BR-EL-022 | Immediate withdrawal of pending request before final approval | Services | `services/withdraw.py::withdraw_request` | Terminal immediate withdrawal |
| BR-EL-023 | Cancellation of approved leave before start | Services | `services/cancel.py::cancel_request` | Reverses balance on approval |
| BR-EL-024 | Fresh application after cancellation | Domain | `services/apply.py` | No in-place resurrect/edit |
| BR-EL-025 | Extension of ongoing EL/COL/VL | Services | `services/extend.py::extend_request` | Incremental balance deduction |
| BR-EL-026 | RETIRED IDENTIFIER | N/A | N/A | Retired |
| BR-EL-027 | Resumption applicability (EL, COL, VL) & review authority | Services | `services/resumption.py::submit_resumption` | Sanctioning authority reviews |
| BR-EL-028 | Resumption outcome: normal, early, or late | Services | `services/resumption.py::verify_resumption` | Balance adjusted on early/late |
| BR-EL-029 | Offline-sanctioned leave synchronization | Services | `services/offline.py::record_offline` | Single-actor ledger sync |
| BR-EL-030 | Current configured policy and hierarchy | Selectors | `selectors/policy.py::get_active_policy` | Currently effective policy |
| BR-EL-031 | Effective published holiday/RH calendar | Selectors | `selectors/calendars.py::get_active_calendar` | Current published calendar |
| BR-EL-032 | SLA reminder on still-pending task | Services/Tasks | `services/sla.py::process_sla_reminders` | Logged and stamped |
| BR-EL-033 | SLA escalation on still-pending task | Services/Tasks | `services/sla.py::process_sla_escalations` | Escalates to higher authority |
| BR-EL-034 | No post-submission modification in place | Domain/Services | `domain/rules.py`, `services/apply.py` | In-place edits blocked |
| BR-EL-035 | Actionable task assignment notification | Services | `services/*.py` (transition events) | Emitted on state movement |
| BR-EL-036 | Role-based authorization | API/Services | `api/views.py`, `fusion_auth/permissions.py` | Two-gate RBAC on endpoints |
| BR-EL-037 | Administrative maintenance is not sanctioning | Services | `services/offline.py`, `services/policy.py` | Sync without workflow |
| BR-EL-038 | Configurable SLA thresholds | Models/Services | `models/sla.py`, `services/sla.py` | Admin-configurable thresholds |

---

## Step 3.2 (b) — Domain Model

### Entities & Aggregates

1. **LeaveRequest** (`leave_request`)
   - `id`: BigAutoField
   - `user_id`: IntegerField (db_index=True)
   - `category`: CharField (CL, RH, SCL, EL, COL, VL)
   - `state`: CharField (State Machine status)
   - `starts_on`: DateField
   - `ends_on`: DateField
   - `half`: CharField (none, first_half, second_half)
   - `reason`: TextField
   - `evidence_reference`: CharField (blank=True)
   - `requested_days`: DecimalField(max_digits=5, decimal_places=2)
   - `actual_days`: DecimalField(max_digits=5, decimal_places=2, null=True)
   - `station_leave`: BooleanField(default=False)
   - `station_destination`: CharField(blank=True)
   - `substitute_user_id`: IntegerField(null=True)
   - `extension_to`: IntegerField(null=True, ForeignKey self)
   - `unit_head_recommended`: NullBooleanField()
   - `sanctioning_designation`: CharField(blank=True)
   - `resumed_on`: DateField(null=True)
   - `decided_at`: DateTimeField(null=True)
   - `created_at`, `updated_at`: DateTimeField

2. **LeaveTransition** (`leave_transition`)
   - `request`: ForeignKey(LeaveRequest, on_delete=CASCADE, related_name="transitions")
   - `from_state`: CharField
   - `to_state`: CharField
   - `event`: CharField
   - `actor_role`: CharField
   - `actor_user_id`: IntegerField
   - `remark`: TextField(blank=True)
   - `workflow_ref`: CharField(blank=True)
   - `created_at`: DateTimeField(auto_now_add=True)

3. **LedgerEntry** (`leave_ledger_entry`)
   - Append-only balance accounting.
   - `user_id`: IntegerField(db_index=True)
   - `year`: IntegerField(db_index=True)
   - `category`: CharField(max_length=8)
   - `days`: DecimalField(max_digits=5, decimal_places=2) -- negative for consumption, positive for credit/reversal
   - `reason`: CharField(annual_credit, consumption, cancellation_reversal, resumption_adjustment, vl_to_el_conversion, lapse)
   - `request_id`: IntegerField(null=True)
   - `note`: CharField(blank=True)
   - `created_at`: DateTimeField(auto_now_add=True)

4. **Policy & Configuration**
   - `Policy`: `version`, `effective_from`, `effective_to`, `published`, `vl_to_el_ratio` (default 2.0), `vl_to_el_rounding`, `early_return_tail`, `max_backdate_days`
   - `CategoryRule`: `policy`, `category`, `annual_credit`, `carries_forward`, `carry_forward_cap`, `applies_to_faculty`, `requires_evidence`
   - `AuthorityRule`: `policy`, `category`, `unit`, `designation`, `applies_to_faculty`, `establishment_step`, `sanctioning_designation`, `self_sanction`, `specificity`
   - `SlaRule`: `policy`, `state`, `remind_after_hours`, `escalate_after_hours`, `escalate_to_designation`

5. **Calendars & Holidays**
   - `Calendar`: `year`, `version`, `published`
   - `Holiday`: `calendar`, `day`, `name`, `restricted` (BooleanField)
   - `VacationPeriod`: `calendar`, `name`, `starts_on`, `ends_on`

---

## Step 3.3 (c) — State Machine

Declarative transitions dictionary `TRANSITIONS`:
`((source_state, event, actor_role) -> target_state)`

Key States:
- `submitted_pending_substitute`
- `substitute_declined`
- `submitted_pending_review` (Unit Head)
- `pending_routing` (Establishment / DR Estt.)
- `pending_sanction` (Final Sanctioning Authority: Dean / Registrar / Director)
- `approved` (Terminal success)
- `rejected` (Terminal rejection)
- `withdrawn` (Terminal withdrawal)
- `cancellation_pending_review`
- `cancellation_pending_routing`
- `cancellation_pending_sanction`
- `cancelled`
- `extension_pending_substitute`
- `extension_substitute_declined`
- `extension_pending_review`
- `extension_pending_routing`
- `extension_pending_sanction`
- `resumption_pending`
- `closed`

---

## Step 3.4 (d) — Permission List

```python
MODULE = {
    "code": "leave",
    "label": "Leave",
    "icon": "CalendarBlank",
    "base_path": "/leave",
    "nav_section": "Leave",
    "sort_order": 20,
    "status": "active",
}

PERMISSIONS = [
    ("leave.request.create", "Apply for leave"),
    ("leave.request.view_self", "See your own leave"),
    ("leave.request.withdraw", "Withdraw your pending request"),
    ("leave.substitute.respond", "Accept or decline standing in for someone"),
    ("leave.request.review", "Review as unit head and record a recommendation"),
    ("leave.request.route", "Route a recommended request to the competent authority"),
    ("leave.request.sanction", "Take the final decision on a leave request"),
    ("leave.resumption.verify", "Verify a reported resumption of duty"),
    ("leave.balance.view", "See leave balances across employees"),
    ("leave.policy.manage", "Maintain leave policy and entitlement"),
    ("leave.calendar.manage", "Maintain the holiday and restricted-holiday calendar"),
    ("leave.offline.record", "Record leave sanctioned outside the system"),
]

SYSTEM_PERMISSIONS = [
    "leave.lifecycle.advance",
    "leave.sla.process",
    "leave.yearend.run",
]

SCOPE_PERMISSIONS = [
    "leave.request.view_self",
]
```

---

## Step 3.5 (e) — Endpoint List

All routes under `/api/v1/leave/`:
1. `GET /api/v1/leave/me/requests` — View own leave requests (`leave.request.view_self`)
2. `GET /api/v1/leave/me/balances` — View own leave balances (`leave.request.view_self`)
3. `GET /api/v1/leave/me/statement/{category}` — View own ledger statement (`leave.request.view_self`)
4. `POST /api/v1/leave/requests` — Submit new leave request (`leave.request.create`)
5. `GET /api/v1/leave/requests/{id}` — Get request details (`leave.request.view_self` / scoped queue)
6. `POST /api/v1/leave/requests/{id}/withdraw` — Withdraw request (`leave.request.withdraw`)
7. `POST /api/v1/leave/requests/{id}/cancel` — Request pre-start cancellation (`leave.request.create`)
8. `POST /api/v1/leave/requests/{id}/extend` — Request extension (`leave.request.create`)
9. `POST /api/v1/leave/requests/{id}/renominate` — Renominate substitute (`leave.request.create`)
10. `POST /api/v1/leave/requests/{id}/resumption` — Submit resumption (`leave.request.create`)
11. `GET /api/v1/leave/requests/{id}/trail` — Audit trail (`leave.request.view_self` / scoped)
12. `GET /api/v1/leave/nominations` — Standing-in invitations (`leave.substitute.respond`)
13. `POST /api/v1/leave/nominations/{id}/respond` — Accept/decline nomination (`leave.substitute.respond`)
14. `GET /api/v1/leave/review` & `POST /api/v1/leave/review/{id}` — Unit Head queue (`leave.request.review`)
15. `GET /api/v1/leave/routing` & `POST /api/v1/leave/routing/{id}` — Establishment routing queue (`leave.request.route`)
16. `GET /api/v1/leave/sanction` & `POST /api/v1/leave/sanction/{id}` — Final sanction queue (`leave.request.sanction`)
17. `GET /api/v1/leave/resumptions` & `POST /api/v1/leave/resumptions/{id}/verify` — Resumption queue (`leave.resumption.verify`)
18. `GET /api/v1/leave/balances` — Institute balances read (`leave.balance.view`)
19. `POST /api/v1/leave/admin/offline` — Offline synchronization (`leave.offline.record`)
20. Policy & Calendar CRUD endpoints behind `leave.policy.manage` and `leave.calendar.manage`.

---

## Step 3.6 (f) — Contracts

Exposed by `modules/leave/contracts.py`:
- `get_leave_balances(user_ids: Sequence[int]) -> dict[int, dict[str, Decimal]]`
- `get_active_leaves(user_ids: Sequence[int], on_date: date) -> dict[int, LeaveDTO | None]`

---

## Step 3.7 (g) — Scheduled Work

- `leave_year_end`: Daily run / year-end cadence to process lapse of CL, RH, SCL, and VL->EL conversion.
- `leave_sla`: Hourly run to check pending task SLAs, emit reminders, and trigger escalations.

---

## Step 3.8 (h) — Open Questions & Resolved Scope Boundaries

1. Retired IDs: BR-EL-021 (Modify Pending Request) replaced by BR-EL-034 (Withdrawal + Fresh Application).
2. SCL Admissibility: Encoded as authority-admissible check without separate rigid rules as specified in BR-EL-004.
3. Offline Sanctioning: Synchronizes append-only ledger directly without triggering fresh approval workflow as per BR-EL-029 and BR-EL-037.
