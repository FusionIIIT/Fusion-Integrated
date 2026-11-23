# LMS implementation quality report

## Step 8 — DEF-LMS-01 follow-up

The self-grading defect handed off by Student 2 is fixed locally on the partner's
spec baseline `600a6469438611af71c2081d2d21ffa2a7d0a503`. Owner grading mutations now return
422 / CANNOT_GRADE_OWN_SUBMISSION before any grade/audit changes. Current backend
verification: 388 LMS cases, including all 163 partner cases, passed;
module branch coverage 98.64% and domain 100%.
Both reserved spec-test directories are present from partner commits and remained
byte-for-byte unchanged by this fix. [Full defect response](DEF-LMS-01.md).

Round 3 reviewed f09c49d with 13 open findings; no 10/10 verdict or Q1 result is
claimed. This update resolves DEF-LMS-01 only. The remainder below is the historical
Round 2 correction record, retained as evidence of that earlier revision.

## Historical Round 2 correction record

Record date: 23 November 2026 (IST). Scope: Student 1 builder corrections after
completed Round 2 on `92b4ed5f563494c372bd543af4fb5bbc4ea6505a`.

**Historical status:** all 17 Round 2 findings have corresponding builder corrections
below. The corrected revision has not had a subsequent independent review.
PR #628 remains draft. Step 8 remains on hold, and neither reserved spec-test
directory has been created or touched. No independent final score is claimed.

## Approved basis and shared changes

Paired approver Vedha approved blueprint A9-LMS-BP-0.2 at documentation commit
`fca2636c8b92c9312acbfa25d59c4fd636b47ba9` on 22 November 2026:

> I formally approve Blueprint A9-LMS-BP-0.2 (commit
> fca2636c8b92c9312acbfa25d59c4fd636b47ba9) and authorize Student 1 to proceed
> with Stage B LMS application implementation.

Original approved blueprint SHA-256:
`f053725ae7f6b25b1e8e8c457c176209f9b954e562c1783c318512d9eb8c5d39`.
Policy record SHA-256:
`80f98063d05be3df3fa74794ca6d8b7dc5c3866fd634083e49828bb112b30b38`.
The implementation-aligned blueprint 0.3 records actual code locations, without
claiming a new human specification approval or changing the stored policy version.

The 22 November written scope authorizes the real IAM wrappers and FakeIam,
shared private writer, backend/client builder implementation, preapproved
settings/URL/Celery/import/client registrations, new browser demo accounts, and
rebuilt schema/permission artifacts. F-03 storage, F-04 edit guards and F-05 release
scheduling are adopted policies. No dependency was added or harness gate relaxed.

### Shared-file changes approval authority

The additional changes to `config/__init__.py` and `fusion_auth/views.py` were
formally approved by paired approver Vedha on 23 November 2026. The complete dated
approval wording is preserved with trailing Markdown whitespace normalized in
[Shared_Changes_Approval_Decision.md](Shared_Changes_Approval_Decision.md). The original received file has SHA-256
`2a48d1c16b1e3555da11ae1cde7f57575ee8a51a9bd0a66afffe2386ce461b7c`.
It approves the exact Celery bootstrap and exact Principal-refresh code. Its
method label says `MeView.post`; the actual existing role-switch handler is
`MeView.patch`. The approved file/diff is unchanged and implemented in that PATCH
handler; the signed original is not silently edited to correct this label.
Both shared changes have dedicated regressions.

The IAM prerequisite remains locally committed and verified at
`494160849bd101a5cb77a1b1c9f0881307079888`, parent
`d143e4e61b11a2a5e21c03355f8b784d83103b5d`. It is not an official upstream merge.
Nonstudent course associations are approved labelled synthetic fixtures, not a
claim of a production teaching feed. There are no accepted LMS specification gaps,
new dependency approvals or waivers to report.

## Round 2 correction register

The unedited completed report and raw evidence remain in the Student 1 handoff
package. The table below is a builder disposition, not an altered scorecard.
Round 2 reported 2 Blockers, 10 Majors and 5 Minors. Its scores were
10, 3, 8, 4, 10, 4, 3, 0, 3 across the nine dimensions.

| Finding | Correction and evidence |
|---|---|
| R2-01 | Dated paired approval preserved above for the two additional shared changes. |
| R2-02 | Removed the initial migration tool header and reworded ordinary manifest prose; exact mandated attribution scan is empty. No provenance was relabelled. |
| R2-03 | Human and scheduled lifecycle writes converge in locked atomic `transition_content`; append-only ContentTransitionLog persists state/release time/actor/event together. Audit failure rolls back publication. |
| R2-04 | All input serializers reject undeclared fields/non-object JSON, including empty action bodies; every write has a no-side-effect unknown-field refusal. Forged owners are rejected, never accepted/ignored. |
| R2-05 | All 17 write operations have endpoint-specific 429 refusal/state-preservation tests. Absent/repeated grade release explicitly returns 409 without extra audit. Existing permission, scope, CSRF, semantic and conflict regressions remain. |
| R2-06 | UC-LMS-015 journeys use only HTTP business operations while an actual thread worker processes ETA messages on a local memory transport. Success, withdrawal and injected processing-failure branches preserve the correct visibility. Direct task calls stay in dedicated task/unit/concurrency tests. |
| R2-07 | Five serialized real-browser rows below each retain their own matching runserver lines. Plain-user UI refusals are distinguished from successful allowed HTTP reads. |
| R2-08 | Complete response DTO fields/nullability, string submission policy version, release attribution and policy metadata; unseeded policy response now has the same full nullable contract. Acting-role choices are explicit in schema. |
| R2-09 | Teaching is mounted with every Faculty permission except course.update; details controls are absent while assignment controls remain. Removing that guard now fails the test; original source restored. |
| R2-10 | Blueprint 0.3 maps all 103 obligations to existing enforcement locations and records actual registry/nav, aggregate files, commands, APIs, implementation and review status. Approved 0.2 identity is retained. |
| R2-11 | BR-LMS-017 and UC-LMS-013 now point to Faculty-only `grading.release_grade`, rather than a grade-read selector. All 103 source/test links resolve. |
| R2-12 | Both scheduled sweeps have management commands, with idempotence regressions and deployment instructions. |
| R2-13 | Models split into aggregate files; package initializer only re-exports them. Existing business schema retained; audit added in migration 0002. |
| R2-14 | Domain refusals give actionable next steps for deadline, actor, payload, points, required instructions/date, immutable edits and state/time conflicts; no unsupported late override is implied. |
| R2-15 | Browser journey split into seven named stages preserving all actor progression and assertions. |
| R2-16 | 31 endpoint-specific typed TanStack hooks wrap shared internal read/list/write/download helpers; pages consume endpoint hooks and preserve user/role cache isolation. |
| R2-17 | Every API operation has response examples; applicable writes also have request examples. Binary responses use their actual media types. OpenAPI rebuilt and schema check passes. |

## Current verification gates

| Command/check | Current observed result |
|---|---|
| `make check` | Passed: Django/migration checks, lint, all 5 import contracts, no cross-module FK, plural contracts, nav, manifest, schema and whole platform suite. 634 tests collected. |
| `make check-client` | Passed: both TypeScript projects, 59 client tests, production build. |
| `make e2e` | 17 passed in 55.8 seconds against this checkout, real IAM/API and Redis worker. Includes existing auth/shell/Placement tests. |
| Module coverage command below | 209 passed; 98.64% branch-aware production module coverage, floor 90%. |
| Domain coverage command below | 209 passed; 100.00% branch-aware pure domain coverage, floor 95%. |
| Production deployment check | Passed with exact upstream CI environment plus DB_PASSWORD; no issues, two existing silenced checks. |
| Reference regeneration | 103 live enforcement/test links validated. |
| Fresh PostgreSQL database | Both migrations applied, rolled back and reapplied; missing setup named; 3,686 workspaces initialized; readiness passed. |
| Fresh browser | Actual Student course read passed; cookie-authenticated write without CSRF returned 403. |
| Role walkthrough | Five real browser rows below, including plain Student direct-route refusal and Observer hidden controls. |
| Keyboard course flow | Tab/arrow/Enter navigation, course selection and TA announcement posting passed. |
| Teaching guard mutation | New mounted-control regression fails when guard is removed; original source bytes restored. |

```
.venv/bin/pytest modules/lms --ignore=modules/lms/tests/spec --cov=modules/lms --cov-branch --cov-report=term-missing --cov-fail-under=90
.venv/bin/pytest modules/lms --ignore=modules/lms/tests/spec --cov=modules/lms/domain --cov-branch --cov-report=term-missing --cov-fail-under=95
```

Coverage excludes tests and migrations. The three lazy page chunks remain below
150 KB gzip. The shared entry still emits the existing Vite size warning, without
failing the build. No test is skipped, marked expected-failure or made exclusive.
All gates use the supplied test settings and harness without blanket role bypasses.

Selected real gate output:

```text
Contracts: 5 kept, 0 broken.
no cross-module foreign keys
all contract getters are plural
nav items and client routes agree
permission manifest matches the registries
openapi schema matches the code
Tests 59 passed (59)
17 passed (55.8s)
Required test coverage of 90% reached. Total coverage: 98.64%
Required test coverage of 95% reached. Total coverage: 100.00%
System check identified no issues (2 silenced).
```

## Behavioral and adversarial coverage

HTTP journeys cover course access/details, material organization/publication,
conditional TA announcements and audience reads, assignment draft/edit/immediate
and scheduled publication/download, all submission payload types, own history,
Faculty/TA Draft grading, Faculty release and audited Released correction, and
own Released grade visibility. UC-LMS-015 adds withdrawal and processing-failure
journeys on real asynchronous worker execution. The independent specification
test phase has not begun; these are builder tests.

Negative coverage includes every route's anonymous/missing-module/missing-method
permission refusals, live offering revocation/outage and wrong acting role, foreign
IDs, peer/Observer privacy, cookie CSRF, each write's throttle/unknown-field refusal,
domain error categories, malformed link and huge order validation, both sides of
the inclusive deadline, duplicate successes and state conflicts. Refusals preserve
business state and do not consume a successful submission.

Dedicated real PostgreSQL concurrent transactions prove one successful submission,
serialized grade old/new audit, assignment-edit/submit/grade lock ordering, and
duplicate scheduled delivery idempotency. Grade/audit and publication/audit failure
probes prove rollback. Scheduled tests cover due/not-due, reschedule, withdrawal,
bad content, dispatch failure, missing IDs, bounded 50-item sweeps and repeated runs.
File tests cover private scoped downloads, byte limits, formats, hostile names and
cleanup; content is never executed or extracted. Query-budget tests compare small
and larger collections with batched identity enrichment.

Security audit: module/verb/course gates stay mandatory; active roles are not
unioned; client caches separate users/roles; server ownership/timestamps are fixed;
Students never receive peer or Draft evaluation data; TAs cannot release/correct
Released work; Observers cannot access student-specific endpoints. The client uses
escaped text, shared HTTP/CSRF and private downloads, without token storage,
unsafe HTML, arbitrary SQL or request-controlled execution. No local access-control
tables, cross-module FKs, artificial score cap or financial ledger was introduced.

## Fresh installation and operations

The host uses native PostgreSQL with a dedicated local role. The disposable fresh
database check preserves the working database and asserts that the fresh name is
absent before creating it. It applies/rolls back/reapplies both LMS migrations,
checks readiness before/after idempotent IAM synchronization, and starts an isolated
API on 8012 plus temporary client proxy on 5183 for the first browser action/CSRF
proof. The temporary processes/database are removed in a finally block. The
committed client proxy and browser harness are unchanged.

```text
Applying lms.0001_initial... OK
Applying lms.0002_contenttransitionlog... OK
CommandError: Run manage.py sync_lms_workspaces after the IAM catalogue sync.
Initialized 3686 new LMS workspaces.
LMS prerequisites satisfied.
Fresh browser: My Courses -> linked workspace opened; cookie write without CSRF: 403.
Fresh migration rollback/reapply, readiness and browser verification passed.
```

Setup: configure synthetic DB/IAM credentials and private storage, migrate, run
`sync_lms_workspaces`, seed modules/permission manifest into IAM, then run
`check_lms_ready`. Start API, client, Celery worker and beat. Beat merges the two
60-second / 50-item sweeps; ETA dispatch happens after commit. The supplied dev
settings force eager mode, so real-worker verification uses an external settings
overlay changing only CELERY_TASK_ALWAYS_EAGER to false. No test setting was edited.

Operator replay commands (each tested twice on an empty due set):

```
.venv/bin/python manage.py release_due_materials
.venv/bin/python manage.py release_due_assignments
```

Each prints zero released rows when no work is due and uses the ordinary locked
transition/audit path. Both commands are safe to repeat. Worker failure leaves
scheduled content private; the catch-up sweep retries due content after recovery.

## Browser walkthrough with row-specific request evidence

These rows are serialized, read-only UI replays after the full successful E2E
journey, using synthetic fixture accounts. Every block contains that row's actual
runserver lines captured from a fresh journal cursor. The selected workspace is
the account's first associated course and need not be the shared demo offering.
The full E2E journey separately covers writes and all three submission variants.

| Role/account | Walkthrough | Observed result |
|---|---|---|
| Faculty / fac00021 | UC-LMS-001 and common-content reads in workspace 1 | Passed; Opened actual assigned course, details and common-content panels |
| Student / stu03009 | UC-LMS-001 and common-content reads in workspace 3607 | Passed; Opened actual assigned course, details and common-content panels |
| TA / stu03008 | UC-LMS-001 and common-content reads in workspace 1 | Passed; Opened actual assigned course, details and common-content panels |
| Observer / stf00001 | UC-LMS-001 and common-content reads in workspace 1 | Passed; Opened actual assigned course, details and common-content panels; No assignment or announcement write controls |
| Ordinary Student / stu00001 | UC-LMS-001 and common-content reads in workspace 3506 | Passed; Opened actual assigned course, details and common-content panels; Teaching/grading direct routes refused by UI guard; unauthorized pages did not mount |

### Faculty / `fac00021`

```text
[23/Nov/2026 01:17:40] "GET /api/v1/me HTTP/1.1" 200 1195
[23/Nov/2026 01:17:40] "GET /api/v1/lms/courses/ HTTP/1.1" 200 1719
[23/Nov/2026 01:17:41] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 1677
[23/Nov/2026 01:17:41] "GET /api/v1/lms/courses/1/announcements/ HTTP/1.1" 200 1654
[23/Nov/2026 01:17:41] "GET /api/v1/lms/courses/1/assignments/ HTTP/1.1" 200 8084
[23/Nov/2026 01:17:41] "GET /api/v1/lms/courses/1/materials/ HTTP/1.1" 200 3279
```

### Student / `stu03009`

```text
[23/Nov/2026 01:17:42] "GET /api/v1/me HTTP/1.1" 200 1521
[23/Nov/2026 01:17:42] "GET /api/v1/lms/courses/ HTTP/1.1" 200 9009
[23/Nov/2026 01:17:43] "GET /api/v1/lms/courses/3607/ HTTP/1.1" 200 345
[23/Nov/2026 01:17:43] "GET /api/v1/lms/courses/3607/assignments/ HTTP/1.1" 200 42
[23/Nov/2026 01:17:43] "GET /api/v1/lms/courses/3607/grades/ HTTP/1.1" 200 42
[23/Nov/2026 01:17:43] "GET /api/v1/lms/courses/3607/materials/ HTTP/1.1" 200 42
[23/Nov/2026 01:17:43] "GET /api/v1/lms/courses/3607/announcements/ HTTP/1.1" 200 42
```

### TA / `stu03008`

```text
[23/Nov/2026 01:17:44] "GET /api/v1/me HTTP/1.1" 200 1674
[23/Nov/2026 01:17:44] "GET /api/v1/lms/courses/ HTTP/1.1" 200 1714
[23/Nov/2026 01:17:44] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 1672
[23/Nov/2026 01:17:45] "GET /api/v1/lms/courses/1/announcements/ HTTP/1.1" 200 1654
[23/Nov/2026 01:17:45] "GET /api/v1/lms/courses/1/assignments/ HTTP/1.1" 200 8084
[23/Nov/2026 01:17:45] "GET /api/v1/lms/courses/1/materials/ HTTP/1.1" 200 3279
```

### Observer / `stf00001`

```text
[23/Nov/2026 01:17:46] "GET /api/v1/me HTTP/1.1" 200 601
[23/Nov/2026 01:17:46] "GET /api/v1/lms/courses/ HTTP/1.1" 200 1721
[23/Nov/2026 01:17:46] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 1679
[23/Nov/2026 01:17:46] "GET /api/v1/lms/courses/1/announcements/ HTTP/1.1" 200 1654
[23/Nov/2026 01:17:46] "GET /api/v1/lms/courses/1/materials/ HTTP/1.1" 200 3279
```

### Ordinary Student / `stu00001`

```text
[23/Nov/2026 01:17:47] "GET /api/v1/me HTTP/1.1" 200 1521
[23/Nov/2026 01:17:48] "GET /api/v1/lms/courses/ HTTP/1.1" 200 9006
[23/Nov/2026 01:17:48] "GET /api/v1/lms/courses/3506/ HTTP/1.1" 200 360
[23/Nov/2026 01:17:48] "GET /api/v1/lms/courses/3506/assignments/ HTTP/1.1" 200 42
[23/Nov/2026 01:17:48] "GET /api/v1/lms/courses/3506/grades/ HTTP/1.1" 200 42
[23/Nov/2026 01:17:48] "GET /api/v1/lms/courses/3506/announcements/ HTTP/1.1" 200 42
[23/Nov/2026 01:17:48] "GET /api/v1/lms/courses/3506/materials/ HTTP/1.1" 200 42
[23/Nov/2026 01:17:48] "GET /api/v1/me HTTP/1.1" 200 1521
[23/Nov/2026 01:17:48] "GET /api/v1/me HTTP/1.1" 200 1521
```

For the plain Student, direct Teaching/Grading visits display “Not available to
your role” with no page controls. The UI guard prevents protected module requests;
the actual session/read requests above return 200. No fictitious backend 403 is
ascribed to a client route guard. Backend method-permission 403s are separately
tested on every endpoint. Observer read replay omits assignment/submission/grade
requests and exposes no write controls.

## Review history and remaining handoff

- Round 1 on cdd8de9 was interrupted before a final scorecard. Three validation
  errors were fixed in 92b4ed5 with 12 regression cases.
- Round 2 on 92b4ed5 completed with 17 findings. Its complete unedited report has
  SHA-256 `d98a72ce9d0d1ee20fbffe08cdf0c8ee14b4cbe91ace6aad8a9818af6cdd6438`
  and is retained in the handoff package with raw review evidence.
- This corrective builder revision has current successful gates, not a completed
  independent verdict. The user chose to update the existing draft PR without
  opening the next independent review now.
- The remaining Step 7 gate is a fresh independent review after the last code
  change, preserving its unedited nine-dimension scorecard. Only a genuine 10/10
  revision unlocks the partner's Step 8 design/automation/testing work. Collaborator
  push access must also be confirmed before that handoff. Neither reserved
  specification-test directory belongs to this builder correction.
