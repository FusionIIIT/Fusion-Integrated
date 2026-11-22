# Department quality report

## Scope and verification

The Department build implements announcement viewing, publication and maintenance, stock and issuance, confidential feedback and review, lab resources, timetable upload and editing, and department details and official proposals. The [blueprint](department-blueprint.md) describes the access model. The [implementation reference](department-reference.md) links the specification to the code and marks external dependencies.

| Check | Observed result |
| --- | --- |
| `make check` | Django checks, migration drift, Ruff, five import contracts, cross-module FK, contracts, navigation, generated permissions, schema and the PostgreSQL pytest suite passed. |
| `make check-client` | Type checking passed. Nine test files and 77 tests passed. Vite produced the production build. |
| `.venv/bin/pytest modules/department --cov=modules/department --cov-branch --cov-report=term-missing --cov-fail-under=90` | 91 tests passed. Combined line and branch coverage was 92.74%. |
| `.venv/bin/pytest modules/department --cov=modules/department/domain --cov-branch --cov-report=term-missing --cov-fail-under=95` | 91 tests passed. Domain coverage was 100%. |
| `manage.py check --deploy --fail-level WARNING` with local production-shaped settings | System check identified no issues (2 silenced). |
| Repository-wide `make e2e` | 13 passed, including completed Department journeys for Student, Faculty, HOD and Dept_Admin, confidential feedback submission and direct-route refusals. |

## Test evidence

The [Round 1 fix record](reviews/round-1/fix-record.md) preserves the original independent report, maps all 15 findings to fixes or remaining work, and links the actual command output. The backend now has 10 announcement tests, 18 HTTP journey tests, 7 invariant tests and 56 review regression tests. It covers database timetable conflicts, real threaded stock issuance, the two endpoint permission gates, cookie CSRF, write throttling, constant query counts and illegal state transitions. Five intentional enforcement mutations each caused test failures; restoring the original files returned all 91 tests to green.

The component suite covers workflow loading/empty/error states, denied controls, selected main actions and direct-route permission checks. Real-browser journeys complete the 16 locally implemented use cases through forms and role switches. External-contract use cases, the exhaustive alternate-flow and per-page action matrices, and a complete Department keyboard-only walkthrough remain open. These are builder checks, not an independent 10/10 verdict.

## Deployment and authorization

1. Apply Django migrations to the Fusion-Integrated PostgreSQL database. The single initial migration installs the stock movement immutability trigger and timetable exclusion constraints. Existing developer databases on the old incremental history must follow the transition note in the Round 1 fix record; fresh databases migrate normally.
2. Run `manage.py seed_modules` and `make permissions`. Apply the manifest from the IAM checkout using `manage.py seed_iam_permissions --manifest <Fusion-Integrated>/registry/permissions.json`.
3. Use IAM to confirm verified designations and the active role. Check the Department announcement page under a basic student or Faculty designation and the relevant workflows under a scoped HOD and Dept_Admin designation.

The isolated database accepted all Department migrations. The portal uses the shared HTTP and CSRF stack. Department intersects the active designation's grant set with IAM permissions, scopes queries before returning rows, and resolves identity attributes live. Feedback notices omit confidential content. Issuance, stock audit and notices commit atomically. The browser refreshes in-app notices while the Department module is open. Fresh test databases apply the complete initial schema and staff browser journeys pass. A complete fresh IAM/ERP installation remains unverified because the available public fixture lacks tables used by the full IAM academic sync.

## Approval and known gaps

On 22 November 2026, Student 1 relayed that Student 2 approved both the blueprint and the open decisions and recommendations in `labs/lab-9/Department-Phase-0.md`. The initial announcement-read commit precedes that relay. The relay is written evidence of what Student 1 reported, and direct written decisions from Student 2 for the individual deferrals are outstanding. The independent Round 1 preflight issued no official scorecard. On 23 November Student 1 relayed Student 2’s direction to “explore the best options available, and execute them.” The concrete choices and the limits of this delegated direction are recorded in the Round 1 fix record; no later-round waiver is claimed.

- **Profiles** (`UC-DEPT-015`, `UC-DEPT-016`, `CFR-DEPT-009` and `010`, `AFR-DEPT-024`–`028`, `BR-DEPT-019`). The 22 November relay covers the profile deferral in Phase 0 decision 2. Keep profile reads and writes deferred until approved field lists, profile write semantics and an authoritative teaching roster are available.
- **Central role assignments and Headship** (`UC-DEPT-020`, `UC-DEPT-022`, `CFR-DEPT-016`, `AFR-DEPT-047`–`053`, `BR-DEPT-021`–`024`, `BW-DEPT-07` and `08`, and `CW-DEPT-04`). The 22 November relay covers the proposed IAM deferral in Phase 0 decision 1. Keep these workflows in IAM pending time-bounded per-department assignments, active-role cardinality, an atomic handoff and an authoritative Headship projection. Verified static office designations serve the implemented local workflows.
- IAM currently supplies module and sidebar navigation across held roles to the shared shell. The Department API and pages apply the active-role intersection. A role-filtered shared shell requires a platform change.
- Student academic information is limited to the verified programme and batch plus applicable timetable slots. A broader programme catalogue has no source contract in this build.
