# LMS implementation quality report

Record date: 23 November 2026 (IST). Student 1 builder corrections on parent
`46a9076d483b480942b898e105f8f93c88e002e9`, branch `module/lms`.

All 13 reconciled Q1/Round 3 findings have corresponding corrections and the
verification recorded below. This is the builder's disposition; a fresh independent
Q2 review is still required. No new score or 10/10 verdict is claimed. PR #628 stays
draft. Student 2's 163 cases, frozen designs and triage files are byte-for-byte
unchanged by this correction. No failing or skipped test was removed.

## Approved basis and scope

Vedha's written Stage B approval is for A9-LMS-BP-0.2 at
`fca2636c8b92c9312acbfa25d59c4fd636b47ba9`, 22 November 2026. Original blueprint
SHA-256: `f053725ae7f6b25b1e8e8c457c176209f9b954e562c1783c318512d9eb8c5d39`;
policy SHA-256: `80f98063d05be3df3fa74794ca6d8b7dc5c3866fd634083e49828bb112b30b38`.
The implementation-aligned blueprint is a record of corrections, not a new human
approval. D-01–D-06 and F-03/F-04/F-05 remain adopted. D-07 is the later explicit
self-grading refusal ruling recorded in [DEF-LMS-01.md](DEF-LMS-01.md).

IAM prerequisite: local `494160849bd101a5cb77a1b1c9f0881307079888`, parent
`d143e4e61b11a2a5e21c03355f8b784d83103b5d`. It is not an official upstream
merge. Nonstudent associations are labelled synthetic fixtures, not a production
teaching feed. Working module/folder identifiers are pair-endorsed; separate
instructor confirmation is not claimed.

The preapproved scope includes IAM wrappers, the module-neutral private writer
(F-03), backend/client implementation, shared registrations, new browser accounts
and regenerated artifacts. The current forwarded RQ1-11 specifically requests the
writer refusal wording. No dependency or test-harness change was introduced.
Additional Celery bootstrap and Principal refresh approvals are preserved in
[Shared_Changes_Approval_Decision.md](Shared_Changes_Approval_Decision.md).
The signed text says MeView.post; the existing implemented handler is MeView.patch.
The signed record has not been rewritten to conceal that method-label mismatch.

## Q1 finding disposition

| Finding | Correction / verification | Location |
|---|---|---|
| RQ1-01 | Datetime values omit only zero seconds, preserving nonzero-second ETA precision. Real Chromium boundary cases 00/01/59 pass. | client/e2e/lms/time.ts; journeys.spec.ts |
| RQ1-02 | An unknown grade stays non-editable until the remaining grade pages are loaded. A TA cannot edit a Released grade found on a later page. | GradingPage.tsx; paginated mounted-page regressions |
| RQ1-03 | Mounted create/update controls are absent without their corresponding permission. Removing the permission expression fails both new regressions. | GradingPage.test.tsx; mutations/frontend-1.log |
| RQ1-04 | A selected-course failure renders the server error. Replacing it with Pending fails the new regression. | GradingPage.test.tsx; mutations/frontend-2.log |
| RQ1-05 | Response ChoiceFields constrain all six finite kind/state/type fields; regenerated OpenAPI matches the existing client unions. | serializers.py; test_response_enums.py |
| RQ1-06 | Direct /lms/courses visit is refused with no controls for a real module-granted actor lacking lms.course.view. | workspaces.spec.ts; iam-fixture.ts |
| RQ1-07 | All 15 UCs have role-bound browser requests matched to real HTTP log lines below; all five roles also have serialized read replays. | walkthrough.json; http-requests.log; release-worker.log |
| RQ1-08 | Per-file collected test counts and five actual backend mutation failures are restored below, with exact commands and failing test identities. | collection tables and mutation table |
| RQ1-09 | Course-home display points to Workspace; student assignment download points to AssignmentDownloadAPI. Other publication/read mismatches also corrected. | ops/docs/lms_reference.py; lms-reference.md |
| RQ1-10 | Inventory delegates grouping, entry selection and link rendering to small helpers. | ops/docs/lms_reference.py |
| RQ1-11 | Duplicate submission and private-storage refusals tell the user what to do next. No unsupported resubmission exemption is promised. | services/submissions.py; core/files/writers.py |
| RQ1-12 | Handled release validation uses a bounded warning with kind/ID/action, no traceback or payload. Regression asserts exc_info is absent. | tasks.py; test_schedule.py |
| RQ1-13 | One complete 0001_initial includes transition audit. Fresh rollback/reapply and readiness pass; existing business-row digests are unchanged. | migrations/0001_initial.py; fresh-install.log |

## Current verification gates

| Gate | Actual result |
|---|---|
| `DJANGO_SETTINGS_MODULE=config.settings.test make check` | Passed; 819 platform cases collected; supplied test settings and gates unchanged. |
| Builder module coverage (spec folders excluded) | 231 passed; 98.65% branch-aware module coverage; pure domain has zero missing lines or branches (100%). |
| Partner spec suites | FR 51, UC 47, BR 45, WF 20: 163 passed. |
| All LMS collection | 394 = 231 builder + 163 partner cases. |
| `make check-client` | Both TypeScript projects, 65 tests in 10 files and production build passed. |
| Production deployment | Exact upstream CI deployment environment plus local DB_PASSWORD; no issues, two existing silenced checks. |
| `make e2e` | 19 passed, default 8 workers, real IAM/API/Redis/Celery; includes platform auth/shell/Placement cases. |
| Browser walkthrough | 15 live UCs and five real role/account replays; keyboard-only course selection and TA posting passed. |
| Fresh installation | One initial migration applied, rolled back, reapplied; readiness failed before sync and passed after 3,686 workspaces initialized; browser read passed and CSRF-less write returned 403. |
| Mutation checks | Five backend and two frontend mutants failed the expected assertions; original bytes restored and targeted tests passed afterward. |
| Reference | 103 unique live IDs have resolving actual enforcement and builder-test anchors. |

Reproduction (use the supplied test settings, not development settings):

```sh
DJANGO_SETTINGS_MODULE=config.settings.test make check
make check-client
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/pytest modules/lms --ignore=modules/lms/tests/spec -o addopts= -q --cov=modules/lms --cov-branch --cov-report=term-missing --cov-fail-under=90
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/pytest modules/lms --ignore=modules/lms/tests/spec -o addopts= -q --cov=modules/lms/domain --cov-branch --cov-fail-under=95
.venv/bin/python ops/docs/lms_reference.py
make e2e
```

Coverage excludes tests and migrations. Domain 100% is computed from the same
branch-aware builder run, without counting specification cases. LMS lazy chunks
gzip sizes: Grading 1.74 KB, Courses 2.29 KB, Teaching 2.97 KB. The existing shared
entry emits the Vite size warning; build succeeds. No skip, xfail, exclusive test,
blanket authorization bypass or weakened supplied harness was added.

Verification logs are in [builder-evidence/q1/](builder-evidence/q1/); the local
evidence-workspace path and trailing whitespace are normalized in copied output; original logs are
retained locally. Counts below come from
actual collected node IDs and the successful client run, rather than the forwarded
Q1 narrative's inconsistent 832-case figure.

## Test counts per file

| Backend LMS file | Collected cases | Owner |
|---|---:|---|
| `modules/lms/tests/spec/br/test_br_spec.py` | 45 | Student 2 |
| `modules/lms/tests/spec/fr/test_fr_spec.py` | 51 | Student 2 |
| `modules/lms/tests/spec/uc/test_uc_spec.py` | 47 | Student 2 |
| `modules/lms/tests/spec/wf/test_wf_spec.py` | 20 | Student 2 |
| `modules/lms/tests/test_celery_bootstrap.py` | 1 | Builder |
| `modules/lms/tests/test_client_route_guards.py` | 1 | Builder |
| `modules/lms/tests/test_concurrency.py` | 4 | Builder |
| `modules/lms/tests/test_domain.py` | 30 | Builder |
| `modules/lms/tests/test_files.py` | 29 | Builder |
| `modules/lms/tests/test_grading_conflicts.py` | 16 | Builder |
| `modules/lms/tests/test_http_scheduling.py` | 4 | Builder |
| `modules/lms/tests/test_iam_contract.py` | 20 | Builder |
| `modules/lms/tests/test_journeys.py` | 9 | Builder |
| `modules/lms/tests/test_privilege_escalation.py` | 35 | Builder |
| `modules/lms/tests/test_refusals.py` | 8 | Builder |
| `modules/lms/tests/test_response_enums.py` | 6 | Builder |
| `modules/lms/tests/test_review_regressions.py` | 38 | Builder |
| `modules/lms/tests/test_schedule.py` | 4 | Builder |
| `modules/lms/tests/test_setup_and_queries.py` | 10 | Builder |
| `modules/lms/tests/test_shared_role_switch.py` | 4 | Builder |
| `modules/lms/tests/test_validation_errors.py` | 12 | Builder |

| Client file | Passing cases |
|---|---:|
| `client/src/app/LoginPage.test.ts` | 17 |
| `client/src/auth/RequireAuth.test.tsx` | 4 |
| `client/src/auth/RequirePermission.test.tsx` | 2 |
| `client/src/lib/download.test.ts` | 10 |
| `client/src/modules/lms/api/hooks.test.tsx` | 4 |
| `client/src/modules/lms/pages/CoursesPage.test.tsx` | 6 |
| `client/src/modules/lms/pages/GradingPage.test.tsx` | 11 |
| `client/src/modules/lms/pages/TeachingPage.test.tsx` | 6 |
| `client/src/modules/placement/api/hooks.test.tsx` | 4 |
| `client/src/modules/placement/pages/CompaniesPage.test.tsx` | 1 |

## Broken-on-purpose rules and catching tests

Each mutation was applied to the real source, executed, and restored in a finally
block with SHA-256 equality checked. Backend mutations ran under
`DJANGO_SETTINGS_MODULE=config.settings.test`. Each command exited 1 with the
listed assertion failure, not an import/setup error. Restored targeted backend
and GradingPage suites passed. The schema uniqueness mutation changes the actual
initial migration used to create the isolated test database.

| Rule temporarily broken | Exact command | Observed failing test(s) | Raw output |
|---|---|---|---|
| course offering scope | `.venv/bin/pytest modules/lms/tests/test_journeys.py::test_uc_lms_001_access_and_uc_lms_002_manage_details --maxfail=1 --tb=short` | FAILED modules/lms/tests/test_journeys.py::test_uc_lms_001_access_and_uc_lms_002_manage_details | [log](builder-evidence/q1/mutations/backend-1.log) |
| action permission | `.venv/bin/pytest modules/lms/tests/test_privilege_escalation.py::test_every_route_refuses_anonymous_missing_permission_missing_module --maxfail=1 --tb=short` | FAILED modules/lms/tests/test_privilege_escalation.py::test_every_route_refuses_anonymous_missing_permission_missing_module[courses/-Courses] | [log](builder-evidence/q1/mutations/backend-2.log) |
| submission deadline | `.venv/bin/pytest modules/lms/tests/test_journeys.py::test_submission_at_deadline_and_late_refusal --maxfail=1 --tb=short` | FAILED modules/lms/tests/test_journeys.py::test_submission_at_deadline_and_late_refusal | [log](builder-evidence/q1/mutations/backend-3.log) |
| draft grade privacy | `.venv/bin/pytest modules/lms/tests/test_journeys.py::test_uc_lms_012_grade_uc_lms_013_release_uc_lms_014_own_grade --maxfail=1 --tb=short` | FAILED modules/lms/tests/test_journeys.py::test_uc_lms_012_grade_uc_lms_013_release_uc_lms_014_own_grade[faculty] | [log](builder-evidence/q1/mutations/backend-4.log) |
| submission database uniqueness | `.venv/bin/pytest modules/lms/tests/test_refusals.py::test_database_uniqueness_survives_service_bypass --maxfail=1 --tb=short` | FAILED modules/lms/tests/test_refusals.py::test_database_uniqueness_survives_service_bypass | [log](builder-evidence/q1/mutations/backend-5.log) |
| grading control permission | `npm test -- src/modules/lms/pages/GradingPage.test.tsx` | FAIL  src/modules/lms/pages/GradingPage.test.tsx > GradingPage > hides a mounted grading form without grade.create<br>FAIL  src/modules/lms/pages/GradingPage.test.tsx > GradingPage > hides a mounted grading form without grade.update | [log](builder-evidence/q1/mutations/frontend-1.log) |
| selected course error | `npm test -- src/modules/lms/pages/GradingPage.test.tsx` | FAIL  src/modules/lms/pages/GradingPage.test.tsx > GradingPage > shows a selected course detail error instead of a spinner | [log](builder-evidence/q1/mutations/frontend-2.log) |

## Browser walkthrough: every live use case

Automation: `client/e2e/lms/journeys.spec.ts` has named steps for UC-LMS-001–015,
separate real Faculty/Student/TA/Observer contexts, UI assertions, real HTTP and
real Redis-backed worker execution. Each row below selects one representative
successful request from the passing journey. The complete role-bound response
records are in [journey-requests.json](builder-evidence/q1/journey-requests.json).
Matching lines below are copied from the actual Django log, with method/path/status
and response/server times checked within four seconds; server lines alone do not
attribute the actor. The actor attribution comes from the browser context.

| UC | Actor | Observed UI result | Matching server request log |
|---|---|---|---|
| UC-LMS-001 | Faculty | Assigned course opens with syllabus, schedule and staff. | `[23/Nov/2026 16:45:27] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 2514` |
| UC-LMS-002 | Faculty | Course details publish and persist. | `[23/Nov/2026 16:45:29] "PATCH /api/v1/lms/courses/1/ HTTP/1.1" 200 2514` |
| UC-LMS-003 | Faculty | Section and NOTE material are created; material is scheduled. | `[23/Nov/2026 16:45:33] "POST /api/v1/lms/courses/1/materials/ HTTP/1.1" 201 238` |
| UC-LMS-004 | Student | Published scheduled note becomes visible to the Student. | `[23/Nov/2026 16:46:02] "GET /api/v1/lms/courses/1/materials/ HTTP/1.1" 200 6239` |
| UC-LMS-005 | TA | Policy-authorized TA posts a timestamped announcement. | `[23/Nov/2026 16:45:41] "POST /api/v1/lms/courses/1/announcements/ HTTP/1.1" 201 146` |
| UC-LMS-006 | Observer | Observer sees the common announcement without authoring controls. | `[23/Nov/2026 16:45:43] "GET /api/v1/lms/courses/1/announcements/ HTTP/1.1" 200 3129` |
| UC-LMS-007 | Faculty | TEXT, FILE and LINK assignment drafts are created. | `[23/Nov/2026 16:45:36] "POST /api/v1/lms/courses/1/assignments/ HTTP/1.1" 201 276` |
| UC-LMS-008 | Faculty | Assignments publish immediately or at the selected future release. | `[23/Nov/2026 16:45:36] "POST /api/v1/lms/assignments/56/publish/ HTTP/1.1" 200 310` |
| UC-LMS-009 | Student | Released assignment instructions download successfully. | `[23/Nov/2026 16:45:58] "GET /api/v1/lms/assignments/56/download/ HTTP/1.1" 200 115` |
| UC-LMS-010 | Student | TEXT, FILE and LINK submissions are accepted once each. | `[23/Nov/2026 16:45:58] "POST /api/v1/lms/assignments/56/submissions/ HTTP/1.1" 201 196` |
| UC-LMS-011 | Student | Own submission history/status is displayed. | `[23/Nov/2026 16:46:02] "GET /api/v1/lms/assignments/58/submissions/ HTTP/1.1" 200 241` |
| UC-LMS-012 | TA | TA records a Draft grade; release control stays absent. | `[23/Nov/2026 16:46:04] "POST /api/v1/lms/submissions/43/grade/ HTTP/1.1" 200 248` |
| UC-LMS-013 | Faculty | Faculty releases grades and corrects a released grade with audit. | `[23/Nov/2026 16:46:08] "POST /api/v1/lms/submissions/43/grade/release/ HTTP/1.1" 200 281` |
| UC-LMS-014 | Student | Own released feedback is visible; prior Draft feedback was absent. | `[23/Nov/2026 16:46:13] "GET /api/v1/lms/courses/1/grades/ HTTP/1.1" 200 7372` |
| UC-LMS-015 | Faculty | Future material/assignment releases execute in the real Celery worker and become readable. | `[23/Nov/2026 16:45:35] "POST /api/v1/lms/materials/21/publish/ HTTP/1.1" 200 265` |

UC-LMS-015 System evidence from the real worker (the scheduled content was then asserted visible in the Student UI):

```text
[2026-11-23 16:45:48,052: INFO/ForkPoolWorker-1] lms.release.transition kind=material id=21 event=release
[2026-11-23 16:45:54,026: INFO/ForkPoolWorker-1] lms.release.transition kind=assignment id=58 event=release
```

## Browser walkthrough: every role and ordinary user

These serialized replay rows use actual synthetic account sessions and each row's
own captured server lines. Automation: the builder role walkthrough following the
passing browser suite. Observer has no authoring controls; the plain Student's
Teaching/Grading visits are refused by the client guard, without mounting controls.
Those client refusals are not falsely described as backend HTTP 403 responses.
All backend routes separately have missing-verb/module/scope refusal tests.

| Role / account | Workspace | Observed result |
|---|---:|---|
| Faculty / `fac00021` | 1 | Opened actual assigned course, details and common-content panels |
| Student / `stu03009` | 3607 | Opened actual assigned course, details and common-content panels |
| TA / `stu03008` | 1 | Opened actual assigned course, details and common-content panels |
| Observer / `stf00001` | 1 | Opened actual assigned course, details and common-content panels; No assignment or announcement write controls |
| Ordinary Student / `stu00001` | 3506 | Opened actual assigned course, details and common-content panels; Teaching/grading direct routes refused by UI guard; unauthorized pages did not mount |

### Faculty / `fac00021`

```text
[23/Nov/2026 16:46:19] "GET /api/v1/me HTTP/1.1" 200 1195
[23/Nov/2026 16:46:19] "GET /api/v1/lms/courses/ HTTP/1.1" 200 2649
[23/Nov/2026 16:46:20] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 2607
[23/Nov/2026 16:46:20] "GET /api/v1/lms/courses/1/announcements/ HTTP/1.1" 200 3129
[23/Nov/2026 16:46:20] "GET /api/v1/lms/courses/1/materials/ HTTP/1.1" 200 6239
[23/Nov/2026 16:46:20] "GET /api/v1/lms/courses/1/assignments/ HTTP/1.1" 200 8096
```

### Student / `stu03009`

```text
[23/Nov/2026 16:46:21] "GET /api/v1/me HTTP/1.1" 200 1521
[23/Nov/2026 16:46:21] "GET /api/v1/lms/courses/ HTTP/1.1" 200 9009
[23/Nov/2026 16:46:22] "GET /api/v1/lms/courses/3607/ HTTP/1.1" 200 345
[23/Nov/2026 16:46:22] "GET /api/v1/lms/courses/3607/announcements/ HTTP/1.1" 200 42
[23/Nov/2026 16:46:22] "GET /api/v1/lms/courses/3607/grades/ HTTP/1.1" 200 42
[23/Nov/2026 16:46:22] "GET /api/v1/lms/courses/3607/assignments/ HTTP/1.1" 200 42
[23/Nov/2026 16:46:22] "GET /api/v1/lms/courses/3607/materials/ HTTP/1.1" 200 42
```

### TA / `stu03008`

```text
[23/Nov/2026 16:46:23] "GET /api/v1/me HTTP/1.1" 200 1674
[23/Nov/2026 16:46:23] "GET /api/v1/lms/courses/ HTTP/1.1" 200 2644
[23/Nov/2026 16:46:23] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 2602
[23/Nov/2026 16:46:23] "GET /api/v1/lms/courses/1/assignments/ HTTP/1.1" 200 8096
[23/Nov/2026 16:46:23] "GET /api/v1/lms/courses/1/materials/ HTTP/1.1" 200 6239
[23/Nov/2026 16:46:23] "GET /api/v1/lms/courses/1/announcements/ HTTP/1.1" 200 3129
```

### Observer / `stf00001`

```text
[23/Nov/2026 16:46:24] "GET /api/v1/me HTTP/1.1" 200 601
[23/Nov/2026 16:46:25] "GET /api/v1/lms/courses/ HTTP/1.1" 200 2651
[23/Nov/2026 16:46:25] "GET /api/v1/lms/courses/1/ HTTP/1.1" 200 2609
[23/Nov/2026 16:46:25] "GET /api/v1/lms/courses/1/announcements/ HTTP/1.1" 200 3129
[23/Nov/2026 16:46:25] "GET /api/v1/lms/courses/1/materials/ HTTP/1.1" 200 6239
```

### Ordinary Student / `stu00001`

```text
[23/Nov/2026 16:46:26] "GET /api/v1/me HTTP/1.1" 200 1521
[23/Nov/2026 16:46:27] "GET /api/v1/lms/courses/ HTTP/1.1" 200 9006
[23/Nov/2026 16:46:27] "GET /api/v1/lms/courses/3506/ HTTP/1.1" 200 360
[23/Nov/2026 16:46:27] "GET /api/v1/lms/courses/3506/assignments/ HTTP/1.1" 200 42
[23/Nov/2026 16:46:27] "GET /api/v1/lms/courses/3506/grades/ HTTP/1.1" 200 42
[23/Nov/2026 16:46:27] "GET /api/v1/lms/courses/3506/announcements/ HTTP/1.1" 200 42
[23/Nov/2026 16:46:27] "GET /api/v1/lms/courses/3506/materials/ HTTP/1.1" 200 42
[23/Nov/2026 16:46:27] "GET /api/v1/me HTTP/1.1" 200 1521
[23/Nov/2026 16:46:27] "GET /api/v1/me HTTP/1.1" 200 1521
```

The additional direct `/lms/courses` test uses `stf00003`, a synthetic staff account
assigned the existing placement_officer designation. Its temporary IAM coarse LMS
module grant has source `e2e:lms-course-refusal`, no LMS verb permission, and is
removed in finally if created by that test. The real CSRF-protected role-switch
endpoint refreshes the saved session after the fixture change. The test checks
both module presence and missing lms.course.view, then requires NotPermitted with
zero page buttons. Existing actor roles are never stripped to force a refusal.

## Installation, migration and operations

One complete unmerged `0001_initial.py` now includes all business and append-only
lifecycle audit models. For the existing local development database, only the
obsolete 0002 migration-recorder row was removed after verifying the matching audit
table already existed; no physical business table was dropped or recreated.
Before/after sorted-row SHA-256 digests match for all 11 LMS tables and 7,620 rows
at the consolidation checkpoint (before later browser fixtures). Digest evidence
is committed; business row contents and database dumps are not.

The disposable fresh database was required to be absent before creation. It was
migrated, rolled back to LMS zero, reapplied, synchronized, checked and exercised
through a real Student browser on isolated ports 8012/5183. Cleanup removes only
that newly created database and owned processes. See [fresh-install.log](builder-evidence/q1/fresh-install.log).

Configure synthetic DB/IAM credentials, private storage outside web root and Redis.
Run migrate, seed_modules, sync_lms_workspaces and check_lms_ready, and seed the
committed permission manifest in IAM. Start API, client, Celery worker and beat.
Real-worker verification uses an external overlay changing only
CELERY_TASK_ALWAYS_EAGER to false; supplied dev/test settings remain unchanged.
The post-commit ETA dispatch and 60-second, 50-item catch-up sweeps converge on the
same locked, audited transition. These replay commands are idempotent:

```sh
.venv/bin/python manage.py release_due_materials
.venv/bin/python manage.py release_due_assignments
```

These runs use native PostgreSQL and real Redis. Docker Compose itself was not
reverified; no claim of a successful Docker gate is made.

## Behavioral coverage and remaining review

HTTP journeys cover all live use cases, successful submission variants, own
history, publication/download, Draft grading, Faculty release and audited correction.
Adversarial cases include missing module/verb/scope, peer/Observer privacy, CSRF,
throttling, undeclared fields, payload/storage refusals, duplicate/conflicting work,
deadline bounds and offering revocation. PostgreSQL concurrency tests cover locks,
one-success uniqueness, audit rollback and duplicate scheduling. Query budgets
cover batched identity enrichment. Logs omit handled validation tracebacks.

Round 1 was interrupted. Round 2 had 17 findings corrected in f09c49d. Round 3 on
f09c49d had 13 findings, with scores 10/10/8/6/10/0/1/3/10. The self-grading
defect was separately fixed in 37557a2. The reconciled Q1 notice on 46a9076 correctly
retained those 13 findings; its prior premature all-10 claim is not adopted here.
This revision supplies the corresponding corrections, not an independent verdict.

Next: Vedha/fresh independent reviewer should review the new correction commit
as Q2, preserve the unedited scorecard, and rerun the partner suites. Keep PR #628
draft until an actual independent review establishes zero open findings. No score
is prefilled and no partner-owned test/design/triage file is edited by Student 1.
