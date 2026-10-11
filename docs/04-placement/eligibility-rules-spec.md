---
owner: placement-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Eligibility Rules Specification

A posting's eligibility rule is a small JSON AST, evaluated by `core/rules/engine.py` against a fixed
field vocabulary.

**Two non-negotiables:**

1. **Fail closed.** An unknown field, a missing fact, or any evaluation error means **ineligible with an
   explicit reason** — never eligible-by-default.
2. **Frozen on publish.** `eligibility_rule_locked_at` is stamped when a posting is published, and a
   database `CheckConstraint` enforces that a published posting has it. Rules cannot change after
   applications open.

The second is a fairness property, not a technical one. A student who applied under "CPI ≥ 7.0" must not
find themselves rejected because the rule silently became 7.5.

---

## Grammar

```
Rule    := Logical | Comparison
Logical := {"all": [Rule, ...]}        # AND — empty list is TRUE (vacuous)
         | {"any": [Rule, ...]}        # OR  — empty list is FALSE
         | {"not": Rule}
Comparison := {<op>: [<field>, <literal>]}
op      := eq | ne | gt | gte | lt | lte | in | not_in | between
```

Parsed and validated as a pydantic discriminated union (`core/rules/ast.py`), so a malformed rule is
rejected at **authoring** time with a field-level error, not discovered at evaluation time.

Nesting depth is capped at 5. Deeper rules are unreadable to the coordinator writing them and to the
student reading the failure.

### Example

```json
{"all": [
  {"gte":    ["cpi", 7.0]},
  {"in":     ["discipline", ["CSE", "ECE", "ME"]]},
  {"eq":     ["active_backlogs", 0]},
  {"lte":    ["current_semester", 8]},
  {"not":    {"eq": ["is_placed", true]}},
  {"any": [
    {"eq":   ["programme", "B.Tech"]},
    {"all": [{"eq": ["programme", "M.Tech"]}, {"gte": ["cpi", 7.5]}]}
  ]}
]}
```

Reads as: CPI ≥ 7.0, in one of three disciplines, no active backlogs, at most semester 8, not already
placed — and either B.Tech, or M.Tech with CPI ≥ 7.5.

---

## Field vocabulary

**Closed set.** A field not on this list is a validation error at authoring time and, defensively, an
ineligible-with-reason at evaluation time.

### From `academics.StudentAcademicStanding` — always the **declared** value

| Field | Type | Source | Notes |
|---|---|---|---|
| `cpi` | decimal | `standing.cpi` | The **declared** CPI of the latest declared semester. Never provisional. [academic-snapshot-integration.md](academic-snapshot-integration.md) |
| `earned_credits` | decimal | `standing.earned_credits` | Includes `S`-graded credits |
| `active_backlogs` | int | `standing.active_backlogs` | |
| `total_backlogs` | int | `standing.total_backlogs` | Includes cleared ones |
| `declared_semester` | int | `standing.semester` | The semester the CPI is *from*, not the student's current one |
| `declared_semester_type` | str | `standing.semester_type` | `Odd Semester` · `Even Semester` · `Summer Semester` |

> **A student with no `StudentAcademicStanding` row is ineligible for any rule referencing an academic
> field**, with reason `no_declared_standing`. This is the fail-closed rule that matters most: a first-year
> student with no declared result is not "CPI 0.0", they are "no declared CPI", and the two must not be
> confused.

### From `directory.UserRef`

| Field | Type | Notes |
|---|---|---|
| `programme` | str | `B.Tech` · `M.Tech` · `PhD` · … |
| `discipline` | str | `CSE`, `ECE`, `ME`, `SM`, `DES` — the acronym |
| `batch_year` | int | admission year |
| `current_semester` | int | the student's current semester, distinct from `declared_semester` |
| `gender` | str | ⚠️ **`SensitivePIIField`**. Permitted only for genuinely gender-specific programmes; every use writes an `audit_event` and appears in the weekly review. |
| `category` | str | ⚠️ **`SensitivePIIField`**. Same treatment. |

`gender` and `category` are available because some employers run genuinely restricted drives, but their use
is audited rather than silent — an unaudited category filter is a discrimination risk nobody would find
later.

### From `placement.PlacementRegistration` and `PlacementRecord`

| Field | Type | Notes |
|---|---|---|
| `is_registered` | bool | registered for this posting's year |
| `is_debarred` | bool | |
| `offer_count` | int | accepted offers held this year |
| `is_placed` | bool | an active `PlacementRecord` exists for the year |
| `best_accepted_tier_rank` | int/null | lower is better; null if unplaced |

### Derived

| Field | Type | Notes |
|---|---|---|
| `has_applied_to_company` | bool | already applied to another posting from the same company |
| `applications_this_year` | int | total submitted this year |

---

## Evaluation

```python
def evaluate(rule: Rule, facts: Facts) -> Outcome:
    """Fail-closed. Returns per-rule outcomes, not just a boolean."""
```

```python
@dataclass(frozen=True)
class RuleOutcome:
    path: str            # "all[0]"
    field: str           # "cpi"
    op: str              # "gte"
    required: Any        # 7.0
    actual: Any          # Decimal("6.80")
    passed: bool
    reason: str          # "cpi_below_minimum"

@dataclass(frozen=True)
class Outcome:
    is_eligible: bool
    outcomes: list[RuleOutcome]
    error: str | None = None
```

Pure function, no Django import, so its whole branch space is fast unit tests.

### Fail-closed table

| Situation | Result | Reason code |
|---|---|---|
| Field not in the vocabulary | ineligible | `unknown_field` |
| No `StudentAcademicStanding` and the rule reads an academic field | ineligible | `no_declared_standing` |
| Fact is `None` and the operator needs a value | ineligible | `missing_fact` |
| Type mismatch (`gte` on a string) | ineligible | `type_mismatch` |
| Nesting deeper than 5 | ineligible | `rule_too_complex` |
| Any unexpected exception | ineligible | `evaluation_error` (+ Sentry) |
| `{"all": []}` | **eligible** | vacuous truth — an empty rule means no restrictions |
| `{"any": []}` | ineligible | `no_alternatives_satisfied` |

Every branch is a test. `evaluation_error` also increments a counter and alerts, because a rule that cannot
be evaluated is a bug we want to hear about immediately rather than a silently-rejected cohort.

---

## What the student sees

`failed_rules` is stored on `EligibilityEvaluation` and rendered directly:

```
Not eligible for SDE-1 at Acme
  ✗ CPI 6.80 — 7.00 required
  ✗ 1 active backlog — 0 required
  ✓ Discipline CSE
  ✓ Not already placed
```

Reason codes map to human strings in one place (`domain/rules/messages.py`), so wording changes do not
touch the engine.

**Never "You are not eligible."** on its own. A student who cannot see which criterion they missed will ask
the placement office, and that is a support cost the design should not create.

---

## Caching and invalidation

```python
inputs_version = standing_version * 1_000_000 + registration_updated_epoch
```

`EligibilityEvaluation` stores it, and an evaluation is trusted only if the recomputed
`inputs_version` matches. So:

- A **new declaration** bumps `standing_version` → every evaluation for that student is stale → recomputed
  on next read. No explicit invalidation call, therefore no forgotten one.
- A **debarment** changes the registration timestamp → same effect.
- A **rule change** cannot invalidate anything, because rules are frozen on publish.

`is_eligible` is re-checked as a **guard at submission** (transition 1 in
[application-state-machine.md](application-state-machine.md)) and re-evaluated if stale. A cached
eligibility can never be the sole basis for accepting an application.

### Precompute

On `placement.posting.published`, a Celery task evaluates every registered student for that posting. This
makes the student's posting list a single indexed read (`evaluation_eligible_idx`, partial on
`is_eligible`) instead of N evaluations at page load — which is what keeps the list fast on deadline day.

---

## Authoring

Coordinators do not write JSON. The UI is a builder emitting the AST, with:

- a field picker restricted to the vocabulary, typed per field;
- **live preview: "142 of 310 registered students match"**, computed against current standings;
- a warning if fewer than 5 match, which almost always means a mis-set threshold;
- an audit entry whenever `gender` or `category` is used.

The preview is the highest-value part. A coordinator who sees "3 students match" fixes the rule before
publishing rather than after the complaints arrive.

Templates for common shapes ("B.Tech, CPI ≥ 7, no backlogs") are seeded and copyable.

---

## Freezing on publish

```python
def publish(posting_id: int, principal) -> JobPosting:
    with transaction.atomic():
        p = JobPosting.objects.select_for_update().get(pk=posting_id)
        validate_rule(p.eligibility_rule)                 # raises before anything is visible
        p.status = PostingStatus.PUBLISHED
        p.eligibility_rule_locked_at = timezone.now()
        p.published_at = timezone.now()
        p.save(update_fields=[...])
        emit("placement.posting.published", {...,
             "eligibility_rule_hash": sha256_of(p.eligibility_rule)})
```

After this point the rule is immutable. A genuine change means **cancelling the posting and creating a new
one**, which is visible to everyone and leaves the applications of the old posting intact and explainable.

Backed by `posting_published_has_locked_rule` in the database
([placement-domain-model.md](placement-domain-model.md#postings)), so it holds even if the service is
bypassed.

`eligibility_rule_hash` in the event lets us prove, later, which rule text a cohort was evaluated against.

---

## Verification

- **Every fail-closed row above** has a test.
- `{"all": []}` is eligible; `{"any": []}` is not.
- **A student with no declared standing** is ineligible for any academic rule, with reason
  `no_declared_standing` — *not* treated as CPI 0.0.
- **Provisional vs declared:** a student whose *undeclared* semester would qualify them is **ineligible**;
  after declaration, eligible. This is the test that proves the snapshot boundary holds end to end.
- Decimal comparison: CPI `7.00` satisfies `gte 7.0`; `6.999` does not. No float rounding anywhere —
  `Decimal` throughout.
- `failed_rules` contains one entry per leaf comparison, passed and failed alike, so the UI can show ✓ and ✗.
- Publishing validates the rule; an invalid rule cannot reach `published`.
- A published posting's rule cannot be edited (service raises; constraint holds).
- `inputs_version` changes on a new declaration and on debarment.
- Precompute for a 310-student cohort finishes within the task's soft time limit.
- **Query budget:** evaluating 300 students issues a constant number of queries — asserted with
  `django_assert_max_num_queries`, because the natural implementation of this is an N+1.
- Using `gender` or `category` in a rule writes an `audit_event`.
