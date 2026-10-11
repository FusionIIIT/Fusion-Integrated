---
purpose: >
  Index for the Employee Leave Management pilot: what it is, what to read,
  and how to turn it on from nothing.
---

# 09 — Leave (ELM) pilot

`modules/elm` implements the Employee Leave Management pilot: an employee submits a
leave request, an approver decides it, and an approval debits an append-only balance
ledger.

| Doc | Scope |
|---|---|
| [elm-blueprint.md](elm-blueprint.md) | The pre-code blueprint: rules, permissions, endpoints, contracts, scheduled work, open questions |
| [elm-domain-model.md](elm-domain-model.md) | Tables, invariants enforced by the database, the ledger |
| [elm-state-machine.md](elm-state-machine.md) | The transition table, guards, and who may drive each edge |

## Turn it on from nothing

```bash
make migrate                       # schema
python manage.py seed_leave_policy # the five leave types, effective today
python manage.py seed_modules      # registers the module once readiness clears
python manage.py leave_readiness   # names every unmet prerequisite
make permissions                   # publish the manifest the IAM seeds from
```

`manage.py grant_annual_leave --year 2026` records the annual grant for every
employee; submissions also ensure their own grant, so the first request works on a
fresh database. The same task runs on a beat schedule from 1 April.

## What this pilot does not cover

The official spec folder was not available in the workspace this was built in; the
blueprint's rule numbers are the pilot's own and must be reconciled with the official
ELM-BR/UC/WF ids. Carry-forward, a two-tier approval chain and hour-level half days
are listed as open questions in the blueprint.
