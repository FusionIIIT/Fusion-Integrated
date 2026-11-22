# LMS implementation quality report

## Validation follow-up — 23 November 2026

The original builder snapshot below describes commit
`cdd8de9fb7caf83cb9f80f4cf9792cabc1874ca6`. The first independent review attempt
on that revision was interrupted by the platform before returning a scorecard.
It therefore produced no final verdict or nine-dimension scores.

Three application input-validation failures reported during that attempt have now
been corrected: section and material order inputs are bounded by the verified
PostgreSQL PositiveIntegerField range, 0 through 2,147,483,647; values outside it
return 400 before writes. Malformed link parsing now becomes a domain validation
response, 422, rather than an unhandled exception. Rejected edits preserve stored
values, and an invalid submission link consumes no successful submission attempt.

Twelve new regression cases cover create/edit refusal, supported ordering
boundaries, malformed material and submission links, and a later valid submission.
Current verification: `make check` passes with 593 platform cases collected;
168 LMS cases pass with 99.05% module branch coverage and 100% domain branch
coverage; `make check-client` passes with 58 cases and a production build;
`make e2e` passes all 17 browser cases. OpenAPI and the 103 source links were
regenerated and checked. No dependency, registration, authorization policy or
Student 2 specification-test file changed in this follow-up.

Step 7 is still incomplete. Builder checks and corrected partial findings are not
an independent approval or a replacement for an unedited completed scorecard.
The remaining sections retain the original builder evidence as historical context.

Record date: 22 November 2026. Scope: the Student 1 builder implementation on
`module/lms`. Independent review has not yet occurred; no 10/10 scorecard is claimed.
Student 2 specification-test folders were neither created nor edited.

## Approved basis and shared changes

The approved documentation revision is
`fca2636c8b92c9312acbfa25d59c4fd636b47ba9`, blueprint A9-LMS-BP-0.2,
SHA-256 `f053725ae7f6b25b1e8e8c457c176209f9b954e562c1783c318512d9eb8c5d39`.
The policy record SHA-256 is
`80f98063d05be3df3fa74794ca6d8b7dc5c3866fd634083e49828bb112b30b38`.
The IAM revision is `494160849bd101a5cb77a1b1c9f0881307079888`.

The dated written approval supplied by the paired reviewer states:
> I formally approve Blueprint A9-LMS-BP-0.2 (commit
> fca2636c8b92c9312acbfa25d59c4fd636b47ba9) and authorize Student 1 to proceed
> with Stage B LMS application implementation.

The 22 November authorization explicitly includes IAM client wrappers and FakeIam,
the private `core/files/writers.py` extension, the LMS backend and client, builder
tests, settings/URL/Celery/import-linter/client registrations, new browser accounts,
and regenerated API and permission artifacts. It adopts F-03 upload validation,
F-04 assignment-edit guards and F-05 release scheduling. The generated permission
catalog is regenerated with the manifest. No new dependency was added.

Two additional shared integration corrections were presented separately:

- `fusion_auth/views.py`: after changing the IAM role, resolve and return the
  updated Principal. The 22 November user response was: “Yes, apply and test the
  shared fix”. A regression verifies selected-role permissions, an unheld-role
  refusal, expired sessions and IAM outages.
- `config/__init__.py`: initialize the configured Celery app for HTTP processes.
  The exact three-line bootstrap and a fresh-process regression were presented;
  the 22 November response directed: “complete whatever you are doing its time
  to submit”. A local settings overlay, outside the repository, disables the
  supplied development eager-task override for real Redis-worker verification.

There are no accepted specification gaps recorded for the LMS behavior. Synthetic
nonstudent associations are the explicitly approved local integration fixture,
not a claim of a production authoritative teaching feed. No waiver or independent
review score has been invented.

## Gate results

| Gate | Observed result |
|---|---|
| `make check` | Passed: system/migration checks, lint, five import contracts, FK/contract/navigation checks, manifest, schema, whole platform tests |
| Platform collection | 581 tests |
| `make check-client` | Type checks, 58 tests across 10 files, production build passed |
| `make e2e` | 17 passed, including the existing platform and Placement suites |
| LMS builder suite | 156 passed; 99.05% branch-aware coverage |
| Pure domain | 100% branch-aware coverage; required floor 95% |
| Production deploy check | No issues, with the two pre-existing silenced checks |
| Teaching reference | 103 live enforcement/test links validated |
| Five rule mutations | Five killed; original file bytes restored |
| Disposable fresh database | Migration rollback/reapply, setup/readiness, browser read and missing-CSRF refusal passed |
| Keyboard course flow | Tab/arrow/Enter navigation and TA announcement posting passed |

No tests or migrations appear in the measured production coverage. The module's
three lazy page chunks are 1.65 KB, 2.31 KB and 2.95 KB gzip, each below 150 KB.
Vite also prints its existing shared-entry size warning; it does not fail the build.

### Commands and actual output

`make check`

```text
permission manifest matches the registries
make schema-check
make[1]: Entering directory '/home/denish/fusion-assignment9/Fusion-Integrated'
openapi schema matches the code
make[1]: Leaving directory '/home/denish/fusion-assignment9/Fusion-Integrated'
.venv/bin/python -m pytest -q
........................................................................ [ 12%]
........................................................................ [ 24%]
........................................................................ [ 37%]
........................................................................ [ 49%]
........................................................................ [ 61%]
........................................................................ [ 74%]
........................................................................ [ 86%]
............................................. [ 94%]
................................                                         [100%]
```

`make check-client`

```text
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rollupOptions.output.manualChunks to improve chunking: https://rollupjs.org/configuration-options/#output-manualchunks
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
✓ built in 7.61s
```

`make e2e`

```text
  ✓  17 [chromium] › e2e/shell.spec.ts:6:3 › shell › the collapsed sidebar names each module for a screen reader (1.5s)
  ✓  12 [chromium] › e2e/placement/companies.spec.ts:8:3 › placement: companies › a placement officer registers a company and sees it pending approval (6.0s)
  ✓   7 [chromium] › e2e/lms/journeys.spec.ts:63:3 › lms: complete course journeys › UC-LMS-001 through UC-LMS-015: publication, submissions, grading and scheduled release (43.3s)

  17 passed (48.9s)
```

`pytest modules/lms --cov=modules/lms --cov-branch --cov-fail-under=90`

```text
modules/lms/services/submissions.py                         35      1      8      1    95%   53
modules/lms/services/workspaces.py                          38      0      6      0   100%
modules/lms/tasks.py                                        23      0      0      0   100%
----------------------------------------------------------------------------------------------------
TOTAL                                                      935      6    118      4    99%
Required test coverage of 90% reached. Total coverage: 99.05%
156 passed in 16.74s
```

`pytest modules/lms --cov=modules/lms/domain --cov-branch --cov-fail-under=95`

```text
modules/lms/domain/__init__.py            0      0      0      0   100%
modules/lms/domain/rules.py              44      0     28      0   100%
modules/lms/domain/state_machine.py      13      0      6      0   100%
---------------------------------------------------------------------------------
TOTAL                                    57      0     34      0   100%
Required test coverage of 95% reached. Total coverage: 100.00%
156 passed in 16.69s
```

`production manage.py check --deploy --fail-level WARNING`

```text
System check identified no issues (2 silenced).
```

The deploy check used the guide's exact production environment values plus
`PRIVATE_UPLOAD_ROOT=/tmp/check-private-uploads`; no new required production secret
or CI exception was introduced. The original test settings, gate files and browser
harness were preserved.

## Builder test inventory and journeys

| File | Collected cases |
|---|---:|
| test_celery_bootstrap | 1 |
| test_client_route_guards | 1 |
| test_concurrency | 4 |
| test_domain | 30 |
| test_files | 29 |
| test_iam_contract | 20 |
| test_journeys | 10 |
| test_privilege_escalation | 35 |
| test_refusals | 8 |
| test_schedule | 4 |
| test_setup_and_queries | 10 |
| test_shared_role_switch | 4 |

HTTP journeys map UC-LMS-001/002 to course opening/details;
003/004 to organized material creation/reading; 005/006 to announcement permission,
policy versions, timestamp and audience; 007/008/009 to Draft configuration,
publication and assignment download; 010/011 to payload/deadline/one-success and own
history; 012/013/014 to both grading actors, Draft privacy, Faculty-only release,
Student read-only feedback and audited correction; and 015 to due release,
withdrawal, stale jobs, failure handling and duplicate delivery. The generated
reference resolves the CFR/AFR/BR/workflow citations to actual assertions.

Every registered endpoint separately refuses anonymous access, a missing module
grant and a missing action permission. Additional probes cover peer/out-of-course
IDs, forged owner input, an acting role with other held designations, Observer
read/write restrictions, TA course-structure refusals, session-bound CSRF, semantic
422 responses, conflicts, unavailable IAM and write throttling. All six list
families have equal two-versus-twenty-row query budgets. Real PostgreSQL threads
exercise concurrent submissions, grading and both release sweep tasks.

## Five deliberate mutations

Each file was copied outside the repository, deliberately changed, tested and
restored byte for byte in a finally block. No reset/checkout/stash was used.

| Broken rule | Failing test |
|---|---|
| course scope | `modules/lms/tests/test_journeys.py::test_uc_lms_001_access_and_uc_lms_002_manage_details` |
| fine permission gate | `modules/lms/tests/test_privilege_escalation.py::test_every_route_refuses_anonymous_missing_permission_missing_module` |
| submission deadline | `modules/lms/tests/test_journeys.py::test_submission_at_deadline_and_late_refusal` |
| draft grade privacy | `modules/lms/tests/test_journeys.py::test_uc_lms_012_grade_uc_lms_013_release_uc_lms_014_own_grade` |
| database submission uniqueness | `modules/lms/tests/test_refusals.py::test_database_uniqueness_survives_service_bypass` |

The full restored suite passed afterward. The external evidence bundle contains
the actual failing logs and original hashes.

## Adversarial pass and security self-audit

| Question/check | Outcome |
|---|---|
| Can an actor guess an unrelated parent/child ID? | Scope-first selectors return 404; body section IDs must belong to the same workspace. |
| Can other held roles increase current authority? | Server uses only active-role grants plus matching course role; client caches include user/role. |
| Can a Student read a peer or Draft grade? | Owner filtering and Released-only selector; direct submission and grade-list refusals verified. |
| Can an Observer see Student data or write? | Common-only permissions; every registered write path refused. |
| Can a TA author structure, release grades or edit released grades? | Explicit permission and domain role checks refuse each. |
| Can retries create a second successful submission? | Assignment lock plus database uniqueness; overlapping real transactions yield one success and one conflict. |
| Can a due date shorten or points change after grading? | F-04 guards refuse with 422 and preserve the row. |
| Can a released score change without audit? | Audit failure rolls back the score; concurrent changes preserve serial before/after values. |
| Can a stale/duplicate task release withdrawn/future content? | Locked state/time re-read, repeated and concurrent task probes. |
| Can an attachment escape authorization or private storage? | Parent scope first, content/size validation, opaque paths, sanitized attachment names and no public URLs. |
| Are server-owned serializer fields writable? | Explicit output fields/read-only fields; input DTOs omit owner, state, audit and timestamps. |
| Are cookie writes protected and throttled? | Shared authentication CSRF and per-principal write throttle; safe reads do not consume that write budget. |
| Are unsafe execution/SQL paths introduced? | No request-data SQL, eval, archive extraction, notebook execution or subprocess execution. |
| Does the client render untrusted HTML or persist tokens? | Escaped text, shared HTTP/CSRF client, no dangerous HTML or token storage. |
| Are access-control tables or cross-module FKs added? | Neither; five import contracts and FK checks pass. |
| Are logs free of credentials and production data? | IDs/statuses only; the evidence package excludes environment files and saved browser sessions. |

Self-approval, spendable negative balances, approval queues and third-party
availability do not occur in this module; grading points have no invented upper
cap. These are not waived rules or substitute workflows.

## Fresh-install proof

The host uses a dedicated PostgreSQL role rather than the guide's example Docker
database container. One verification command created an absent disposable
`fusion_integrated_fresh`, ran every management command with that explicit DB_NAME,
rolled LMS migrations back and reapplied them, demonstrated the missing setup
message, then synchronized the IAM catalogue and reran readiness successfully.
The existing working database was preserved. The disposable database and servers
were removed in a finally block.

```text
Operations to perform:
  Apply all migrations: accesscontrol, auth, contenttypes, directory, lms, placement
Running migrations:
  Applying lms.0001_initial... OK
DB_NAME=fusion_integrated_fresh manage.py seed_modules
  registered placement_cell (active)
  lms: registered but NOT active — 1 prerequisite(s) unmet:
      Run manage.py sync_lms_workspaces after the IAM catalogue sync.
  registered lms (active)
2 module(s) registered
DB_NAME=fusion_integrated_fresh manage.py check_lms_ready
CommandError: Run manage.py sync_lms_workspaces after the IAM catalogue sync.
DB_NAME=fusion_integrated_fresh manage.py sync_lms_workspaces
Initialized 3686 new LMS workspaces.
DB_NAME=fusion_integrated_fresh manage.py seed_modules
  registered placement_cell (active)
  registered lms (active)
2 module(s) registered
DB_NAME=fusion_integrated_fresh manage.py check_lms_ready
LMS prerequisites satisfied.
Fresh browser: My Courses -> linked workspace opened; cookie write without CSRF: 403.
Fresh migration rollback/reapply, readiness and browser verification passed.
```

A separate backend on 8012 and a temporary local client proxy on 5183 opened
the real Student course workspace in Chromium. The cookie-authenticated write
without the CSRF header returned 403. Neither the committed Vite configuration nor
the browser harness was changed for this proof.

## Browser walkthrough and requests

All rows were exercised by the successful `client/e2e/lms/journeys.spec.ts` run;
ordinary-user and direct-route checks also use `workspaces.spec.ts`. These are
synthetic dump usernames, not production identities.

| Role/account | Use cases | Result |
|---|---|---|
| Faculty / fac00021 | 001, 002, 003, 007, 008, 012, 013 | Passed through the portal and UI forms |
| Student / stu03009 | 001, 004, 006, 009, 010, 011, 014 | Passed; all three submission payload types |
| TA / stu03008 | 001, 004, 005, 006, 012 | Passed; conditional posting and Draft grading |
| Observer / stf00001 | 001, 004, 006 | Passed; no assignment/submission/grade or write controls |
| Ordinary Student / stu00001 | 001 and forbidden direct teaching/grading routes | Passed common workspace/navigation and route guards |
| System worker | 015 | Actual Redis ETA material and assignment jobs completed; beat catch-up also executed |

Representative request lines from the verified local runtime:

```text
Nov 22 17:40:41 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:41] "GET /api/v1/lms/courses/1/assignments/ HTTP/1.1" 200 4812
Nov 22 17:40:41 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:41] "GET /api/v1/lms/courses/1/grades/ HTTP/1.1" 200 1719
Nov 22 17:40:41 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:41] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 1215
Nov 22 17:40:41 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:41] "GET /api/v1/lms/courses/ HTTP/1.1" 200 1257
Nov 22 17:40:41 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:41] "GET /api/v1/lms/assignments/13/submissions/ HTTP/1.1" 200 237
Nov 22 17:40:41 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:41] "PATCH /api/v1/lms/submissions/7/grade/ HTTP/1.1" 200 300
Nov 22 17:40:42 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:42] "GET /api/v1/lms/assignments/13/submissions/ HTTP/1.1" 200 237
Nov 22 17:40:42 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:42] "GET /api/v1/lms/courses/1/assignments/ HTTP/1.1" 200 4812
Nov 22 17:40:42 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:42] "GET /api/v1/lms/courses/1/grades/ HTTP/1.1" 200 1740
Nov 22 17:40:42 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:42] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 1215
Nov 22 17:40:42 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:42] "GET /api/v1/lms/courses/ HTTP/1.1" 200 1257
Nov 22 17:40:42 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:42] "GET /api/v1/lms/courses/ HTTP/1.1" 200 9009
Nov 22 17:40:43 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:43] "GET /api/v1/lms/courses/?cursor=cD0xNTYz HTTP/1.1" 200 8761
Nov 22 17:40:43 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:43] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 1216
Nov 22 17:40:43 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:43] "GET /api/v1/lms/courses/1/assignments/ HTTP/1.1" 200 4812
Nov 22 17:40:43 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:43] "GET /api/v1/lms/courses/1/announcements/ HTTP/1.1" 200 771
Nov 22 17:40:43 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:43] "GET /api/v1/lms/courses/1/materials/ HTTP/1.1" 200 1805
Nov 22 17:40:43 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:10:43] "GET /api/v1/lms/courses/1/grades/ HTTP/1.1" 200 1740
Nov 22 17:42:02 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:12:02] "GET /api/v1/lms/courses/ HTTP/1.1" 200 1252
Nov 22 17:42:03 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:12:03] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 1210
Nov 22 17:42:03 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:12:03] "GET /api/v1/lms/courses/1/assignments/ HTTP/1.1" 200 4812
Nov 22 17:42:03 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:12:03] "GET /api/v1/lms/courses/1/materials/ HTTP/1.1" 200 1805
Nov 22 17:42:03 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:12:03] "GET /api/v1/lms/courses/1/announcements/ HTTP/1.1" 200 771
Nov 22 17:42:03 LAPTOP-A1RJJ9N1 python[31412]: [22/Nov/2026 23:12:03] "POST /api/v1/lms/courses/1/announcements/ HTTP/1.1" 201 150
```

Keyboard verification:

```text
Keyboard-only course navigation, selection and TA announcement posting passed.
```

Scheduled task replay (each invoked twice after release):

```text
36 objects imported automatically (use -v 2 for details).

material sweep: 0 0
assignment sweep: 0 0
```

## Independent review milestone

No independent numbered review round has been completed. This is a builder record,
not a review scorecard. Independent review of the latest revision remains pending. Step 8 remains gated on the pushed revision
and its unedited nine-dimension 10/10 scorecard. No file in either Student 2
specification-test folder is part of this builder change.
