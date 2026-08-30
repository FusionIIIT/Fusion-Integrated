---
owner: leave-lead
status: authoritative
last-reviewed: 2026-08-31
---

# Counting and Entitlement

The arithmetic. This is the page to read before changing anything in `domain/counting.py` or
`domain/entitlement.py`, and the one to check a disputed figure against.

Both modules are framework-free — no Django import — which is what keeps every rule here unit-testable
without a database.

---

## Chargeable days

BR-EL-011. Two counting modes, decided by category:

| Mode | Categories | A Sunday inside the leave |
|---|---|---|
| **Continuous** | `EL`, `COL`, `VL` | charged |
| **Working days only** | `CL`, `RH`, `SCL` | not charged |

Worked example, Monday 10th to Monday 17th with the intervening Saturday and Sunday closed:

| Category | Charged |
|---|---|
| `EL` | **8** |
| `CL` | **6** |

A half day is `0.5` and is only available where the category allows it (BR-EL-010: casual leave), on a
single date. The database enforces the single date with a check constraint, not just the serializer.

---

## Early resumption

BR-EL-028. Somebody sanctioned to the 17th who returns on the 13th has not used the tail. What happens
to it is **policy**, because two defensible readings exist and the institute has to pick one:

| `early_return_tail` | Meaning | The example |
|---|---|---|
| `TRIM_TO_LAST_WORKING_DAY` *(default)* | Charge to the last working day actually absent | 5 days charged |
| `CHARGE_TO_RESUMPTION` | Charge the whole span up to resumption | 7 days charged |

The unused days come back as a `RESTORED` ledger entry, and only once the resumption is **verified** —
a reported return that nobody has checked does not move a balance.

---

## Entitlement and year end

`close_year()` is a pure function over balances and category policies. It returns a `YearEndOutcome`
naming what lapsed, what carried and what converted; the service turns that into ledger rows. Nothing
is mutated in place, so the outcome can be computed and inspected before it is written — which is what
`leave_year_end --dry-run` does.

### VL → EL conversion

BR-EL-007. Unused faculty vacation leave converts at the policy's ratio (currently 2:1), with the
policy's rounding:

| `vl_to_el_rounding` | 45 VL at 2:1 |
|---|---|
| `EXACT_HALF` *(default)* | 22.5 EL |
| `FLOOR_TO_WHOLE` | 22 EL |
| `ROUND_TO_WHOLE` | 23 EL |

Neither the ratio nor the rounding is a constant. `tests/test_entitlement.py` passes a 3:1 ratio
specifically to prove the arithmetic does not assume 2:1 — if somebody ever hardcodes it, that test
fails rather than the discovery happening in a pay dispute.

### Carry-forward

`EL` and `COL` carry, capped where the policy caps them. `CL`, `RH` and `SCL` lapse. `VL` neither
carries nor lapses outright — it converts, and whatever the conversion does not absorb lapses.

---

## The balance cannot go negative

Nothing is held against a pending request — that is deliberate, so an approval that never comes does not
keep days hostage. It also means two requests can each be affordable when they are made and unaffordable
together.

So the balance is checked **twice**: at submission, for early feedback, and again at final approval where
the days actually move, under a lock on that person's ledger for the year. The second check is the one
that matters; the first is a courtesy.

---

## Leave in the past

An application may reach back `max_backdate_days`, which defaults to **0**. Leave that genuinely happened
before it was recorded goes in through EL-UC-016 instead — entered by the leave administrator against the
written sanction, not applied for retrospectively by the person who took it.

---

## Overlap

BR-EL-012. A new request may not overlap leave the employee already holds, pending or approved. The one
exception is two half days on the same date: a first-half and a second-half casual leave do not clash
with each other, but either clashes with a full day.

The same check runs against the **nominated substitute**. Somebody who is themselves away over those
days covers nothing, and accepting the nomination would only surface as duties going unperformed.

`first_conflict()` returns the offending period so the refusal can name it — *"this overlaps leave you
already hold from 2 March to 4 March"* rather than "overlapping leave".
