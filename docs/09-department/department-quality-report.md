# Department quality report

## Scope and verification

The Department build implements announcement viewing, publication and maintenance, stock and issuance, confidential feedback and review, lab resources, timetable upload and editing, and department details and official proposals. The [blueprint](department-blueprint.md) describes the access model. The [implementation reference](department-reference.md) links the specification to the code and marks external dependencies.

| Check | Observed result |
| --- | --- |
| `make check` | Django checks, migration drift, Ruff, five import contracts, cross-module FK, contracts, navigation, generated permissions, schema and the PostgreSQL pytest suite passed. |
| `make check-client` | Type checking passed. Seven test files and 40 tests passed. Vite produced the production build. |
| `.venv/bin/pytest modules/department --cov=modules/department --cov-branch --cov-report=term-missing --cov-fail-under=90` | 21 tests passed. Combined line and branch coverage was 92.60%. |
| `.venv/bin/pytest modules/department --cov=modules/department/domain --cov-branch --cov-report=term-missing --cov-fail-under=95` | 21 tests passed. Domain coverage was 100%. |
| `manage.py check --deploy --fail-level WARNING` with local production-shaped settings | System check identified no issues (2 silenced). |
| Department-only Playwright run without the unrelated Placement global setup | 2 passed. The public synthetic student account opened announcements and the confidential feedback form through the real portal and IAM. |
| Repository-wide `make e2e` | 11 passed in 6.4 seconds, including both Department browser checks. The Department staff walkthrough is open. |

## Test evidence

The Department announcement and workflow suites exercise audience relevance, both permission gates, active-role selection, scoped edits, immutable stock movements, approval before issuance, the post-approval shortage case, handling of confidential feedback, atomic timetable uploads, Faculty lab-resource scope and approval before publishing official changes. The frontend tests cover empty and paged announcements. The two browser checks exercise `UC-DEPT-001` and the `UC-DEPT-007` form. The wider per-use-case browser suite and the five intentional regression mutations required by the review prompt are open.

## Deployment and authorization

1. Apply Django migrations to the Fusion-Integrated PostgreSQL database. The stock movement migration installs the database trigger that rejects updates and deletes.
2. Run `manage.py seed_modules` and `make permissions`. Apply the manifest from the IAM checkout using `manage.py seed_iam_permissions --manifest <Fusion-Integrated>/registry/permissions.json`.
3. Use IAM to confirm verified designations and the active role. Check the Department announcement page under a basic student or Faculty designation and the relevant workflows under a scoped HOD and Dept_Admin designation.

The isolated database accepted all Department migrations. The portal uses the shared HTTP and CSRF stack. Department intersects the active designation's grant set with IAM permissions, scopes queries before returning rows, and resolves identity attributes live. Feedback notices omit confidential content. Issuance, stock audit and notices commit atomically. The browser refreshes in-app notices while the Department module is open. The complete fresh-install and staff browser proof remain open because the available public fixture also lacks tables used by the full IAM academic sync.

## Approval and known gaps

On 22 November 2026, Student 1 relayed that Student 2 approved the blueprint and the documented open decisions. The exact relay began “Student 2 said ok to the blueprint”. The initial announcement-read commit precedes that relay. No independent Student 1 scorecard has been received.

- `UC-DEPT-015` and `UC-DEPT-016` remain deferred until approved profile fields, profile write semantics and authoritative instructor-to-student scope are available.
- `UC-DEPT-020` and `UC-DEPT-022` remain deferred until IAM allows time-bounded per-department assignments, active-role cardinality, an atomic handoff and authoritative Headship. The verified static office designations are used for the implemented local workflows.
- IAM currently supplies module and sidebar navigation across held roles to the shared shell. The Department API and pages apply the active-role intersection. A role-filtered shared shell requires a platform change.
- Student academic information is limited to the verified programme and batch plus applicable timetable slots. A broader programme catalogue has no source contract in this build.
