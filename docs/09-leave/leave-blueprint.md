---
owner: leave-lead
status: draft
last-reviewed: 2026-10-11
---

# Employee Leave Management — blueprint

The ELM module (`modules/leave`, module code `leave`, URL `/api/v1/leave/`) built
from the synchronized specification set in `elm_srs/`:

| Document | Version |
|---|---|
| Problem Statement | v1.4 FINAL |
| Functional Requirement Specification (CFR/AFR) | v1.5 FINAL |
| Use Case Specifications | v1.4 FINAL |
| Business Rule Specifications | v1.4 FINAL |
| Workflow Specifications | v1.6 FINAL |
| Traceability Matrix | v1.5 FINAL |

Environment: `module-only` — `Fusion_System_Administrator` and `Fusion-Integrated`,
`fusionlab` restored from `fusion-dev.dump`. There is no `Fusion-client` checkout,
so the portal sidebar entry is handed over in §5, not added.

## 0. Inventory (Phase 0)

| Artefact | Live | Retired by the spec |
|---|---|---|
| Business rules | **36** — BR-EL-001…038 | 2 — BR-EL-021 (behaviour *reversed*, replacement BR-EL-034), BR-EL-026 (no behaviour) |
| Use cases | **20** — 18 actor-triggered, 2 event-triggered (EL-UC-020, 021) | 1 — EL-UC-006 Modify Pending Request (replaced by EL-UC-007 + EL-UC-001, BR-EL-034, CFR-EL-017/018) |
| Workflows | 17 basis (BW-EL-01…17), 4 composite (CW-EL-01…04), 1 cross-cutting pattern (XTP-EL-01) | legacy WF-EL-01…08 |
| Requirements | 32 CFRs, 128 AFRs | — |

Neither retirement leaves behaviour behind: BR-EL-021 *permitted* modification and
was reversed, so the live behaviour is the prohibition (BR-EL-034).

**Contradictions between documents.** One, and it is stale numbering rather than
semantics: the Traceability Matrix v1.5 counts **19** basis workflows and maps the
legacy workflows to `BW-EL-01–08 / 09–12 / 13–16 / 17–19`. Workflow Specifications
v1.6 (the later document, which states it corrects exactly this) has **17**. This
module follows v1.6 and cites only BW-EL-01…17. The matrix's mapping columns are
otherwise populated and agree with the rule-by-rule reading in §1.

**Actors** (Problem Statement App. A, UC registry, every STT): Employee (ACT-01),
Substitute (ACT-02), Unit Head (ACT-03), Deputy Registrar (Estt.) / Establishment
(ACT-04), Dean (ACT-05), Registrar (ACT-06), Director (ACT-07), Leave Administrator
(ACT-08), "authorized administrative role" (EL-UC-014/015/017/018). Not actors:
EXT-01 Academic Calendar, EVT-01 year-end boundary, EVT-02 SLA threshold.

## 1. Traceability (a)

`domain/` decides, `services/` enforces at the choke point, `selectors/` decides
who sees what. `api/` enforces nothing but the two gates.

### Business rules

| Id | What it requires | Layer | Enforcement point | Notes |
|---|---|---|---|---|
| BR-EL-001 | Only CL/RH/SCL/EL/COL/VL; category applicable to the applicant | domain | `domain/categories.py::applicable`, `domain/validation.py` | VL is faculty-only; EL is availed by anyone holding EL (BR-EL-008) |
| BR-EL-002 | CL 8/yr, lapses | domain | `domain/entitlement.py`, `domain/yearend.py` | entitlement number is policy (BR-EL-030) |
| BR-EL-003 | RH 2/yr; date must be an RH in the effective published calendar; lapses | domain | `domain/validation.py::_rh_dates`, `domain/yearend.py` | |
| BR-EL-004 | SCL ≤15/calendar year; purpose judged by the authority; lapses | domain | `domain/entitlement.py`, `domain/yearend.py` | no encoded admissibility test, by the rule |
| BR-EL-005 | Non-faculty EL 30/yr, carries forward | domain | `domain/entitlement.py`, `domain/yearend.py` | |
| BR-EL-006 | Faculty VL 60; only inside an Academic Calendar vacation period | domain | `domain/validation.py::_vacation` | vacation periods: see §8 Q3 |
| BR-EL-007 | Year-end VL→EL at 2:1, fractions kept, no VL carry | domain | `domain/yearend.py::outcome` | |
| BR-EL-008 | Converted EL is ordinary, usable, carried EL | domain | `domain/yearend.py`, `domain/categories.py` | |
| BR-EL-009 | COL 20/yr; medical evidence where applicable; carries forward | domain | `domain/validation.py::_evidence`, `domain/yearend.py` | threshold is policy, §8 Q4 |
| BR-EL-010 | Half-day CL (first/second), 0.5 day | domain | `domain/counting.py` | |
| BR-EL-011 | EL/COL/VL count every calendar day; CL/SCL/RH skip weekends and closed holidays | domain | `domain/counting.py::chargeable_days` | weekend days are policy |
| BR-EL-012 | No overlap with own pending/approved leave; different CL halves do not overlap | domain + DB lock | `domain/overlap.py`, `services/applications.py` under the account lock | |
| BR-EL-013 | Station Leave inside the application | domain | `domain/validation.py::_station` | no separate lifecycle exists to call |
| BR-EL-014 | One substitute: another employee, not the applicant, no overlapping leave | domain + service | `domain/validation.py::substitute_problems`, `services/substitutes.py` | |
| BR-EL-015 | Routing waits for acceptance; decline → applicant action | domain | `domain/state_machine.py` (no edge leaves `awaiting_substitute` except accept/decline/withdraw) | |
| BR-EL-016 | CL/RH: Unit Head is final | domain | `domain/state_machine.py` (`uh_final` guard) | |
| BR-EL-017 | Higher-sanction: Unit Head records (Not) Recommended, never final | domain | `domain/state_machine.py` (`recommend` edges) | |
| BR-EL-018 | Higher-sanction proceeds through configured hierarchy | domain + service | `domain/routing.py::resolve_route`, `services/workflow.py` | |
| BR-EL-019 | Route resolved from applicant/unit/designation/category/config; Estt step only where configured | domain | `domain/routing.py` | |
| BR-EL-020 | Director self-sanction replaces the route | domain + service | `domain/state_machine.py` (`director` guard), `services/workflow.py::_authorise` | the single permitted self-decision |
| BR-EL-022 | Withdraw any pending request immediately; tasks closed; no later decision; concerned roles told | service | `services/workflow.py::withdraw` | |
| BR-EL-023 | Cancel approved leave only before start; same hierarchy; Cancelled + balance restored; reject leaves it | domain + service | `domain/state_machine.py`, `services/workflow.py::_effects` | |
| BR-EL-024 | Revised leave after cancellation is a fresh application | service | there is no edit path; `services/applications.py` | |
| BR-EL-025 | Extension only for ongoing EL/COL/VL; full validation; approval posts the increment only | domain + service | `domain/validation.py::extension_problems`, `services/workflow.py::_effects` | |
| BR-EL-027 | Resumption reviewed for EL/COL/VL by the applicable Sanctioning Authority | domain + service | `domain/resumption.py`, `services/resumptions.py` | |
| BR-EL-028 | Normal: no change; early/late: actual period recorded and balance adjusted after review | domain + service | `domain/resumption.py::classify`, `services/resumptions.py::review` | §8 Q6 on the date reading |
| BR-EL-029 | Offline sanctioned leave: evidence, consistency, balance/history, no second workflow | service | `services/records.py::record_offline` | |
| BR-EL-030 | Current configured policy/hierarchy, no draft/publish lifecycle | model + service | `models/policy.py`, `models/hierarchy.py` — the newest revision is current | see §2 on revisions |
| BR-EL-031 | Date/RH validation uses the effective published calendar until replaced | model + service | `models/calendar.py` (one published per year, DB constraint), `services/calendar.py::publish` | |
| BR-EL-032 | Remind only a still-pending task, and log it | service | `services/sla.py::process` | |
| BR-EL-033 | Escalate only a still-pending task: notify, or reassign, and log it | service | `services/sla.py::process` | reassign is XTP-EL-01 |
| BR-EL-034 | No in-place modification of a pending request | api + service | no update endpoint exists; serializers are read-only for requests | |
| BR-EL-035 | Notify the assignee of every actionable task | service | `services/workflow.py::_open_task` → `services/notifications.py` | |
| BR-EL-036 | Role-based authorization | api + service | `HasModuleGrant("leave")` + `HasPermission` on every view, `services/authz.py` | |
| BR-EL-037 | Administrative maintenance is never a sanction | service | `services/records.py` writes ledger adjustments only; no status edge | |
| BR-EL-038 | Configurable SLA thresholds govern EL-UC-021 | model + service | `models/sla.py`, `services/sla.py` | |

### Use cases

| Id | What it requires | Layer | Enforcement point |
|---|---|---|---|
| EL-UC-001 | Apply | service | `services/applications.py::submit` |
| EL-UC-002 | Substitute accepts/declines | service | `services/substitutes.py::respond` → `workflow.advance` |
| EL-UC-003 | Unit Head review | service | `services/workflow.py::decide` (step `unit_head`) |
| EL-UC-004 | Establishment verify and route | service | `services/workflow.py::decide` (step `establishment`) |
| EL-UC-005 | Final sanction | service | `services/workflow.py::decide` (steps `sanction`, `director`) |
| EL-UC-007 | Withdraw pending | service | `services/workflow.py::withdraw` |
| EL-UC-008 | Request cancellation | service | `services/applications.py::request_cancellation` |
| EL-UC-009 | Request extension | service | `services/applications.py::request_extension` |
| EL-UC-010 | Submit resumption | service | `services/resumptions.py::submit` |
| EL-UC-011 | Review resumption | service | `services/resumptions.py::review` |
| EL-UC-012 | Balances and history | selector | `selectors/balances.py`, `selectors/scoping.py::own_requests` |
| EL-UC-013 | Printable/exportable application | service | `services/documents.py::render` |
| EL-UC-014 | Policy and hierarchy configuration | service | `services/policy.py`, `services/hierarchy.py` |
| EL-UC-015 | Holiday/RH calendar | service | `services/calendar.py` |
| EL-UC-016 | Offline sanctioned leave | service | `services/records.py::record_offline` |
| EL-UC-017 | Record maintenance | service | `services/records.py::adjust` |
| EL-UC-018 | SLA thresholds | service | `services/sla.py::configure` |
| EL-UC-019 | Replacement substitute | service | `services/substitutes.py::renominate` |
| EL-UC-020 | Year-end processing | service + beat | `services/yearend.py::run`, `tasks.py::year_boundary` |
| EL-UC-021 | SLA threshold event | service + beat | `services/sla.py::process`, `tasks.py::process_sla` |

## 2. Domain model (b)

Every person is a plain `user_id`. No foreign key leaves the module.

| Table | Purpose | Database-enforced invariants |
|---|---|---|
| `leave_policy_revision`, `leave_category_rule` | policy parameters; newest revision is current | one rule per (revision, category); entitlement ≥ 0 |
| `leave_hierarchy_revision`, `leave_org_unit`, `leave_sanction_route` | Unit Head per unit, higher-sanction routes | one unit per (revision, department) |
| `leave_holiday_calendar`, `leave_holiday` | per-year calendar, draft → published → superseded | **one published calendar per year** (partial unique); one entry per date |
| `leave_vacation_period` | Academic Calendar vacation periods (EXT-01) | end ≥ start |
| `leave_sla_revision`, `leave_sla_rule` | reminder/escalation thresholds per step | escalation > reminder > 0 |
| `leave_request` | new leave, cancellation, extension — one table, `kind` | end ≥ start; half-day only on a single day; **one pending cancellation and one pending extension per leave** (partial unique) |
| `leave_substitution` | one nomination, its answer | **one pending nomination per request** (partial unique) |
| `leave_task` | the actionable work item behind every pending state | **one open task per request** (partial unique) |
| `leave_request_event` | append-only audit of every movement | — |
| `leave_resumption` | resumption declaration and review | **one per leave** (unique) |
| `leave_account` | one row per employee, the lock every balance write takes | unique `user_id` |
| `leave_ledger_entry` | append-only ledger; balance = sum | **unique idempotency key**; delta ≠ 0 |
| `leave_year_end_run` | year-end evidence and exceptions | one per year |
| `leave_outbox`, `leave_sla_event` | notifications; SLA log | unique dedupe key |

**Policy is revisioned, not edited.** Step 2.8 of the authoring rules wants
administrator configuration effective-dated and never edited; BR-EL-030 forbids a
draft/publish/effective-version lifecycle. Both hold at once: every save is a new
revision row that is current the moment it commits — no draft, no publish, no
future date — and the old rows remain as history. The calendar is the one thing
the spec *does* give a publish step (BR-EL-031), and only it has one.

**Balances are a ledger.** Year-scoped: the annual credit, every approval debit,
cancellation and resumption reversals, administrative adjustments, and year-end
lapse / conversion / carry-forward entries. A year sums to zero once closed; the
carried amount reappears as the next year's opening entry. Every write takes the
employee's `leave_account` row `FOR UPDATE` first, and every entry carries an
idempotency key, so a retried task cannot credit twice.

**A leave is charged to the year it starts in.**

## 3. State machine (c)

`domain/state_machine.py` holds one table of `(kind, from, event, actor, guards) →
to`, generated from the STTs of CW-EL-01, 02 and 03. A move is looked up, never
computed, and a combination that is not in the table cannot be made. Guards are
facts known before the move: `needs_substitute`, `director`, `uh_final` (CL/RH),
`establishment` (an Establishment step is configured for this route).

CW-EL-04 is a separate two-step machine in `domain/resumption.py`, because a
resumption is a different record from the leave it closes out.

The diagrams live in [leave-state-machine.md](leave-state-machine.md).

## 4. Permissions (d)

```python
MODULE = {"code": "leave", "label": "Leave", "icon": "CalendarCheck",
          "base_path": "/leave", "nav_section": "Leave", "sort_order": 20,
          "status": "active"}

_EMPLOYEE = ["leave.request.create", "leave.request.view", "leave.request.revoke",
             "leave.request.export", "leave.balance.view", "leave.substitution.review"]
_UNIT_HEAD = ["leave.request.review"]
_ESTABLISHMENT = ["leave.request.review", "leave.request.assign",
                  "leave.request.approve", "leave.resumption.review"]
_AUTHORITY = ["leave.request.review", "leave.request.approve",
              "leave.resumption.review"]
_ADMIN = ["leave.policy.update", "leave.hierarchy.update", "leave.calendar.update",
          "leave.calendar.publish", "leave.sla.update", "leave.record.view",
          "leave.record.import", "leave.record.update"]
SYSTEM_PERMISSIONS = ["leave.ledger.manage", "leave.task.assign"]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE, "staff": _EMPLOYEE,
    "HOD (CSE)": _UNIT_HEAD, "HOD (ECE)": _UNIT_HEAD, "HOD (ME)": _UNIT_HEAD,
    "HOD (NS)": _UNIT_HEAD, "HOD (Design)": _UNIT_HEAD, "HOD (Liberal Arts)": _UNIT_HEAD,
    "SectionHead_HR": _UNIT_HEAD, "SectionHead_IWD": _UNIT_HEAD,
    "SectionHead_PS": _UNIT_HEAD, "SectionHead_RSPC": _UNIT_HEAD,
    "Deputy Registrar": _ESTABLISHMENT,
    "Registrar": _AUTHORITY, "Director": _AUTHORITY, "Dean_s": _AUTHORITY,
    "Dean Academic": _AUTHORITY, "Dean (P&D)": _AUTHORITY, "Dean (R&D)": _AUTHORITY,
    "dean_rspc": _AUTHORITY,
    "hradmin": _ADMIN,
}
```

Every designation is spelled exactly as `globals_designation` holds it. Mapping of
spec actors (approved 2026-10-11):

| Spec actor | Designation(s) | Citation |
|---|---|---|
| Employee | `faculty`, `staff` (held by definition) | ACT-01, EL-UC-001 |
| Substitute | any employee, by nomination — a *person*, not a role | ACT-02, EL-UC-002 |
| Unit Head | per org unit, configured: `HOD (…)`, `SectionHead_…`, or an authority | ACT-03, EL-UC-003, BR-EL-016/017 |
| Deputy Registrar (Estt.) | `Deputy Registrar` | ACT-04, EL-UC-004 |
| Dean / Registrar / Director | `Dean_s`, `Dean Academic`, `Dean (P&D)`, `Dean (R&D)`, `dean_rspc`, `Registrar`, `Director` | ACT-05–07, EL-UC-005 |
| Leave Administrator / administrative role | `hradmin` | ACT-08, EL-UC-014–018 |

**The acting role decides the queue.** IAM permissions are the union of a
person's designations, so a task is matched against `active_role`: an HOD acting
as `faculty` sees no HOD queue. Permissions decide the verb; the task decides the
row.

Hierarchy configuration is validated against these grants: a unit's head must hold
`leave.request.review`, an Establishment step `leave.request.assign`, a sanction
step `leave.request.approve`. A route cannot name a designation that would see a
task and be unable to act on it.

## 5. Endpoints (e)

All under `/api/v1/leave/`, all behind `HasModuleGrant("leave")` then
`HasPermission(...)`.

| Method | Path | Permission | Returns | Rules |
|---|---|---|---|---|
| GET | `overview` | `leave.balance.view` | balances, applicable categories, my policy | UC-012, BR-001–011 |
| GET | `ledger` | `leave.balance.view` | own ledger entries | UC-012 |
| GET | `calendar` | `leave.request.create` | effective holidays + vacation periods | BR-003, BR-031 |
| GET | `employees` | `leave.request.create` | employee search for a substitute | BR-014 |
| GET/POST | `requests` | view / create | own requests / apply | UC-001, UC-012 |
| GET | `requests/<id>` | view or review | one request, scoped | UC-012 |
| GET | `requests/<id>/document` | `leave.request.export` | printable HTML | UC-013 |
| POST | `requests/<id>/withdraw` | `leave.request.revoke` | | UC-007, BR-022 |
| POST | `requests/<id>/cancellation` | `leave.request.create` | | UC-008, BR-023 |
| POST | `requests/<id>/extension` | `leave.request.create` | | UC-009, BR-025 |
| POST | `requests/<id>/substitute` | `leave.request.create` | | UC-019, BR-014/015 |
| POST | `requests/<id>/resumption` | `leave.request.create` | | UC-010, BR-027 |
| GET | `substitutions` | `leave.substitution.review` | requests awaiting my answer | UC-002 |
| POST | `substitutions/<id>/respond` | `leave.substitution.review` | | UC-002, BR-015 |
| GET | `queue` | `leave.request.review` / `leave.resumption.review` | open tasks for my acting role | UC-003–005, UC-011 |
| POST | `tasks/<id>/decide` | per step | | UC-003–005, UC-011 |
| GET/POST | `admin/policy` | `leave.policy.update` | | UC-014, BR-030 |
| GET/POST | `admin/hierarchy` | `leave.hierarchy.update` | | UC-014, BR-019 |
| GET/POST | `admin/calendars` | `leave.calendar.update` | | UC-015 |
| PUT | `admin/calendars/<id>` | `leave.calendar.update` | | UC-015 |
| POST | `admin/calendars/<id>/publish` | `leave.calendar.publish` | | UC-015, BR-031 |
| GET/POST/DELETE | `admin/vacations[/<id>]` | `leave.calendar.update` | | BR-006 |
| GET/POST | `admin/sla` | `leave.sla.update` | | UC-018, BR-038 |
| GET | `admin/records` | `leave.record.view` | an employee's requests and ledger | UC-017 |
| POST | `admin/records/offline` | `leave.record.import` | | UC-016, BR-029 |
| POST | `admin/records/adjustments` | `leave.record.update` | | UC-017, BR-037 |
| GET | `admin/year-end` | `leave.record.view` | year-end runs and exceptions | UC-020 |
| GET | `admin/readiness` | `leave.policy.update` | unmet prerequisites | — |

**`Fusion-client` sidebar entry** — for whoever holds that repository; the one
piece this environment cannot finish. Append to `INTEGRATED_MODULES` in
`src/ui/nav/navigation.js`:

```js
{ id: "leave", label: "Leave", icon: "CalendarCheck", to: "/leave", section: "Leave" },
```

## 6. Contracts (f)

`modules/leave/contracts.py` exposes one plural getter, for attendance or HR
consumers: `get_leave_days(user_ids, start, end) -> {user_id: [LeaveDayDTO]}` —
approved leave as it was actually taken, after cancellation and resumption.

Needed from elsewhere:

| Need | From | Status |
|---|---|---|
| name, kind, department of a person | `directory.get_users` | exists |
| employee search for substitute nomination | `directory.search` | exists |
| **holders of a designation** (notifying a role's task) | **new** `directory.get_designation_holders(designations)` → `IamClient.get_designation_holders` → **new IAM endpoint** `GET /api/iam/v1/directory/holders?designations=…` | built in this change, both repositories |
| applicant's own designations | the session (`principal.roles`) | exists |

## 7. Scheduled work (g)

| Beat entry | Cadence | What breaks if it does not run |
|---|---|---|
| `leave.deliver-notifications` | 60 s | nobody is told a task is waiting; decisions arrive by word of mouth |
| `leave.process-sla` | 15 min | EL-UC-021 never fires: a forgotten request waits forever |
| `leave.year-boundary` | daily 00:30 | no annual credit, no lapse, no VL→EL conversion: January balances are wrong for everyone |

## 8. Open questions (h)

Decisions taken to keep building, each reversible by configuration or a small
change. Every one is the spec not saying, not a contradiction.

1. **Who decides that responsibility coverage is "required"?** Policy, per
   category: `required`, `optional` (the applicant decides), or `none`. Seeded
   `optional` everywhere.
2. **A Unit Head's own leave.** The unit's `head_leave_designation` reviews it; if
   none is configured the application is refused with a message. No one may decide
   their own request except the Director (BR-EL-020).
3. **EXT-01 has no service in Fusion yet.** Vacation periods are kept in
   `leave_vacation_period`, entered by the Leave Administrator from the published
   Academic Calendar. Replace the selector when the academic module can answer.
4. **COL evidence "where applicable".** Policy: `evidence_min_days`; at or above it
   an evidence reference is required. Seeded at 3.
5. **Back-dating.** Policy `max_backdate_days`, seeded 0: past leave is the offline
   path (EL-UC-016), which needs a sanction reference.
6. **"Resumes on the approved end date".** Read as returning on the first day after
   the last approved leave day; earlier is early, later is late.
7. **Late return beyond balance.** The review is refused with a message rather
   than driving a balance negative; the excess must be regularised first.
8. **Cancellation decided after the leave began.** Refused at decision time: a
   cancellation approved after the leave was taken would restore days that were
   used.
9. **Director's cancellation and extension.** CW-EL-02/03 draw no Director path;
   BR-EL-020 is applied to them too, since it speaks of "the Director's own leave".
10. **Leave spanning the year boundary** is charged wholly to its start year.
11. **Year-end with requests in flight.** That employee's account is reported as an
    exception and left untouched (EL-UC-020 alternative flow); a re-run after the
    decision finishes it.
12. **Units without a head.** Most staff sections have no held head designation in
    `fusionlab`. Their employees cannot apply until the Leave Administrator maps
    the unit; the readiness check lists every unmapped unit that has employees.
13. **Seeded routes** — faculty: Deputy Registrar → Director; staff: Deputy
    Registrar → Registrar — are a starting point for the institute to correct, not
    a statement of its policy.
