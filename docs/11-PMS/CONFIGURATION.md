# PMS Configuration (M1, DEC-7 / DEC-8 / DEC-9)

Operator policy is read from `PmsConfiguration` (`key`, JSON `value`). The
decision services use this configuration rather than inventing an escalation
threshold, appeal period, or maintenance schedule.

## What is seeded

`0002_seed_pms_configuration` seeds **only** the three values the
specifications state outright:

| Key | Seeded value | Authority |
|---|---|---|
| `review_business_days` | `15` | BR-PMS-031 |
| `revision_days` | `60` | BR-PMS-035 |
| `alert_offsets` | `[30, 15, 5]` | PMS-AFR-176, 177, 178 |

## What is deliberately **not** seeded

PS §2.4 says PMS must not define these, so they ship absent and stay `None`
until an operator sets them. An absent value is never guessed:

| Key | Effect while unset |
|---|---|
| `budget_threshold` | No escalation comparison; the Director's decision stands and the audit records `threshold: "not configured"` (BR-PMS-051). `PatentBudget.threshold_limit` retains a legacy model default of 100000, but current `decide_budget` does not consult it when policy is unset. The legacy field is therefore not the authoritative policy. |
| `appeal_period_days` | No appeal window is enforced (BR-PMS-093). |
| `escalation_chain` | Missed deadlines raise the escalation notification only; no chain is invented (BR-PMS-104). |
| `maintenance_schedule` | No renewal cycle is created; grant and renewal audits record `schedule not configured` (BR-PMS-060). |
| `holiday_calendar` | Business days are plain Mon–Fri (DEC-9). |

## Writing values

```python
from modules.pms.services import set_policy_value, unset_policy_value, configured_keys, load_policy

set_policy_value("budget_threshold", "100000.00")
set_policy_value("holiday_calendar", ["2026-01-26", "2026-03-04"])
set_policy_value("maintenance_schedule", {
    "IN": [
        {"cycle": 1, "due_after_days": 1095, "fee_amount": "5000.00"},
        {"cycle": 2, "due_after_days": 1460, "fee_amount": "6000.00"},
    ]
})
```

`set_policy_value` parses the value against `PmsPolicy` before storing, so an
invalid value is rejected at write time instead of surfacing later as a wrong
deadline. Unknown keys are rejected — a typo must not look like a configured
policy.

The API still accepts and persists an optional `threshold_limit` on budget
submission for compatibility. When `budget_threshold` is configured, policy
configuration controls escalation. When it is unset, no comparison is made;
the stored legacy field value does not imply an active escalation threshold.

## How the services use it

| Service | Policy read |
|---|---|
| `calculate_review_deadline` | `review_business_days`, `holiday_calendar` |
| `calculate_revision_deadline` | `revision_days` |
| `monitor_and_process_deadlines` | `alert_offsets` (notification topics `deadline.alert_<n>` are accepted for any configured offset) |
| `decide_budget` | `budget_threshold` |
| `schedule_cycle` (grant / renewal) | `maintenance_schedule` per jurisdiction |

## Guarantees

- A missed **review** or **office-action** deadline escalates; it never changes
  the application's status (DEC-9).
- Revision expiry remains a rule-driven lifecycle transition mandated by
  BR-PMS-038 / PMS-AFR-072 — it is a specification rule, not a deadline
  escalation.
- Maintenance never fabricates a due date or a fee: without a schedule, no
  cycle row is written and the audit says `schedule not configured`.
- Budget escalation remains external/configured; M1 adds no internal approval
  transition and no automatic approval (DEC-2).

## Deployment and operator commands

For a new environment, apply migrations, run `seed_pms_configuration`, register
modules with `seed_modules`, grant permissions through the platform IAM, then
run `pms_readiness`. The policy command creates only missing fixed defaults and
does not overwrite operator values. The migration also seeds those defaults,
so this command is safe to repeat after migration. Readiness exits unsuccessfully
while the required IAM Director-domain projection, trusted scanner/private
storage, or external prior-art source is unavailable; it prints each missing
prerequisite and does not claim that these integrations exist.

The scheduled tasks can be invoked synchronously during operations or incident
response with `run_pms_deadlines` and `run_pms_notifications --limit 50`. These
commands call the same task entry points registered in Celery Beat; they do not
create an alternative workflow or bypass task/service idempotency.
