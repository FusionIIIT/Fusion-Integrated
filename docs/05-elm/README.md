# Employee Leave Management (ELM)

Module `modules/elm`, API under `/api/v1/elm/`. Implements the RS1 requirements,
use cases, business rules and workflows (SRS-EL-001..107, EL-UC-001..016,
BR-EL-001..033, WF-EL-01..08, SF-EL-001..002).

## Structure

| Layer | Files |
|---|---|
| Data | `models.py`, `migrations/` |
| Rules | `services/validation.py` (counting, overlap, balance), `services/policy.py` (versioned policy and calendar), `services/routing.py` (approver resolution) |
| Workflow | `services/workflow.py` (pure state machine), `services/applications.py` (apply, substitute, review, sanction, withdraw), `services/lifecycle.py` (modify, cancel, extend, resume) |
| Ledger | `services/accounts.py` (every balance change is a `LeaveTransaction` row) |
| Jobs | `services/scheduled.py`, `management/commands/elm_year_end.py`, `elm_sla.py`, `services/offline.py` |
| API | `api/serializers.py`, `api/views.py`, `api/urls.py` |

## Authorization

Permissions in `registry.py` only open the module. Who may act on a given request is
decided by holding the open workflow task, so a Unit Head cannot decide a request that
was never routed to them. Every `faculty` and `staff` member receives the employee
permissions through the basic roles; `Leave Administrator` is an ELM-defined role that
holds the employee and administration permissions.

## Assumptions

The specifications leave these open. Each is a deliberate, reversible choice.

1. **Approver lookup.** IAM has no "unit head of X" lookup, so ELM keeps its own
   published `HierarchyRule` table (BR-EL-019), maintained through
   `POST /admin/hierarchy`.
2. **Director self-sanction (BR-EL-020).** The rule is not defined. The Director is the
   person named by a published `director` rule, and decides their own request through
   a task assigned to themselves.
3. **Weekends.** Saturday and Sunday. CL, SCL and RH skip weekends and closed holidays;
   EL, COL and VL count every calendar day (BR-EL-011).
4. **Half-day CL** applies only to a single date and costs 0.5 day. A first half and a
   second half on the same date do not overlap (BR-EL-012).
5. **Year boundary.** A leave is charged entirely to the year it starts in.
6. **Modification (SRS-EL-058).** A modified request restarts at the substitute gate or
   the first approval gate; a request needing a substitute must name one again.
7. **Resumption (UC-011).** The Unit Head verifies. The date given is the first day
   back at work; days from that date to the approved end are restored, and only after
   verification (SRS-EL-086).
8. **Escalation target (BR-EL-033).** The final authority, or the Director rule when the
   task already sits with the final authority. Default thresholds are 48 and 96
   hours, overridable with `SLA_REMINDER_HOURS` and `SLA_ESCALATION_HOURS` in the
   policy parameters.
9. **Year-end.** Processes every account for the year and can be re-run safely.
   Converted EL (2 VL : 1 EL, fractions kept) and carried EL and COL are posted into
   next year's account. VL never carries.
10. **Future-dated policy (SRS-EL-091).** Publishing a policy with a future
    `effective_from` leaves the current one in force until that date.
11. **Substitute required** is a flag on the request, set by the applicant.
12. **Roles.** Approvers need no extra role: authority comes from holding the workflow
    task, and the hierarchy table decides who that is.

## Not implemented

- Notifications (SRS-EL-054, 061, 104, 105). SLA actions and decisions are recorded
  (`SlaLog`, `Decision`) but no message is sent, because there is no notification
  service to call.
- Attendance synchronization (SRS-EL-084). No attendance module exists.
- PDF rendering of the printable application (SRS-EL-088). The endpoint returns the
  data for the client to render.

## Running

    python manage.py elm_sla                    # hourly
    python manage.py elm_year_end --year 2026   # once, at year end
    python -m pytest modules/elm