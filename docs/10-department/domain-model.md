# Department: domain model

The blueprint (`department-blueprint.md`) is the design and its approval record. This page is the short
map for a maintainer.

## Aggregates

| Table | What it holds | Invariants the database enforces |
|---|---|---|
| `department_department` | One row per department (CSE, ECE, ME, Design, NS, SM, LA), seeded by `seed_departments` | code unique, name not blank |
| `department_official_change` | A proposed name or core-policy change, effective only on HOD approval | only `name`/`core_policies`; one pending per field; decided iff not pending |
| `department_announcement` | A notice with audience role, programme and batch year (blank = any) | title and body present; audience from a closed list |
| `department_inventory_item` | An item and its running quantity | quantity never negative; name unique per department, case-insensitive |
| `department_stock_movement` | The append-only ledger of receipts and issues | quantity positive; an issue names its request, a receipt none; no update or delete path |
| `department_stock_request` | A Faculty request through HOD decision to issue | quantity positive; status from the table; issued has an issuer |
| `department_feedback`, `department_feedback_note` | Confidential feedback and HOD oversight notes | reviewed iff not new; disposed iff terminal |
| `department_timetable_slot` | A class or lab slot | ends after it starts; day 0 to 6 |
| `department_lab_resource` | A lab and its equipment | name unique per department |
| `department_profile_record` | Department-local profile supplement; identity stays with the ERP | one per user per department; a login unless alumni; no sensitive field exists |
| `department_role_tenure` | Who holds HOD or Dept_Admin, and when. Grants no permission | interval positive; overlap refused under a department row lock |
| `department_notification_outbox` | Notices written in the event's transaction | dedupe key unique |

## State machines

All three are tables in `modules/department/domain/state_machine.py`; a move that is not listed cannot
be expressed, and every service change goes through `resolve()`.

```
stock request   (none) -Faculty-> pending_hod -HOD-> approved -Dept_Admin-> issued
                                   pending_hod -HOD-> rejected
feedback        (none) -Student/Faculty-> new -Dept_Admin-> under_review -Dept_Admin/HOD-> resolved | closed
official change (none) -Dept_Admin-> pending -HOD-> approved | rejected
```

## Who acts for which department

The acting IAM designation gives the verb (`registry.ROLE_GRANTS`). The department comes from:

- a student's discipline, or a faculty member's department, as `directory` projects them;
- for HOD and Dept_Admin, the designation names the department (`HOD (CSE)` → CSE), and a
  `RoleTenure` for that department naming the person must be in effect now. Without one, the
  person sees no rows and every write is refused (blueprint Q1).

## Deployment order

`migrate` → `seed_departments` → `seed_modules` → `seed_iam_permissions --manifest registry/permissions.json`
(from the IAM checkout) → record the first HOD and Dept_Admin tenures as `acadadmin` →
`check_department_readiness`. Beat must run `department.deliver_notifications` and
`department.apply_role_transitions`; `run_department_tasks` runs both by hand.
