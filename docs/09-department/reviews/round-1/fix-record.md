# Round 1 continuation — 23 November 2026

The [original review](https://github.com/LightCreator1007/Fusion-Integrated/blob/fc65686cccb157fe1ab768c4ed57e624a8bb4e58/docs/09-department/reviews/round-1/original-review.md) is preserved unedited. It reviewed
`8a550b4d3a2f67102bb3bebf44f30d93cf667aea`, stopped official preflight on a global
instruction file, and separately returned 15 findings. It did not award a score.
This file records builder work, not an independent verdict.

## Pair direction and choices

On 23 November, Student 1 relayed that Student 2 was present and said:
“explore the best options available, and execute them.” This authorizes investigating
and implementing the supported options; it is not represented as a retroactive
approval of every deferral or a waiver of a specification requirement.

The current IAM supplies live department, programme and batch fields, but no
teaching-roster/profile-write contract or effective-dated department-role assignment
contract. Keep authoritative identity and role data in IAM. Do not infer confidential
profile fields, invent a roster, or duplicate IAM role tables in Department. The
profile and Headship requirements remain open dependencies. The current academic
view uses the verified programme, batch and published timetable; the unavailable and
request-error states now render explicitly. These choices need a concrete scope
decision before they can be treated as accepted omissions by the course reviewer.

The added throttle registration is in the shared setting explicitly allowed by the
review prompt. Browser accounts are new entries only. No protected gate, shared
authentication spec, auth implementation or review prompt was changed.

## Findings and evidence

| Finding | Builder response | Remaining work |
| --- | --- | --- |
| R1-01, R1-02 | Verified missing IAM contracts; retained explicit profile and role/Headship dependencies. | Implement the external contracts or obtain named acceptance of the gaps. |
| R1-03 | Database exclusion constraints reject overlapping room, instructor and cohort intervals; upload/edit catch only the named conflict constraints. | Independent review. |
| R1-04 | All writes inherit `department_write`; reads remain unthrottled by that scope. HTTP regression proves 201 then 429. | Independent review. |
| R1-05 | Programme empty/error states added. Programme/batch/timetable remain the supported content. | Decide catalogue scope. |
| R1-06 | Expanded abbreviated identifiers; added invalid-publication, recipient-notice, privacy and approval assertions. | Complete the live-ID/alternate-flow audit, including external dependencies. |
| R1-07 | Access endpoint now has both gates. Every declared GET/POST/PUT has separate missing-module and missing-permission tests; cookie writes require CSRF. Direct student routes are refused in Chromium. | Shared shell still uses held-role navigation union; settle this platform scope. |
| R1-08 | Exhaustive table state/action refusals, permission-string drift, constant query budget at 2/20 rows, and real threaded timetable/stock issuance tests added. | Independent assessment of full domain/category coverage. |
| R1-09 | Real UI journeys now complete all 16 locally implemented use cases across Student, Faculty, Dept_Admin and HOD. | External-contract use cases and remaining alternate browser journeys. |
| R1-10 | Existing HTTP flows moved to `test_journeys.py`, with new negative journeys; role walkthrough summarized below. | Exhaustive alternate-flow audit and a complete Department keyboard-only walkthrough. |
| R1-11 | Seven workflow pages gain loading/empty/error tests; denied controls, several main actions, route permissions, and missing states are tested. Proposal type matches the API fields. | Complete per-page action matrix and independently review route-guard equivalence. |
| R1-12 | Existing membership, state and inventory refusals now give recovery guidance. | Audit the remaining DomainError strings. |
| R1-13 | One initial migration preserves all model state, stock immutability and timetable exclusions. Fresh pytest database migrations and drift check pass. | Full clean IAM + ERP install still depends on missing public-fixture academic tables. |
| R1-14 | Saved actual gate logs, coverage, test counts and five caught mutations. | Remaining walkthrough/approval evidence above. |
| R1-15 | Continuation commits describe behavior and intent. | Earlier published commit messages remain unchanged; no shared history rewrite. |

## Verification

Commands ran in the builder working tree; these are not results from an independent
review checkout. Final evidence accompanies this record:

- `make check`: [backend gates](backend-gates.log), all green.
- `make check-client`: [client gates](client-gates.log), 9 files / 77 tests, typecheck and build passed.
- `make e2e`: [browser gates](browser-gates.log), 13 passed, real IAM and portal.
- `.venv/bin/pytest modules/department --ignore=modules/department/tests/spec --cov=modules/department --cov-branch --cov-report=term-missing --cov-fail-under=90`: [91 passed; 92.74%](module-coverage.log).
- Same suite with `--cov=modules/department/domain --cov-fail-under=95`: [100%](domain-coverage.log).
- CI production-shaped environment plus local database configuration, `manage.py check --deploy --fail-level WARNING`: [no issues, 2 existing silences](deploy.log).
- [Counts by backend file](test-counts.log): announcements 10, invariants 7, journeys 18, review fixes 56.

The first run with newly authenticated browser accounts exhausted IAM's sign-in
quota and failed the existing wrong-password check with 429. With saved valid sessions,
the unchanged shared authentication tests and the full suite passed. This first-run
quota limitation remains; no application limit or shared test was weakened.

## Intentional regressions

Each mutation was applied individually, the Department suite was run, and the exact
file was restored from a copy outside the repository. The restored suite passed
91 tests. [Actual failure identifiers and final green run](mutation-results.log).

| Removed enforcement | Test that caught it |
| --- | --- |
| Department scope on lab resources, BR-DEPT-012 | `test_faculty_lab_resources_use_department_scope` |
| Endpoint permission gate | `test_every_department_method_requires_two_gates` |
| Issuance balance check, BR-DEPT-015 | `test_stock_shortage_after_approval_preserves_existing_movements`; concurrent issuance test |
| Approval before issuance, BR-DEPT-007 | `test_stock_shortage_after_approval_preserves_existing_movements` |
| Database room-overlap exclusion, BR-DEPT-010 | `test_database_excludes_overlaps_on_each_axis[room]` |

## Automated real-browser walkthrough

`client/e2e/department/workflows.spec.ts` uses the real login sessions and normal
forms. Each role's writes become visible through another role's page; no business
records are inserted directly through SQL or test-only endpoints.

| Role/journey | Observed outcome |
| --- | --- |
| Faculty → Student → HOD, UC-DEPT-002/001/003 | Publish, read relevant content, hide, confirm disappearance. |
| Dept_Admin → Faculty → HOD → Dept_Admin, UC-DEPT-019/004/005/006 | Insert stock, request, approve, issue, read issued history. |
| Student → Dept_Admin → HOD, UC-DEPT-007/008/014 | Submit confidential text, verify hidden before initial review, categorize, resolve. |
| Dept_Admin → Faculty, UC-DEPT-011/017 | Save a lab profile, read its resource details. |
| Dept_Admin → HOD, UC-DEPT-010/012 | Save general information, propose official name, approve, verify publication. |
| Dept_Admin → Student, UC-DEPT-009/018 | Publish a timetable slot, view it with the matching programme and batch. |
| Student direct entry | Inventory, requests, feedback inbox, labs and details refuse access. |

The walkthrough records uncaught page errors and API 5xx responses. During this
builder run the portal log is `/tmp/swe-lab9-r1-api.log`, and IAM log is
`/tmp/swe-lab9-r1-iam.log`. These are local synthetic-fixture logs, not a complete
per-row manual walkthrough or a production deployment record.

## Migration and next handoff

The old migration sequence was already applied locally. A replacement migration
was recorded before retiring the old files, preserving local data. A fresh database
uses `0001_initial_schema` directly. A different existing developer database with
the old migration history must transition using the old branch and the squashed
replacement before deleting old migrations; do not fake-initial against an
unverified schema. Original local files were backed up at
`/tmp/swe-lab9-r1-original-migrations/`.

Student 2's independent spec tests have not been written or edited here. Step 8
starts only after a fresh independent Step 7 review awards 10/10 in every dimension,
or the assignment's later-round pair-decision procedure applies. The submission PR
comes after Student 2's test/fix/review loop. This continuation is not that clearance.
