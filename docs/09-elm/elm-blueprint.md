---
purpose: >
  The blueprint for the Employee Leave Management (ELM) pilot module, written before
  the code as the new-module prompt requires. Rule numbers here are this pilot's
  own traceability numbers, because the official ELM spec folder is not present in
  this workspace — see "Open questions" at the bottom.
---

# ELM — Employee Leave Management: blueprint

`modules/elm` (module code `elm`, base path `/leave`) implements the employee leave
lifecycle on the same shape as `modules/placement`: a pure `domain/`, models split by
aggregate, all reads in `selectors/`, every write through one transactional choke
point in `services/`, transport-only `api/`, and a declarative state machine.

**Scope of this pilot.** An employee submits a leave request against a leave type and a
date range; an approver decides it; an approval debits an append-only balance ledger; a
cancellation reverses the debit. Leave types, holidays and entitlements are
administrator-configured, effective-dated, never edited in place.

## (a) Traceability — the pilot's own rules

| Rule | What it requires | Layer | Enforcement point |
|---|---|---|---|
| BR-01 | A request is always for a whole day or an allowed half day of a single day | domain | `domain/policy.py::count_days` |
| BR-02 | A request must cover at least one working day | domain | `domain/policy.py::validate_request` |
| BR-03 | Start and end must be ordered; the span is bounded | domain, DB | `policy.validate_request`, `CheckConstraint leave_application_dates_ordered` |
| BR-04 | Back-dated requests are allowed at most 7 days, for a record rather than a decision | services | `services/applications.py::submit_application` |
| BR-05 | A person's active requests may not overlap | services, DB | `applications._reject_overlap`, `leave_application_one_active_per_day` |
| BR-06 | Balances are an append-only ledger; a correction is a reversing entry | models, services | `models/balances.py`, `services/balances.py` |
| BR-07 | A request may not be approved beyond the available balance | services | `applications._debit` guard `balance_sufficient` |
| BR-08 | Nobody decides their own request, and it never enters their own queue | services, selectors | `applications._guard`, `selectors/scoping.py::approvals_inbox` |
| BR-09 | A rejection carries a note the applicant can read | domain, services | guard `has_decision_note` |
| BR-10 | An approved request may be cancelled only before it finishes, and only by its owner | domain, services | guard `not_finished`, transition table |
| BR-11 | Only the acting role's permissions count; scope narrows rows | services, selectors | `services/authz.py`, `selectors/scoping.py` |
| BR-12 | Types and entitlements are effective-dated; a change is a new version | models, services | `LeaveType.effective_from`, `services/policy_admin.py` |
| BR-13 | Annual entitlements are granted once per (person, type, year) | models, services | `leave_grant_once_per_year`, `balances.ensure_annual_grant` |
| BR-14 | A debit is written once per application, even under retries | models | `leave_debit_once_per_application` |
| BR-15 | A decision is recorded with actor and time, and can never be edited | models, services | `models/applications.py::LeaveEvent` |
| BR-16 | Every endpoint is behind the module grant *and* a permission | api | `HasModuleGrant("elm")` + `HasPermission(...)` on each view |
| BR-17 | A malformed query parameter is a 400, never a 500 | api | `views._int_param` |
| BR-18 | A row outside the caller's scope is a 404, not a 403 | selectors | detail views read through `scoping` |

## (b) Domain model

- **`LeaveType`** — `code`, `name`, `annual_entitlement_days`, `counts_calendar_days`,
  `allows_half_day`, `requires_reason`, `effective_from` (unique with `code`),
  `is_active`. Never edited; a new row supersedes. The selector picks the row with the
  greatest `effective_from <= today`.
- **`Holiday`** — `date` (unique), `name`, `created_by_user_id`. Working days exclude
  Saturdays, Sundays and these dates.
- **`LeaveApplication`** — `user_id` (plain IAM id, no FK), `leave_type` (local FK),
  `start_date`, `end_date`, `is_half_day`, `half_day_part`, frozen `days`, `reason`,
  `status`, decision actor/time/note. Partial unique index on `(user_id, start_date)`
  for active statuses; check constraints on date order and positive days.
- **`LeaveBalanceEntry`** — append-only ledger: `user_id`, `leave_type`, `year`,
  `kind` (`grant` / `debit` / `credit` / `reversal`), signed `days`, optional
  `application`, `granted_by_user_id`, `note`. Partial unique indexes make the annual
  grant and the per-application debit impossible to write twice.
- **`LeaveEvent`** — append-only audit: `application`, `from_status`, `to_status`,
  `actor_user_id`, `actor_label`, `note`, `at`.

No table stores roles or permissions; the IAM owns those. No FK crosses a module
boundary.

## (c) State machine

Declarative, in `domain/state_machine.py`.

| From | Event / to | Actor lane | Permission | Guards |
|---|---|---|---|---|
| — (composition) | `pending` | employee | `elm.application.create` | submit-time policy rules (BR-01…05) |
| `pending` | `approved` | approver | `elm.application.approve` | `not_self_approval`, `balance_sufficient` |
| `pending` | `rejected` | approver | `elm.application.approve` | `not_self_approval`, `has_decision_note` |
| `pending` | `withdrawn` | employee (owner) | `elm.application.delete` | — |
| `approved` | `cancelled` | employee (owner) | `elm.application.delete` | `not_finished` |

`rejected`, `withdrawn`, `cancelled` are terminal. Every change goes through
`services/applications.py::_transition`, which locks the row, resolves the edge,
checks the guards, writes `LeaveEvent`, and writes or reverses the ledger entry in the
same transaction. An illegal move is refused by construction.

## (d) Permission list (registry.py)

| Code | What it allows | Held by |
|---|---|---|
| `elm.application.create` | Submit a leave request | `Employee`, `faculty`, `staff` |
| `elm.application.view` | See requests within your scope (scope permission) | all employee and approver roles |
| `elm.application.approve` | Approve or reject a request | `Leave Approver`, `Leave Administrator` |
| `elm.application.delete` | Withdraw or cancel your own request | `Employee`, `faculty`, `staff` |
| `elm.balance.view` | See balances within your scope (scope permission) | employee and approver roles |
| `elm.balance.manage` | Grant or adjust balances | `Leave Administrator` |
| `elm.policy.manage` | Configure types, holidays, entitlements | `Leave Administrator` |
| `elm.balance.accrue` | Annual accrual task | _service only_ |

Roles: `faculty` and `staff` are held by definition; `Employee`, `Leave Approver` and
`Leave Administrator` are ordinary designations, created by the manifest and assigned
in the IAM console. A role that should see no leave screen is not granted the module.

## (e) Endpoints — `/api/v1/elm/`

Every endpoint sits behind `HasModuleGrant("elm")` and its own permission.

| Method | Path | Permission | Returns |
|---|---|---|---|
| GET | `types` | `create` or `view` | Effective leave types (latest version per code) |
| POST | `types` | `policy.manage` | New effective-dated version |
| POST | `types/<pk>/deactivate` | `policy.manage` | Retires one version |
| GET | `holidays` | `create` or `view` | Holidays, optionally by range |
| POST | `holidays` | `policy.manage` | Adds a holiday |
| DELETE | `holidays/<pk>` | `policy.manage` | Removes a mistaken holiday |
| GET | `applications` | `view` (scoped) | Own or in-scope requests |
| POST | `applications` | `create` | Submits a request |
| GET | `applications/<pk>` | `view` (scoped) | One request, 404 when out of scope |
| POST | `applications/<pk>/transition` | `approve` or `delete` | Decides, withdraws or cancels |
| GET | `applications/<pk>/history` | `view` (scoped) | Append-only audit trail |
| GET | `approvals` | `approve` | Pending queue, never the caller's own |
| GET | `balances` | `balance.view` (scoped) | Entitled / used / available per type |
| POST | `balances/grant` | `balance.manage` | Records a credit or a reversing entry |

No `Fusion-client` sidebar entry is needed: this repo's own `client/` renders the
module, and `Fusion-client`'s `INTEGRATED_MODULES` entry is recorded here for hand-over:
`{id: "leave_elm", label: "Leave Management", icon: "CalendarBlank", to: "/leave",
section: "Leave"}`.

## (f) Contracts

`modules/elm/contracts.py` exposes, plural by signature:

- `get_leave_balances(user_ids: Sequence[int], year: int) -> dict[int, tuple[LeaveBalanceDTO, ...]]`
- `get_leave_availability(user_ids: Sequence[int], on_date: date | None) -> dict[int, LeaveAvailabilityDTO]`

Nothing is needed from another module beyond `modules.directory`'s existing
`get_users` / `get_employees`.

## (g) Scheduled work

One beat entry, registered in `config/celery.py` from `modules/elm/schedule.py`:
the annual accrual on 1 April. If it does not run, nobody's entitlement is granted
for the year and the first request fails closed on `balance_sufficient` rather than
silently approving on an empty ledger. It is idempotent per (person, type, year) and
can be run by hand with `manage.py grant_annual_leave --year <year>`.

## (h) Open questions

1. **The official spec folder was not present in this workspace.** Rule numbers above
   are this pilot's own (BR-01…BR-18) and are cited in the code at their enforcement
   points. They must be reconciled with the official ELM-BR / ELM-UC / ELM-WF ids
   before review; no id invented here is dressed up as a spec id.
2. **Approval chain.** This pilot implements one approval step (a `Leave Approver`
   decides). A two-step recommend-then-sanction chain, if the spec requires it, is a
   state-machine extension, not a rewrite: add the intermediate state and the
   recommending role.
3. **Carry-forward and year-end.** Balances are per calendar year and do not carry
   forward. If the spec has a carry cap, it belongs in the annual grant task.
4. **Leave categories and entitlements.** Seeded defaults (CL/EL/VL/COL/RH) are pilot
   values in `seed_leave_policy`; the real entitlements are institute policy and must
   come from the spec.
5. **Half-day parts.** Only `first`/`second` are modelled; a spec that needs hour-level
   parts changes `count_days` only.
6. **Calendar-day types.** `counts_calendar_days` exists on the model, but no seeded
   type uses it; confirm against the spec.
