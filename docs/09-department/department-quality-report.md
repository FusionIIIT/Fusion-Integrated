# Department quality report

## Scope and verification

The Department build implements announcement viewing, publication and maintenance, stock and issuance, confidential feedback and review, lab resources, timetable upload and editing, and department details and official proposals. The [blueprint](department-blueprint.md) describes the access model. The [implementation reference](department-reference.md) links the specification to the code and marks external dependencies.

| Check | Observed result |
| --- | --- |
| `make check` | Django checks, migration drift, Ruff, five import contracts, cross-module FK, contracts, navigation, generated permissions, schema and the PostgreSQL pytest suite passed. |
| `make check-client` | Type checking and the production build passed. All 99 client tests passed. |
| Department backend coverage, excluding spec tests | 139 tests passed. Combined line and branch coverage was 94.23% against the 90% gate. |
| Domain coverage, excluding spec tests | 100% coverage against the 95% gate. |
| Active specification strategies | BR 36, FR 45, UC 34 and WF 12 passed. There were zero failures or skips. |
| `manage.py check --deploy --fail-level WARNING` with local production-shaped settings | System check identified no issues (2 silenced). |
| Repository-wide `make e2e` | 14 passed, including the Department role journeys, confidential feedback, HOD oversight, direct-route refusals and keyboard-only feedback submission. |

## Test evidence

The [Round 1 fix record](reviews/round-1/fix-record.md) preserves the original independent report, maps all 15 findings to fixes or remaining work, and links the command output. The Department builder suite now has 10 announcement tests, 20 HTTP journey tests, 8 invariant tests and 101 review regression tests. It covers database timetable conflicts, threaded stock issuance, the two endpoint permission gates, cookie CSRF, write throttling, constant query counts and illegal state transitions.

The Step 9 check found that a person could change roles and act on their own submission. Department now excludes that person's pending stock requests, feedback and pending proposals from the relevant queues and refuses the write by ID. Three backend mutations verified the feedback queue scope, proposal ownership check and oversight overwrite protection. Two frontend mutations verified the HOD-only control and inbox error state. All five mutations caused test failures and were restored before the final run.

The component suite covers workflow loading, empty and error states, denied controls, selected main actions and all nine production route guards. The browser suites exercise the main flows through forms and role switches. The Step 9 review was a self-review. Exhaustive alternate-flow and manual per-page walkthrough evidence was outside this pass.

## Deployment and authorization

1. Apply Django migrations to the Fusion-Integrated PostgreSQL database. The initial migration installs the stock movement immutability trigger and timetable exclusion constraints. Two subsequent migrations add stock decision and feedback oversight records. Existing developer databases on the old incremental history must follow the transition note in the Round 1 fix record. Fresh databases migrate normally.
2. Run `manage.py seed_modules` and `make permissions`. Apply the manifest from the IAM checkout using `manage.py seed_iam_permissions --manifest <Fusion-Integrated>/registry/permissions.json`.
3. Run `manage.py department_readiness`. Use IAM to confirm the verified designations and active role, then check the Department announcement page under a basic student or Faculty designation.

A throwaway PostgreSQL database migrated, rolled back Department to zero and migrated again. Readiness reported the missing module registration before seeding and passed after seeding. With the provisioned IAM fixture, a fresh platform database returned HTTP 200 for student login and the first announcement read, and HTTP 403 for a cookie-authenticated feedback write without a CSRF header. Feedback notices omit confidential content. Issuance, stock audit and notices commit atomically.

## Approval and known gaps

On 22 November 2026, Student 1 relayed that Student 2 approved both the blueprint and the open decisions and recommendations in `labs/lab-9/Department-Phase-0.md`. The initial announcement-read commit precedes that relay. In the 23 November 2026 assignment handoff, Student 1 confirmed the pair’s decision in writing: “Accept the named dependencies and programme scope.” The decision covers these three items:

- **Profiles** (`UC-DEPT-015`, `UC-DEPT-016`, `CFR-DEPT-009` and `010`, `AFR-DEPT-024`–`028`, `BR-DEPT-019`). Defer profile viewing and editing until there are approved privacy and field rules, a profile-write contract and an authoritative teaching roster.
- **Central role assignments and Headship** (`UC-DEPT-020`, `UC-DEPT-022`, `CFR-DEPT-016`, `AFR-DEPT-047`–`053`, `BR-DEPT-021`–`024`, `BW-DEPT-07` and `08`, and `CW-DEPT-04`). Keep these workflows in IAM pending time-bounded per-department assignments, a single active holder per role, an atomic handoff and an authoritative Headship projection. Verified static office designations serve the implemented local workflows.
- **Student academic information** (`UC-DEPT-018`, `AFR-DEPT-036` and `037`). Show the verified programme and batch plus applicable published timetable slots. A broader programme catalogue is outside the agreed scope.

Separately, IAM supplies module and sidebar navigation across held roles to the shared shell. The Department API and pages apply the active-role intersection. A role-filtered shared shell requires a platform change.

On 23 November 2026, Student 2 wrote in the assignment handoff, “Since we are short on time, let us stash the skipped tests and move on with whatever is already implemented. Record what tests were skipped though so we can come back later.” The profiles and IAM/Headship cases are accepted dependencies for this branch. Their system-level verification remains pending. See the [case-by-case triage](spec-tests/triage.md).

For UC-DEPT-014, “HOD oversight is recorded” through an explicit action after the initial Dept_Admin review. Department records the HOD's identity, time and notes without advancing the reviewed status or notifying the submitter. The feedback inbox exposes the action to the HOD and keeps its record with the confidential feedback.

Step 7 clearance was missed. The designs were committed locally before conversion, and the required pre-conversion push was missed. See the [Round 3 scorecard](reviews/round-3/scorecard.md) and the [baseline record](spec-tests/triage.md).
