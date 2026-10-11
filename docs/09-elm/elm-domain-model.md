---
purpose: >
  The ELM pilot's tables, what each one is for, and the invariants the database
  enforces so the service layer cannot forget them.
---

# ELM — domain model

## Entities

```
LeaveType 1 ─── n LeaveApplication n ─── 1 LeaveBalanceEntry(application)
   │                    │
   │                    └── n LeaveEvent            (append-only audit)
   └──────────── n LeaveBalanceEntry(leave_type, year)

Holiday                                  (calendar input to day counting)
```

People are plain integer `user_id`s projected from the IAM; no table here stores
identity, roles, or a user. No FK crosses a module boundary.

## LeaveType — configuration, effective-dated

| Column | Notes |
|---|---|
| `code` | `CL`, `EL`, `VL`, `COL`, `RH` in the seeded pilot |
| `name` | Human label |
| `annual_entitlement_days` | Granted once per person per year by the accrual |
| `counts_calendar_days` | Working days (default) vs calendar days |
| `allows_half_day` | Single-day half requests permitted |
| `requires_reason` | Submission refused without one |
| `effective_from` | Unique together with `code`; never edited in place |
| `is_active` | Retired versions stop being offered, history still resolves |

The selector resolves a type *on a date*: the row with the greatest
`effective_from <= date`. Changing an entitlement means inserting a new version.

## Holiday

`date` (unique), `name`, `created_by_user_id`. Holidays are an input to
`domain/policy.py::count_days`, never a hard-coded calendar.

## LeaveApplication

| Column | Notes |
|---|---|
| `user_id` | Plain IAM id (`UserScopedModel`), indexed |
| `leave_type` | Local FK, `PROTECT` — a type with history is never deleted |
| `start_date`, `end_date` | Half-open nowhere: both inclusive |
| `is_half_day`, `half_day_part` | `first` / `second`, single day only |
| `days` | **Frozen at submission** from the day-count rule; a later holiday edit never rewrites an old decision |
| `reason` | Required when the type says so |
| `status` | `pending` / `approved` / `rejected` / `withdrawn` / `cancelled` |
| `decided_by_user_id`, `decided_at`, `decision_note` | Written once, never edited |

Database-enforced invariants:

- `leave_application_dates_ordered` — `end_date >= start_date`.
- `leave_application_days_positive` — `days > 0`.
- `leave_application_one_active_per_day` — partial unique on `(user_id, start_date)`
  where the status is active: the second identical submission is a duplicate insert,
  not a race the service has to win.

## LeaveBalanceEntry — the ledger

Nothing stores a balance *column*; the balance is the sum of the ledger, computed in
`selectors/queries.py::balance_rows`. Corrections are new entries.

| Column | Notes |
|---|---|
| `leave_type`, `year` | The bucket the entry belongs to |
| `kind` | `grant` (+), `debit` (−), `credit` (±, manual), `reversal` (+) |
| `days` | Signed, never zero |
| `application` | Set for `debit` and its `reversal` |
| `granted_by_user_id`, `note` | Who did it and why |

- `leave_grant_once_per_year` — partial unique on `(user_id, leave_type, year)` where
  `kind = grant`: the annual accrual is idempotent at the database, not by a lock.
- `leave_debit_once_per_application` — partial unique on `(application)` where
  `kind = debit`: an approval can be retried and still debit once.

## LeaveEvent — audit

`application`, `from_status`, `to_status`, `actor_user_id`, `actor_label`, `note`,
`at`. Append-only: written by the transition choke point, exposed read-only through
`applications/<pk>/history`.
