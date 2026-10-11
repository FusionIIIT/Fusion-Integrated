---
purpose: >
  The ELM transition table as it exists in domain/state_machine.py, with the
  actor lane and guards for each edge, and the effects the service writes.
---

# ELM — state machine

A request is *composed* on the client and enters the database at `pending`; `draft`
is deliberately not a stored state, so there is no way to park a request in a state
no rule covers.

| # | From | To | Lane | Permission | Guards | Effects |
|---|---|---|---|---|---|---|
| 1 | _(new)_ | `pending` | employee | `elm.application.create` | submit-time rules | `LeaveEvent(→pending)`, annual grant ensured |
| 2 | `pending` | `approved` | approver | `elm.application.approve` | `not_self_approval`, `balance_sufficient` | `LeaveEvent`, debit entry |
| 3 | `pending` | `rejected` | approver | `elm.application.approve` | `not_self_approval`, `has_decision_note` | `LeaveEvent` |
| 4 | `pending` | `withdrawn` | employee (owner) | `elm.application.delete` | — | `LeaveEvent` |
| 5 | `approved` | `cancelled` | employee (owner) | `elm.application.delete` | `not_finished` | `LeaveEvent`, reversal entry |

`rejected`, `withdrawn`, `cancelled` are terminal.

## Guards

- `not_self_approval` — the actor's `user_id` may not equal the application's. The
  approvals queue already excludes the caller's own rows; this is the second lock.
- `balance_sufficient` — available = grants + credits + reversals − debits for
  `(user, type, start_date.year)`. A refusal names the shortfall and the available
  figure, so the message tells the approver what to do next.
- `has_decision_note` — a rejection whose note is blank is refused.
- `not_finished` — cancellation is refused once `today > end_date`; a finished leave
  is history and is corrected by an administrator, not by a cancel button.

## Who may drive an edge

The lane is derived from what the actor was granted, not from `principal.kind`:

```
employee   has elm.application.create or elm.application.delete, and is the owner
approver   has elm.application.approve
system     the accrual task
```

An approver acting on their own row is refused by `not_self_approval` regardless of
lane; a person holding both employee and approver roles keeps both abilities on
other people's requests, and only the employee lane on their own.

## Model invariants that back the table

- Partial unique `(user_id, start_date)` over active statuses — two identical active
  requests cannot both exist.
- Partial unique `(application)` for `kind = debit` — one debit per approval.
- `status` moves only inside `services/applications.py::_transition`, which locks the
  row with `select_for_update()` and refuses a terminal source state, so two approvers
  clicking at once produce one decision and one 409.
