---
purpose: >
  The ELM (Employee Leave Management) blueprint: traceability, domain model, state machine,
  permissions, endpoints, contracts, scheduled work and open questions.
---

# ELM — blueprint

| Blank | Value |
|---|---|
| `MODULE_NAME` | Employee Leave Management |
| `SPEC_FOLDER_PATH` | `RS1_Phase1_Student_Distribution/Reference_Documents/` (00–05) |
| `ID_PREFIX` | `SRS-EL-`, `BR-EL-`, `EL-UC-`, `SF-EL-`, `WF-EL-` |
| `module_code` | `elm` |
| `ENVIRONMENT` | `module-only` |

## Phase 0 inventory

| Artefact | Count | Notes |
|---|---|---|
| Requirements `SRS-EL-001..107` | 107 | none retired |
| Business rules `BR-EL-001..033` | 32 | **`BR-EL-026` is absent** from the index and body; not cited anywhere |
| Use cases `EL-UC-001..016` | 16 | none retired |
| Scheduled functions `SF-EL-001..002` | 2 | year-end, SLA |
| Workflows `WF-EL-01..08` | 8 | |

Actors named (Step 1.4.6): Employee, Substitute / Responsibility Holder, Unit Head,
Deputy Registrar (Estt.) / Establishment role, Dean, Registrar, Director, Leave
Administrator, System Scheduler (domain context §3; EL-UC-001..016; WF-EL-01..08).

## 3.1 (a) Traceability

| Id | Requires | Layer | Enforcement point |
|---|---|---|---|
| BR-EL-001 | category eligibility under effective policy | domain | `domain/policy.py::check_eligible` via `services/requests.py::_validate` |
| BR-EL-002 | 8 CL/yr, lapses | domain + services | `domain/policy.py` defaults, `services/ledger.py::ensure_annual_credits`, `services/year_end.py` |
| BR-EL-003 | 2 RH/yr, must match published RH, lapses | domain | `domain/counting.py::validate_rh_dates`, `services/year_end.py` |
| BR-EL-004 | 15 SCL/yr, authority decides admissibility, lapses | domain + services | policy defaults; final decision in `services/workflow.py` |
| BR-EL-005 | 30 EL/yr for non-faculty, carries forward | domain + services | `domain/policy.py::annual_credit_for`, `services/year_end.py` |
| BR-EL-006 | 60 VL for faculty, only inside published vacation | domain | `domain/counting.py::validate_vacation` |
| BR-EL-007 | VL→EL 2:1 fractional at year end | domain | `domain/year_end.py::vl_to_el` |
| BR-EL-008 | converted EL credited, carries forward | services | `services/year_end.py` |
| BR-EL-009 | 20 COL/yr, carries forward, medical evidence | domain + services | policy defaults, `_validate` evidence check |
| BR-EL-010 | half-day CL = 0.5 | domain | `domain/counting.py::chargeable_days` |
| BR-EL-011 | EL/COL/VL count intervening weekends/holidays | domain | `domain/counting.py::chargeable_days` |
| BR-EL-012 | no overlap; different CL halves do not overlap | domain + services | `domain/overlap.py`, `services/requests.py::_validate` (row lock on applicant) |
| BR-EL-013 | Station Leave inside the same application | models | `LeaveRequest.station_leave*` fields |
| BR-EL-014 | substitute is another employee with no overlapping leave | services | `services/requests.py::_validate_substitute` |
| BR-EL-015 | no routing until substitute accepts | domain | `domain/state_machine.py` (only `substitute_accept` leaves `awaiting_substitute`) |
| BR-EL-016 | Unit Head final for CL/RH | domain | `domain/routing.py::resolve_route` |
| BR-EL-017 | Unit Head recommends for SCL/EL/COL/VL, never final | domain | `domain/routing.py`, `domain/state_machine.py` |
| BR-EL-018 | higher sanction through configured hierarchy | domain | `domain/routing.py::resolve_route` |
| BR-EL-019 | path from applicant, unit, role, category, hierarchy | domain | `domain/routing.py::resolve_route` |
| BR-EL-020 | Director self-sanction | domain | `domain/routing.py` (`director` step) |
| BR-EL-021 | modify only while pending; revalidate; supersede tasks | services | `services/requests.py::modify` |
| BR-EL-022 | immediate withdrawal; close tasks; inform | services | `services/requests.py::withdraw` |
| BR-EL-023 | cancel approved only before start, same hierarchy | services | `services/requests.py::request_cancellation` |
| BR-EL-024 | fresh application after cancellation | domain | no transition out of `cancelled` |
| BR-EL-025 | extension only for ongoing EL/COL/VL | services | `services/requests.py::apply_extension` |
| BR-EL-027 | resumption after EL/COL/VL, verified, closes | services | `services/resumption.py` |
| BR-EL-028 | early resumption restores unused only after verification | services | `services/resumption.py::verify` |
| BR-EL-029 | offline sanctioned leave is record sync, not approval | services | `services/offline.py::record` |
| BR-EL-030 | effective published policy/hierarchy | selectors | `selectors/config.py::effective_policy` |
| BR-EL-031 | effective published calendar | selectors | `selectors/config.py::effective_calendar` |
| BR-EL-032 | SLA reminder at threshold, not if no longer pending | services | `services/sla.py::process` |
| BR-EL-033 | SLA escalation, logged | services | `services/sla.py::process` |
| EL-UC-001..016 | see services column above | services | one service per use-case family |
| SF-EL-001 / SF-EL-002 | year-end / SLA | tasks | `tasks.py`, `schedule.py` |

Known gaps: SRS-EL-084 (attendance synchronisation) — there is no attendance module in this
platform; verified resumption records the actual period and closes the leave, the attendance
half is listed in (h).

## 3.2 (b) Domain model

- `PolicyVersion` — `params` (JSON, validated by `domain/policy.py`), `hierarchy` (JSON),
  `effective_from`, `status` draft|published. Published rows are never edited.
- `CalendarVersion` + `CalendarEntry` (kind closed_holiday | restricted_holiday | vacation,
  `start_date`, `end_date`). Same publish rule.
- `LeaveRequest` — `user_id`, `category`, `kind` leave|extension, `parent` (extension → leave),
  dates, `half` (CL), `days`, purpose, station-leave fields, `substitute_user_id`,
  `substitute_status`, `status`, `route` (JSON snapshot), `stage`, `current_role`,
  `recommendation`, `cancellation_stage`, `actual_return_date`, `policy_version`.
  `CheckConstraint end >= start`, `days > 0`.
- `LeaveTransition` — append-only audit (from, to, event, actor, note).
- `LedgerEntry` — append-only (`user_id`, `category`, `delta`, `entry_type`, `year`,
  `request`). Partial unique index: one `annual_credit` per (user, category, year), one
  `debit` / `reversal` / `restore` per request.
- `OfflineLeaveRecord` — evidence of offline sanction.
- `YearEndRun` — unique per year, with exceptions report.
- `Notification` — in-app notifications to a user or to a designation.
- `SlaAction` — unique per (request, stage, action) so a threshold fires once.

## 3.3 (c) State machine

Declared in `domain/state_machine.py` as `(state, event) → targets, actor`. States:
`awaiting_substitute`, `substitute_declined`, `awaiting_unit_head`, `awaiting_establishment`,
`awaiting_sanction`, `awaiting_director`, `approved`, `rejected`, `withdrawn`,
`cancellation_pending`, `cancelled`, `resumption_pending`, `closed`.

## 3.4 (d) Permissions

See `modules/elm/registry.py`. Roles map to designations from `globals_designation`:
Employee → `faculty`, `staff`; Unit Head → `HOD (CSE)`, `HOD (ECE)`, `HOD (ME)`,
`HOD (Design)`, `HOD (NS)`, `HOD (Liberal Arts)`, `SectionHead_PS`, `SectionHead_IWD`,
`SectionHead_RSPC`, `SectionHead_HR`; Establishment → `Deputy Registrar`; Sanctioning →
`Registrar`, `Director`; Leave Administrator → `Leave Administrator` (new designation,
provisioned with `assign_role`).

## 3.5 (e) Endpoints

All under `/api/v1/elm/`, gated by `HasModuleGrant("elm")` then a permission.

| Method | Path | Permission | Rules |
|---|---|---|---|
| GET/POST | `requests` | `elm.leave_request.view` / `.create` | EL-UC-001 |
| GET | `requests/<id>` | `elm.leave_request.view` (scoped) | EL-UC-012 |
| POST | `requests/<id>/modify` | `elm.leave_request.update` | EL-UC-006 |
| POST | `requests/<id>/withdraw` | `elm.leave_request.delete` | EL-UC-007 |
| POST | `requests/<id>/cancel` | `elm.leave_request.update` | EL-UC-008 |
| POST | `requests/<id>/extend` | `elm.leave_request.create` | EL-UC-009 |
| POST | `requests/<id>/resume` | `elm.leave_request.update` | EL-UC-010 |
| POST | `requests/<id>/substitute` | `elm.leave_request.update` | SRS-EL-041 |
| GET | `requests/<id>/print` | `elm.leave_request.view` | EL-UC-013 |
| GET | `substitutions` | `elm.substitution.review` | EL-UC-002 |
| POST | `substitutions/<id>/respond` | `elm.substitution.review` | EL-UC-002 |
| GET | `queue` | `elm.leave_request.review` / `.approve` | EL-UC-003..005 |
| POST | `queue/<id>/decide` | `elm.leave_request.review` / `.approve` | EL-UC-003..005, 008, 009 |
| GET | `resumptions` | `elm.resumption.review` | EL-UC-011 |
| POST | `resumptions/<id>/verify` | `elm.resumption.review` | EL-UC-011 |
| GET | `balances` | `elm.leave_balance.view` | EL-UC-012 |
| GET/POST | `admin/policies`, `admin/policies/<id>/publish` | `elm.policy.publish` | EL-UC-014 |
| GET/POST | `admin/calendars`, `admin/calendars/<id>/publish` | `elm.calendar.publish` | EL-UC-015 |
| GET/POST | `admin/offline` | `elm.offline_record.create` | EL-UC-016 |
| GET | `notifications` | module grant | SRS-EL-054 |

`Fusion-client` sidebar entry: `{ id: "elm", label: "Leave", icon: "CalendarCheck", to: "/elm", section: "Services" }`.

## 3.6 (f) Contracts

Exposes `get_on_leave(user_ids, on)`. Consumes `directory.get_users` (kind, department).

## 3.7 (g) Scheduled work

| Task | Cadence | If it does not run |
|---|---|---|
| `elm.year_end` | 1 Jan 00:30 | CL/RH/SCL never lapse, VL never converts, no new-year credit |
| `elm.sla` | hourly | no reminders or escalations |

## 3.8 (h) Open questions

1. Unit Head for staff sections with no head designation in `globals_designation`
   (General Administration, Computer Center, Academics, Directorate, …). Unmapped units are
   refused at submission with a message naming the unit.
2. Who reviews a Unit Head's own leave. The Unit Head step refuses self-review; no route
   is specified.
3. Which Dean (if any) sanctions which category. Not granted by default.
4. SLA reminder/escalation thresholds and escalation target — seeded empty, so SLA is off
   until the Leave Administrator publishes values.
5. SRS-EL-084 attendance synchronisation — no attendance module exists.
6. `BR-EL-026` is missing from the spec.

## Deployment order

```bash
manage.py migrate
manage.py seed_elm_policy        # before seed_modules, or ELM registers as "planned"
manage.py seed_modules
make permissions                 # then, in the IAM:
manage.py seed_iam_permissions --manifest <path>/registry/permissions.json
manage.py assign_role --user <stfNNNNN> --designation "Leave Administrator"
manage.py elm_readiness          # names every unmet prerequisite
```
