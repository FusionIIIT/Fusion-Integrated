---
owner: leave-lead
status: authoritative
last-reviewed: 2026-08-31
---

# Leave Domain Model

> Looking for a specific business rule or use case? **[The ELM reference](ELM_REFERENCE.md)**
> lists all 32 rules and 16 use cases with a link to the line that decides each one.

Employee Leave Management, built from the ELM specification set v1.2/v1.3. Every rule below cites the
document it comes from; nothing here is invented policy.

The module's job is narrow and unforgiving: it decides how many days somebody is owed, whether a
request may be granted, who grants it, and what the balance is afterwards. All four answers have to
still be defensible in twenty years, which is what shapes most of the decisions on this page.

---

## The five design decisions that matter

| Decision | Why | Where |
|---|---|---|
| **The balance is a ledger, not a column** | A stored counter edited from several places drifts, and a drifted balance cannot be argued about. Summing rows can always be re-derived and explained entry by entry. A wrong entry is corrected by a reversing entry, so the record of what happened survives the correction. | `models/ledger.py` |
| **Policy is effective-dated and never edited** | BR-EL-030. A decision is judged against the ordinance in force when it was taken. A revised ordinance is a new version with its own effective date, so last year's approvals still explain themselves. | `models/policy.py` |
| **Transitions are a table, not branches** | An illegal state change is *inexpressible* rather than rejected in a check somebody can forget to write. The table renders into the diagram, so the code and the workflow document cannot disagree silently. | `domain/state_machine.py` |
| **Authority is configuration** | BR-EL-019. Naming offices in code makes a reorganisation into a deployment. Here it is a row. | `models/workflow.py::AuthorityRule` |
| **No figure is hardcoded** | Entitlements, the VL:EL ratio, rounding, the early-return rule and the SLA thresholds all come from the policy row. A test passes a 3:1 ratio to prove the arithmetic does not assume 2:1. | `tests/test_entitlement.py` |

---

## Bringing the module up

The module is inert until a policy and a calendar are published and the year is credited. All three
steps are needed, and skipping the third is the easy mistake: a policy that grants 8 casual leave grants
nobody anything until a credit row exists, because the balance is a **sum of the ledger**.

```
manage.py sync_directory        # pull the payroll into the local projection
manage.py seed_leave_policy     # policy + routing + a minimal calendar, published
manage.py leave_credit_year 2026
manage.py seed_modules          # last: this is what makes Leave visible
manage.py leave_readiness       # says yes, or exactly what is still missing
```

**`seed_modules` comes last, and it checks.** The module declares its prerequisites in
`registry.readiness()`, and until they are met it registers as `planned` rather than `active` — which
keeps it out of every sidebar and off every route. A module that advertises itself and then refuses
every application reads as a broken system; one nobody can see yet reads as a rollout in progress. The
deploy runs `leave_readiness` and reports, without failing the release.

`sync_directory` comes first and is not optional. It reconciles in **both** directions — it brings
people in and retires anyone the identity service no longer calls an employee, because a projection
that only ever grows keeps crediting someone who was reclassified upstream. The directory projection normally fills in lazily as
screens ask for names, so it routinely holds a fraction of the institute; crediting against that would
report success and leave most of the staff with nothing. `leave_credit_year` therefore asks the identity
service **which** employees it knows and refuses if any are missing, naming them. It compares identities
rather than counts, because a stale row standing in for a missing one keeps the totals equal — which is
exactly the case the guard exists to catch.

### Undoing a credit

`leave_credit_year <year> --revoke` reverses the entitlement of anyone who has been credited and is not
an employee. It writes reversing entries linked by `reverses_id`, never deletions: an audit has to be
able to see the mistake and the correction, not a tidy absence. It refuses where any of the leave has
already been used — taking back days somebody was approved for is a decision about their leave, not a
bookkeeping correction.

`seed_leave_policy` transcribes the entitlements from BR-EL-002 to BR-EL-009 — it does not choose them.
Read them against the ordinance before a real year opens, and supersede the version rather than editing
it. It refuses to run if a policy is already published, so it cannot overwrite a configured institute.
`--draft-only` writes everything without publishing, for review first.

Holidays and vacation periods are institute data and are added under **Policy & Calendar**. Until a
vacation period exists, `VL` cannot be applied for; until restricted holidays are published, neither
can `RH`.

Everything the seed does is also available through the API to anyone holding `leave.policy.manage` or
`leave.calendar.manage`, so an institute that wants nothing seeded can configure it from the screens.

> **If nothing is published**, every application is refused with `409 no_effective_policy` and a message
> naming who has to act. It used to be a 500; `NoEffectivePolicy` is a `DomainError` precisely because a
> fresh install is the state in which the first person clicks Apply.

---

## Leave categories

BR-EL-002 to BR-EL-009. The figures below are **the current policy's**, not constants in the code.

| Code | Name | Annual credit | Carries forward | Counts intervening holidays | Half day |
|---|---|---|---|---|---|
| `CL` | Casual Leave | 8 | no | no | yes |
| `RH` | Restricted Holiday | 2 | no | n/a — one published date | no |
| `SCL` | Special Casual Leave | 15 | no | no | no |
| `EL` | Earned Leave | 30 (non-faculty) | yes | **yes** | no |
| `COL` | Commuted Leave | 20 | yes | **yes** | no |
| `VL` | Vacation Leave | 60 (faculty) | no — converts | **yes** | no |

**Continuous counting** is the rule most often got wrong. For `EL`, `COL` and `VL`, a Saturday, Sunday
or holiday falling *inside* the leave is charged; for `CL`, `RH` and `SCL` it is not. Monday the 10th to
Monday the 17th is **8 days** of EL and **6 days** of CL.

`S`-shaped edge cases are handled in `domain/counting.py` and pinned by `tests/test_counting.py`.

---

## Tables

```
leave_policy(version UNIQUE, effective_from, effective_to NULL, published,
  vl_to_el_ratio, vl_to_el_rounding, early_return_tail)
leave_category_rule(policy FK, category, annual_credit, carries_forward,
  carry_forward_cap NULL, applies_to_faculty NULL, requires_evidence)

leave_holiday_calendar(year, version, published)
leave_holiday(calendar FK, day, name, restricted)
leave_vacation_period(calendar FK, name, starts_on, ends_on)

leave_ledger_entry(user_id, year, category, days, reason, request_id NULL,
  policy_id NULL, reverses_id NULL, recorded_by_user_id NULL, note)
  -- append-only. There is no balance column anywhere in this module.

leave_request(user_id, category, state, starts_on, ends_on, half, reason,
  requested_days, actual_days NULL, policy_id, calendar_id, unit,
  station_leave, station_destination, station_from, station_to,
  extends_request_id NULL, resumed_on NULL, decided_at NULL)
leave_substitute_nomination(request FK, substitute_user_id, response,
  responded_at NULL, remark, supersedes_id NULL)

leave_request_transition(request FK, from_state, to_state, event, actor_role,
  actor_user_id NULL, remark, workflow_ref)      -- append-only
leave_authority_rule(policy_id, category, unit, designation,
  applies_to_faculty NULL, establishment_step, sanctioning_designation,
  self_sanction, specificity)
  UNIQUE(policy_id, category, unit, designation)
leave_sla_rule(policy_id, state, remind_after_hours, escalate_after_hours,
  escalate_to_designation)                        UNIQUE(policy_id, state)
leave_sla_clock(request FK, state, assigned_user_id NULL, started_at,
  remind_at, escalate_at, reminded_at NULL, escalated_at NULL, stopped_at NULL)
```

Eleven tables, eleven database check constraints. The constraints are tested by attempting to insert
bad rows, not by reading the migration — a constraint nobody has watched reject something is a
constraint that might not be there.

### Why `unit` is a name and not an id

There is no numeric organisational-unit registry in this institute's data. The directory carries a
department name, and that is what the leave module keys on. Modelling it as a surrogate integer meant
nothing could populate it, and an unpopulated scope column does not fail loudly — it silently widens
the review queue to the whole institute.

`AuthorityRule.unit` is **empty rather than null** for "any unit", because a null defeats the unique
constraint on Postgres and two conflicting general rules could then coexist.

---

## Balances

`selectors/balances.py` aggregates the ledger. `statement()` returns the rows behind a figure, and the
UI puts them one click from the number, because a balance nobody can explain is a balance that gets
disputed.

| Reason | Sign | Written by |
|---|---|---|
| `ANNUAL_CREDIT` | + | year-end / `credit_year` |
| `OPENING_BALANCE` | + | year-end carry-forward |
| `CONSUMED` | − | final approval |
| `RESTORED` | + | early resumption, verified |
| `CANCELLED` | + | approved cancellation |
| `LAPSED` | − | year-end |
| `CONVERTED_OUT` / `CONVERTED_IN` | − / + | year-end VL→EL |
| `OFFLINE_RECORDED` | − | EL-UC-016 |
| `CORRECTION` | ± | administrative correction |

**Balance moves only at final approval.** A request sitting in a queue has reserved nothing, which is
deliberate: an approval that never comes must not hold days hostage.

---

## Year end — SF-EL-001

`services/yearend.py`, run by `manage.py leave_year_end <year>`.

1. Lapse what does not carry.
2. Convert unused faculty `VL` into `EL` at the policy's ratio, with the policy's rounding.
3. Carry `EL` and `COL` forward, capped where the policy caps them.

Idempotent per employee and year: a year already carrying closing entries is skipped rather than
settled twice. `--dry-run` rehearses the whole run inside a rolled-back transaction, `--user` re-runs
one account after a correction.

> A bug worth remembering: the conversion silently vanished for faculty with no existing `EL` row,
> because the balance selector only returns categories that have entries. The close now seeds every
> policy category plus `EL` before settling.

---

## The clock, not a person — SF

Three of a request's transitions are the passage of time rather than anybody's decision: leave starts
on its start date, reaches its end date, and opens for resumption. `manage.py leave_advance`, and the
`leave.advance_lifecycle` beat task, are what make those happen.

Nothing invoked them at first, and the consequences were not confined to a request sitting in the wrong
state. Approved leave never became `ONGOING`, so it stayed **cancellable after the employee had already
gone**; extension is only reachable while the leave runs, so it was unreachable entirely; resumption
never opened, so nothing ever closed and no early return ever restored a day.

It runs at 00:05 and again at 06:15. The second pass is not redundancy for its own sake — the
transitions are calendar days rather than moments, the operation is idempotent, and one pass takes a
request the whole way, so the morning run silently covers a worker that was down overnight.

---

## SLA — SF-EL-002

BR-EL-032, BR-EL-033. A clock starts when a request enters a state somebody must act in and stops the
moment it leaves; nothing is chased once the task is no longer pending. Thresholds are policy rows,
not constants. `manage.py leave_sla` reminds, then escalates, and stamps both on the clock so
"we did tell them" is answerable from the record.

Queue states name no individual — the queue is the assignment. A nomination is the exception: exactly
one person is being waited on, and the clock names them.

---

## What this module does not do

- It does not send mail. Reminders and escalations are stamped and logged; delivery belongs to a
  notification service this module does not own yet.
- It does not decide leave policy. Every figure is a row somebody with `leave.policy.manage` entered.
- It does not hold a user table. People are plain `user_id` integers, and names come from
  `modules.directory.contracts`.
