# Placement Cell: quality report

This report is the evidence for the `placement` module on branch `module/placement`.
Every number below comes from a run made on 2026-11-20, after the last code change.
The environment is `module-only`, so the real-portal check (Step 6.6) does not apply.
All accounts named here are synthetic accounts from `fusion-dev.dump`.

## 1. Gates

`make check` exit 0.
It runs `manage.py check`, the migration check, `ruff`, `lint-imports`, the three `ops/checks/` scripts, `permission_manifest --check`, `schema-check` and 595 backend tests.
Last lines:

```text
Contracts: 4 kept, 0 broken.
no cross-module foreign keys
all contract getters are plural
nav items and client routes agree
permission manifest matches the registries
openapi schema matches the code
```

`make check-client` exit 0, read after `tsc` finished.

```text
> tsc --noEmit && tsc --noEmit -p e2e
 Test Files  20 passed (20)
      Tests  100 passed (100)
> tsc -b && vite build
✓ built in 2.09s
```

The largest placement chunk in the build is `PostingsPage` at 4.53 kB gzip, under the 150 kB limit.

`make e2e` exit 0, with the IAM and `make dev` running, from a cold start with no saved sessions:

```text
  27 passed (1.2m)
```

## 2. Coverage

```text
$ .venv/bin/pytest modules/placement --cov=modules/placement --cov-branch --cov-report=term-missing --cov-fail-under=90
TOTAL    4003    230    842    137    92%
Required test coverage of 90% reached. Total coverage: 92.01%

$ .venv/bin/pytest modules/placement --cov=modules/placement/domain --cov-branch --cov-report=term-missing --cov-fail-under=95
TOTAL     555     17    202     17    96%
Required test coverage of 95% reached. Total coverage: 95.51%
```

Neither report lists a file under `tests/` or `migrations/`.

## 3. Test counts

34 files, 530 tests in `modules/placement/tests`:

| File | Tests |
|---|---|
| `test_adversarial_pass.py` | 18 |
| `test_alumni_access.py` | 10 |
| `test_api.py` | 11 |
| `test_audit.py` | 12 |
| `test_bulk_actions.py` | 15 |
| `test_clearance.py` | 30 |
| `test_client_route_guards.py` | 2 |
| `test_company_registration.py` | 8 |
| `test_conduct.py` | 27 |
| `test_conduct_and_registration_api.py` | 9 |
| `test_cpi_directory.py` | 9 |
| `test_documents_api.py` | 8 |
| `test_domain.py` | 12 |
| `test_eligibility_rules.py` | 27 |
| `test_exports.py` | 16 |
| `test_notification_worker.py` | 21 |
| `test_offer_flow.py` | 23 |
| `test_offer_policy.py` | 44 |
| `test_office_operations.py` | 14 |
| `test_operator_commands.py` | 13 |
| `test_posting_edits.py` | 19 |
| `test_privilege_escalation.py` | 12 |
| `test_query_budgets.py` | 6 |
| `test_record_maintenance.py` | 15 |
| `test_recruiter_isolation.py` | 36 |
| `test_registration.py` | 21 |
| `test_reports.py` | 10 |
| `test_schedule.py` | 8 |
| `test_scheduled_work_status.py` | 3 |
| `test_spec_actor_goals.py` | 19 |
| `test_spec_journeys.py` | 24 |
| `test_stats.py` | 4 |
| `test_two_gates.py` | 22 |
| `test_write_throttle.py` | 2 |

Journey tests in `test_spec_journeys.py` map to the workflows and use cases as follows.

| Test | Workflow | Use cases |
|---|---|---|
| `test_bw_pc_01_tpo_publishes_and_an_eligible_student_applies` | BW-PC-01 | PC-UC-006, PC-UC-002, PC-UC-003 |
| `test_bw_pc_02_company_publishes_directly_and_a_student_applies` | BW-PC-02 | PC-UC-015, PC-UC-003 |
| `test_bw_pc_03_company_submits_tpo_publishes_and_a_student_applies` | BW-PC-03 | PC-UC-015, PC-UC-006, PC-UC-003 |
| `test_bw_pc_04_application_to_company_shortlist` | BW-PC-04 | PC-UC-016 |
| `test_bw_pc_05_shortlist_to_tpo_scheduled_interview` | BW-PC-05 | PC-UC-009 |
| `test_bw_pc_06_company_schedules_the_interview` | BW-PC-06 | PC-UC-021 |
| `test_bw_pc_07_offer_accepted_updates_the_placement_record` | BW-PC-07 | PC-UC-022, PC-UC-005, PC-UC-010 |
| `test_bw_pc_08_offer_rejected_makes_no_placement_record` | BW-PC-08 | PC-UC-022, PC-UC-005 |
| `test_cw_pc_01` to `test_cw_pc_04` | CW-PC-01 to CW-PC-04 | the composites of the above |

The other use cases are tested by name in these files:

| Use case | Test files |
|---|---|
| PC-UC-001 | `test_documents_api.py`, `test_spec_actor_goals.py` |
| PC-UC-002, PC-UC-004, PC-UC-013, PC-UC-020, PC-UC-023 | `test_spec_actor_goals.py` |
| PC-UC-007 | `test_notification_worker.py` |
| PC-UC-008 | `test_bulk_actions.py`, `test_spec_actor_goals.py` |
| PC-UC-010 | `test_record_maintenance.py` |
| PC-UC-011, PC-UC-012 | `test_reports.py`, `test_stats.py` |
| PC-UC-014 | `test_company_registration.py`, `test_adversarial_pass.py` |
| PC-UC-017 | `test_alumni_access.py` |
| PC-UC-024 | `test_reports.py`, `test_spec_actor_goals.py` |

## 4. Five rules broken on purpose

Each file was copied outside the repository, broken, tested and copied back.
No `git checkout`, `git stash` or `git reset` was used.
The script is `~/a9/gen/break_it.sh`, outside the repository.

| Rule | What was broken | Caught by |
|---|---|---|
| PC-BR-009 scoping | the recruiter's company filter removed from `selectors/scoping.py` | 4 tests, for example `test_privilege_escalation.py::test_a_recruiter_cannot_issue_an_offer_for_another_company` |
| PC-BR-024 permission | the record-manage gate removed from the view and from `services/records.py` | 4 tests, for example `test_record_maintenance.py::TestAlumniRecords::test_an_alumnus_cannot_change_a_record` |
| BW-PC-04 transition | Submitted to Shortlisted removed from `domain/state_machine.py` | 4 tests, for example `test_office_operations.py::TestInterviewOutcomes::test_company_records_an_outcome` |
| PC-BR-013 deadline | the offer deadline check made always false | `test_spec_journeys.py::TestGuardsOnTheWorkflows::test_pc_br_013_a_response_after_the_deadline_is_refused` and one more |
| One active record | the second-active-record check removed from `services/records.py` | `test_record_maintenance.py::TestActiveFlag::test_reactivating_beside_another_active_record_is_409` |

Removing only the view's permission gate left the suite green, because the service checks the permission again.
That is why the permission row removes both layers.
After each restore, the suite was green again.

```text
scoping PC-BR-009:        4 failing (first shown)
FAILED modules/placement/tests/test_audit.py::TestHistoryScope::test_another_companys_recruiter_gets_a_404
FAILED modules/placement/tests/test_privilege_escalation.py::test_a_recruiter_cannot_issue_an_offer_for_another_company
permission PC-BR-024:        0 failing (first shown)
transition BW-PC-04:        4 failing (first shown)
FAILED modules/placement/tests/test_office_operations.py::TestInterviewOutcomes::test_company_records_an_outcome
FAILED modules/placement/tests/test_office_operations.py::TestInterviewOutcomes::test_an_unknown_candidate_is_404
deadline PC-BR-013:        2 failing (first shown)
FAILED modules/placement/tests/test_offer_flow.py::TestDeadlines::test_responding_after_the_deadline_is_refused
FAILED modules/placement/tests/test_spec_journeys.py::TestGuardsOnTheWorkflows::test_pc_br_013_a_response_after_the_deadline_is_refused
uniqueness one active record:        1 failing (first shown)
FAILED modules/placement/tests/test_record_maintenance.py::TestActiveFlag::test_reactivating_beside_another_active_record_is_409
..................................................................................................                    [100%]
permission PC-BR-024 (view gate and service check both removed): 4 failing
FAILED modules/placement/tests/test_record_maintenance.py::TestAlumniRecords::test_an_alumnus_cannot_change_a_record
FAILED modules/placement/tests/test_record_maintenance.py::TestRefusals::test_without_record_manage_a_correction_is_403_and_nothing_changes[perms0]
after restore: 0 failing
```

## 5. Adversarial pass

Each question was asked of the running module with a probe script that sends real requests as the officer and as a student.
The last three rows came from an earlier security review of the upstream module; they were confirmed still present on this branch, then fixed.
Every hole became a test in `test_adversarial_pass.py` before it was fixed.

| Question | Finding | Change |
|---|---|---|
| Can an approver approve their own record? | No. A student or coordinator cannot move their own application (`test_api.py`), alone or in bulk (`test_bulk_actions.py`). Company approval is recorded by the office for a company, not for itself. | none |
| Can a thing appear in its own approval queue? | A recruiter's submitted posting waits for the office, and the recruiter cannot publish it (`awaiting_tpo`). | none |
| Can an amount or count go negative? | **Yes, before this pass.** A posting took a CTC of -5, and an off-campus record took -3. Negative seats and a negative round capacity crashed with a 500. | Minimum values on every amount and count; 400 instead of 500. |
| Can something be back-dated? | **Yes, before this pass.** An interview round could start two days ago. Publishing with a past deadline and issuing an offer with a past deadline were already refused. | A round must start in the future and end after it starts. The date pickers no longer offer past dates. |
| Can one company exist twice? | **Yes, before this pass.** The same name registered twice made a second company with a `-2` slug, so a blacklisted company could register again. | 409 `company_exists`, backed by a unique index on the lowercased name (migration 0013). |
| Can someone act on a row outside their scope by its id? | No. Another company's application or record answers 404 (`test_recruiter_isolation.py`, `test_audit.py`). | none |
| Can a closed record still change? | No. Accepting a declined offer and moving a declined application both answer 409. | none |
| Does the same request twice take effect twice? | No. A second apply, a second offer and a second publish change nothing. | none |
| Can a cookie alone write? | No. A cookie write without `X-CSRF-Token` answers 403 and saves nothing (`test_a_cookie_write_to_the_module_without_the_csrf_token_is_403_and_changes_nothing`). | test added |
| Can a document link run script? | No. A `javascript:` link and a non-Drive link are refused. | none |
| Can a company read what is not its business? | **Yes, before this pass.** Every offer a recruiter read carried `policy_decision`, which records the student's other offers and package. | Recruiters get offers without it (`test_a_recruiter_never_sees_the_policy_decision_on_an_offer`). |
| Can a company grant itself a privilege? | **Yes, before this pass.** A recruiter could set or clear a Dream Slot, which only the placement office declares (policy rule 7). | 403 `dream_slot_office_only` (`test_a_recruiter_cannot_declare_a_dream_slot`). |
| Can a stranger lock a recruiter out? | **Yes, before this pass.** Failures were counted per email only, so fifteen wrong passwords from anywhere locked the account until an admin acted. A burst of parallel guesses could also pass the check before any failure was saved. | Failures are counted per email and address, and attempts on one account run one at a time (`test_failures_from_another_address_do_not_lock_the_recruiter_out`, `test_a_parallel_burst_of_guesses_cannot_outrun_the_lockout`). |

The probe's final run, after the fixes:

```text
posting with negative CTC: 400 {"error": {"code": "validation_error", "message": "The submitted data was not valid.", "details": [{"field": "ctc_lpa",
posting with negative seats: 400 {"error": {"code": "validation_error", "message": "The submitted data was not valid.", "details": [{"field": "seats",
posting closing in the past (create): 201 {"id": 153, "title": "Adv Role fc12c0e5", "kind": "fte", "company": {"id": 181, "name": "Adv Co c98803c5", "
  ...then publish it: 409 {"error": {"code": "deadline_in_past", "message": "The application deadline is already past.", "details": [], "request_id": 
publish: 200 {"id": 154, "title": "Adv Role fc12c0e5", "kind": "fte", "company": {"id": 181, "name": "Adv Co c98803c5", "slug": "adv-co-c98803c5", "se
publish twice: 200 {"id": 154, "title": "Adv Role fc12c0e5", "kind": "fte", "company": {"id": 181, "name": "Adv Co c98803c5", "slug": "adv-co-c98803c5
edit a published posting: 200 {"id": 154, "title": "Adv Role fc12c0e5", "kind": "fte", "company": {"id": 181, "name": "Adv Co c98803c5", "slug": "adv-
apply: 201 {"id": 105, "posting": {"id": 154, "title": "Adv Role fc12c0e5", "kind": "fte", "company": {"id": 181, "name": "Adv Co c98803c5", "slug": "
apply twice: 409 {"error": {"code": "already_applied", "message": "You have already applied to this posting.", "details": [], "request_id": "ec238808-
round starting in the past: 409 {"error": {"code": "starts_in_past", "message": "A round must start in the future.", "details": [], "request_id": "a84
round with negative capacity: 400 {"error": {"code": "validation_error", "message": "The submitted data was not valid.", "details": [{"field": "capaci
issue offer before shortlist: 409 {"error": {"code": "invalid_transition", "message": "An application cannot move from 'submitted' to 'offer_issued'."
offer back-dated deadline: 409 {"error": {"code": "deadline_in_past", "message": "The response deadline must be in the future.", "details": [], "reque
issue offer: 201 {"id": 38, "posting": {"id": 154, "title": "Adv Role fc12c0e5", "kind": "fte", "company": {"id": 181, "name": "Adv Co c98803c5", "slu
issue offer twice: 409 {"error": {"code": "offer_exists", "message": "This application already has an offer.", "details": [], "request_id": "5fb4a2cd-
decline: 200 {"id": 38, "posting": {"id": 154, "title": "Adv Role fc12c0e5", "kind": "fte", "company": {"id": 181, "name": "Adv Co c98803c5", "slug": 
accept after decline: 409 {"error": {"code": "offer_not_open", "message": "This offer is already declined.", "details": [], "request_id": "46f03dfd-7d
move a declined application: 409 {"error": {"code": "invalid_transition", "message": "An application cannot move from 'offer_declined' to 'under_revie
offer with negative CTC (new app needed: skipped): 0 {}
off-campus negative CTC: 400 {"error": {"code": "validation_error", "message": "The submitted data was not valid.", "details": [{"field": "ctc_lpa", "
off-campus record: 201 {"id": 24, "company": {"id": 181, "name": "Adv Co c98803c5", "slug": "adv-co-c98803c5", "sector": "", "sector_kind": "other", "
correct record to negative CTC: 400 {"error": {"code": "validation_error", "message": "The submitted data was not valid.", "details": [{"field": "ctc_
correct record with no reason: 400 {"error": {"code": "validation_error", "message": "The submitted data was not valid.", "details": [{"field": "reaso
off-campus record for unknown season: 409 {"error": {"code": "policy_missing", "message": "No placement policy for 1999-00.", "details": [], "request_
student reads office records: 200 {"results": []}
student corrects a record: 403 {"error": {"code": "permission_denied", "message": "You do not have permission to perform this action.", "details": [],
student publishes an announcement: 403 {"error": {"code": "permission_denied", "message": "This action needs placement.announcement.publish.", "detail
student approves a company: 403 {"error": {"code": "permission_denied", "message": "You do not have permission to perform this action.", "details": []
profile doc javascript: link: 409 {"error": {"code": "url_not_https", "message": "The link must start with https://.", "details": [], "request_id": "9
profile doc non-drive link: 409 {"error": {"code": "url_not_drive", "message": "Only Google Drive links are accepted. Share the file from Drive and pa
register company twice same name: 409 {"error": {"code": "company_exists", "message": "Adv Co c98803c5 is already registered with the placement office
write without CSRF header: 403 {"error": {"code": "permission_denied", "message": "Missing or invalid CSRF token. Send the `csrf_token` from your sess
```

## 6. Security self-audit

| Item | Result |
|---|---|
| Both gates on every view | Pass. `test_two_gates.py` refuses a user with the module grant but no placement permission on every shared view. |
| `AllowAny`, unrouted views | None found. |
| Explicit serializer fields, server-owned fields read-only | Pass. No `__all__` or `exclude`. Seventeen output serializers set `read_only_fields = fields`. |
| Reads start from `selectors/scoping.py`, body ids checked | Pass. The break of the scoping filter is caught (section 4). |
| No raw SQL, `.extra()`, `eval`, `pickle`, `yaml.load`, `subprocess` | None found. |
| File uploads | New documents are Google Drive links checked by `core.files.drive`; no new file bytes are stored. Files stored before this rebuild are served only by `DocumentDownloadView`, which checks the module grant, the permission and the caller's scope. |
| Every write has a `throttle_scope` | Pass. `test_write_throttle.py::test_every_write_view_declares_a_throttle_scope`. |
| Logs carry ids only | Pass. No log call in the module includes a name, email, roll number, token or body. |
| No stack trace, SQL or path in an error | Pass. Errors use the platform envelope; the 500s found in section 5 are fixed. |
| No loosened authentication | Three views clear `authentication_classes`: company self-registration (PC-UC-014), invite acceptance and recruiter sign-in. They are the public entry points, and each has its own per-address limit. |
| CSRF on cookie writes | Pass. Tested in the module (section 5) and in `core/tests/test_csrf.py`. |
| Client: no `dangerouslySetInnerHTML`, no token in `localStorage`, all calls through `lib/http.ts` | Pass. None found in `client/src/modules/placement` or `client/src/recruiter`. |
| New dependencies | None. |
| Deploy check with production settings | Pass: `System check identified no issues (2 silenced).` |

## 7. Fresh install

Run on a throwaway database.
The app's Postgres on this machine is the Homebrew server on port 5432, so `createdb` and `dropdb` replace `docker compose exec -T db`.

Migrate, roll the module back to zero, migrate again, seed, readiness:

```text
+(eval):1> dropdb -h 127.0.0.1 -U fusion_admin --if-exists fusion_integrated_fresh
NOTICE:  database "fusion_integrated_fresh" does not exist, skipping
+(eval):2> createdb -h 127.0.0.1 -U fusion_admin fusion_integrated_fresh
+(eval):3> DB_NAME=fusion_integrated_fresh make migrate
+(eval):3> tail -1
  Applying placement.0013_company_name_unique_ci... OK
+(eval):4> DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py migrate placement zero
+(eval):4> tail -1
  Unapplying placement.0001_initial... OK
+(eval):5> tail -1
+(eval):5> DB_NAME=fusion_integrated_fresh make migrate
  Applying placement.0013_company_name_unique_ci... OK
+(eval):6> DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py seed_modules
+(eval):6> tail -4
  placement: registered but NOT active — 1 prerequisite(s) unmet:
      No active placement season. Run `manage.py open_placement_season --season 2026-27` to open one.
  registered placement (planned)
1 module(s) registered
+(eval):7> DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py placement_readiness
CommandError: 1 prerequisite(s) unmet.
  No active placement season. Run `manage.py open_placement_season --season 2026-27` to open one.
+(eval):7> echo 'readiness exit=1'
readiness exit=1
```

Readiness names the missing season, as intended.
Then the IAM was seeded from `make permissions`, one account was granted its role, the season was opened, and readiness passed:

```text
+(eval):7> make permissions
+(eval):7> tail -1
wrote registry/permissions.json — directory: 1 permission(s), 4 designation(s), placement: 22 permission(s), 4 designation(s)
+(eval):7> cd ../Fusion_System_Administrator/Backend/backend
+(eval):7> tail -2
+(eval):7> env -u DJANGO_SETTINGS_MODULE ../venv/bin/python manage.py seed_iam_permissions --manifest /Users/ashutoshsaxena/a9/Fusion-Integrated/registry/permissions.json
  placement: 29 mapping(s)
0 added, 0 revoked; 68 total
+(eval):7> env -u DJANGO_SETTINGS_MODULE ../venv/bin/python manage.py assign_role --user stf00062 --designation 'placement officer'
+(eval):7> tail -1
  now holds: staff, placement officer
+(eval):7> cd /Users/ashutoshsaxena/a9/Fusion-Integrated
+(eval):8> DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py open_placement_season --season 2026-27
+(eval):8> tail -2
Opened season 2026-27 with 5 categories.
+(eval):9> DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py seed_modules
+(eval):9> tail -2
  registered placement (active)
1 module(s) registered
+(eval):10> DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py placement_readiness
placement is ready.
+(eval):10> echo 'readiness exit=0'
readiness exit=0
```

Then `make dev` was restarted on the fresh database, and the officer registered a company through the Companies page in a browser.
The page started empty, the save answered 201, the new row appeared, and the console showed no error.
The `runserver` lines:

```text
[20/Nov/2026 11:42:02] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:42:04] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:42:04] "GET /api/v1/placement/companies HTTP/1.1" 200 42
[20/Nov/2026 11:42:05] "POST /api/v1/placement/companies HTTP/1.1" 201 324
[20/Nov/2026 11:42:05] "GET /api/v1/placement/companies HTTP/1.1" 200 366
```

`make dev` was then restarted normally and the database was dropped.

## 8. Browser walkthrough

Each row was run alone with `npx playwright test <spec>:<line> --workers=1` against the running IAM, `make dev` and the client.
The lines under each row are the `runserver` lines that row produced.
Row 3 is the keyboard-only flow.
No row produced a 5xx, an uncaught page error or a console error; the shared test fixture fails a test on any of them.
Screens were also checked by eye at 1280 px with the sidebar open, which led to these fixes: whole badges in tables, every action column visible, a Role column on the interview lists, an empty-state line on the company report, and real icons in the sidebar.

| Row | Role | Dump username | Use case | Result | Spec |
|---|---|---|---|---|---|
| 1 | anonymous | none (a new unknown name each run) | Sign-in refusal | passed | `auth.spec.ts` |
| 2 | student (plain user) | stu00001 | Sign in, student screens only, sign out | passed | `auth.spec.ts` |
| 3 | student (plain user) | stu00001 | Sign in with the keyboard alone | passed | `auth.spec.ts` |
| 4 | placement officer | stf00062 | PC-UC-014 (office registers a company) | passed | `placement/companies.spec.ts` |
| 5 | student (plain user) | stu00001 | Five office pages opened by address are refused | passed | `placement/office-pages.spec.ts` |
| 6 | placement officer | stf00062 | PC-UC-006 | passed | `placement/office.spec.ts` |
| 7 | placement officer | stf00062 | PC-UC-008 | passed | `placement/office.spec.ts` |
| 8 | placement officer | stf00062 | PC-UC-009 | passed | `placement/office.spec.ts` |
| 9 | placement officer | stf00062 | PC-UC-010 | passed | `placement/office.spec.ts` |
| 10 | placement officer | stf00062 | PC-UC-011 | passed | `placement/office.spec.ts` |
| 11 | placement officer | stf00062 | PC-UC-020 | passed | `placement/office.spec.ts` |
| 12 | placement chairman | fac00001 | PC-UC-012 | passed | `placement/oversight.spec.ts` |
| 13 | placement chairman | fac00001 | PC-UC-013 | passed | `placement/oversight.spec.ts` |
| 14 | alumnus | stu00003 | PC-UC-017 | passed | `placement/oversight.spec.ts` |
| 15 | company, not signed in | none (public form) | PC-UC-014 (self-registration) | passed | `placement/recruiter.spec.ts` |
| 16 | company recruiter | invited per run (hire-...@example.test) | PC-UC-015 | passed | `placement/recruiter.spec.ts` |
| 17 | company recruiter | invited per run (hire-...@example.test) | PC-UC-016, PC-UC-021, PC-UC-022 | passed | `placement/recruiter.spec.ts` |
| 18 | student | stu00002 | PC-UC-001, PC-UC-023 | passed | `placement/student.spec.ts` |
| 19 | student | stu00002 | PC-UC-002, PC-UC-003 | passed | `placement/student.spec.ts` |
| 20 | student | stu00002 | PC-UC-004 | passed | `placement/student.spec.ts` |
| 21 | student | stu00002 | PC-UC-005 | passed | `placement/student.spec.ts` |
| 22 | student | stu00002 | PC-UC-024 | passed | `placement/student.spec.ts` |
| 23 | student (plain user) | stu00001 | Collapsed sidebar names each module | passed | `shell.spec.ts` |

**Row 1: wrong credentials are refused and the user stays on the login page**

```text
[20/Nov/2026 11:42:33] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:42:34] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:34] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:34] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:42:34] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:42:34] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:42:36] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:42:38] "POST /api/v1/auth/login HTTP/1.1" 401 149
```

**Row 2: a student sees only student screens, then signs out**

```text
[20/Nov/2026 11:42:40] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:42:41] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:41] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:41] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:42:41] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:42:41] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:42:42] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:42:45] "POST /api/v1/auth/login HTTP/1.1" 200 91
[20/Nov/2026 11:42:45] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:45] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
[20/Nov/2026 11:42:45] "GET /api/v1/placement/postings HTTP/1.1" 200 16667
[20/Nov/2026 11:42:45] "GET /api/v1/placement/companies HTTP/1.1" 200 9371
[20/Nov/2026 11:42:45] "POST /api/v1/auth/logout HTTP/1.1" 200 11
[20/Nov/2026 11:42:45] "GET /api/v1/placement/companies HTTP/1.1" 401 161
[20/Nov/2026 11:42:45] "GET /api/v1/placement/seasons HTTP/1.1" 401 161
```

**Row 3: a student can sign in with the keyboard alone**

```text
[20/Nov/2026 11:42:47] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:42:48] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:48] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:48] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:42:48] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:42:48] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:42:49] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:42:49] "POST /api/v1/auth/login HTTP/1.1" 200 91
[20/Nov/2026 11:42:50] "GET /api/v1/me HTTP/1.1" 200 1604
```

**Row 4: a placement officer registers a company and sees it pending approval**

```text
[20/Nov/2026 11:42:51] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:42:52] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:52] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:52] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:42:52] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:42:52] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:42:53] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:42:54] "GET /api/v1/placement/companies HTTP/1.1" 200 9807
[20/Nov/2026 11:42:54] "POST /api/v1/placement/companies HTTP/1.1" 201 487
[20/Nov/2026 11:42:54] "GET /api/v1/placement/companies HTTP/1.1" 200 9942
```

**Row 5: a student who opens /placement/companies is told it is not for them**

```text
[20/Nov/2026 11:42:56] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:42:57] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:57] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:57] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:42:57] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:42:57] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:42:58] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:58] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:58] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:59] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:42:59] "GET /api/v1/me HTTP/1.1" 200 1604
```

**Row 6: PC-UC-006: the officer publishes a draft posting**

```text
[20/Nov/2026 11:43:01] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:02] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:02] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:02] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:02] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:02] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:02] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:02] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:02] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:43:03] "POST /api/v1/placement/companies/183/approve HTTP/1.1" 200 373
[20/Nov/2026 11:43:03] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:43:03] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:03] "POST /api/v1/placement/postings HTTP/1.1" 201 635
[20/Nov/2026 11:43:04] "GET /api/v1/placement/postings HTTP/1.1" 200 16166
[20/Nov/2026 11:43:04] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
[20/Nov/2026 11:43:04] "GET /api/v1/placement/companies HTTP/1.1" 200 9828
[20/Nov/2026 11:43:04] "GET /api/v1/placement/postings/155/eligibility HTTP/1.1" 200 483
[20/Nov/2026 11:43:04] "POST /api/v1/placement/postings/155/publish HTTP/1.1" 200 668
[20/Nov/2026 11:43:04] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
[20/Nov/2026 11:43:04] "GET /api/v1/placement/postings HTTP/1.1" 200 16199
[20/Nov/2026 11:43:04] "GET /api/v1/placement/companies HTTP/1.1" 200 9828
[20/Nov/2026 11:43:04] "GET /api/v1/placement/postings/155/eligibility HTTP/1.1" 200 483
```

**Row 7: PC-UC-008: the officer filters applications and moves one to review**

```text
[20/Nov/2026 11:43:06] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:07] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:07] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:07] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:07] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:07] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:07] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:08] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:08] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:43:08] "POST /api/v1/placement/companies/184/approve HTTP/1.1" 200 373
[20/Nov/2026 11:43:08] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:43:08] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:08] "POST /api/v1/placement/postings HTTP/1.1" 201 635
[20/Nov/2026 11:43:08] "POST /api/v1/placement/postings/156/publish HTTP/1.1" 200 668
[20/Nov/2026 11:43:08] "POST /api/v1/placement/applications/apply HTTP/1.1" 201 1351
[20/Nov/2026 11:43:09] "GET /api/v1/placement/applications HTTP/1.1" 200 37441
[20/Nov/2026 11:43:09] "POST /api/v1/placement/applications/106/transition HTTP/1.1" 200 1367
[20/Nov/2026 11:43:09] "GET /api/v1/placement/applications HTTP/1.1" 200 37429
```

**Row 8: PC-UC-009: the officer puts a shortlisted candidate into an interview round**

```text
[20/Nov/2026 11:43:11] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:12] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:12] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:12] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:12] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:12] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:12] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:12] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:12] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:43:12] "POST /api/v1/placement/companies/185/approve HTTP/1.1" 200 373
[20/Nov/2026 11:43:12] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:43:13] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:13] "POST /api/v1/placement/postings HTTP/1.1" 201 635
[20/Nov/2026 11:43:13] "POST /api/v1/placement/postings/157/publish HTTP/1.1" 200 668
[20/Nov/2026 11:43:13] "POST /api/v1/placement/applications/apply HTTP/1.1" 201 1351
[20/Nov/2026 11:43:13] "POST /api/v1/placement/applications/107/transition HTTP/1.1" 200 1389
[20/Nov/2026 11:43:13] "POST /api/v1/placement/interviews/rounds HTTP/1.1" 201 302
[20/Nov/2026 11:43:13] "GET /api/v1/placement/interviews/rounds HTTP/1.1" 200 7621
[20/Nov/2026 11:43:13] "GET /api/v1/placement/postings HTTP/1.1" 200 16376
[20/Nov/2026 11:43:13] "GET /api/v1/placement/applications HTTP/1.1" 200 37440
[20/Nov/2026 11:43:14] "GET /api/v1/placement/applications?posting=157&status=shortlisted HTTP/1.1" 200 1563
[20/Nov/2026 11:43:14] "POST /api/v1/placement/interviews/rounds/39/candidates HTTP/1.1" 201 15
[20/Nov/2026 11:43:14] "GET /api/v1/placement/applications?posting=157&status=shortlisted HTTP/1.1" 200 42
[20/Nov/2026 11:43:14] "GET /api/v1/placement/interviews/rounds HTTP/1.1" 200 7621
[20/Nov/2026 11:43:14] "GET /api/v1/placement/postings HTTP/1.1" 200 16376
[20/Nov/2026 11:43:14] "GET /api/v1/placement/applications?posting=157 HTTP/1.1" 200 1574
[20/Nov/2026 11:43:14] "GET /api/v1/placement/applications HTTP/1.1" 200 37451
```

**Row 9: PC-UC-010: the officer corrects a placement record and its history keeps the old value**

```text
[20/Nov/2026 11:43:16] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:17] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:17] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:17] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:17] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:17] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:17] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:17] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:17] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:43:17] "POST /api/v1/placement/companies/186/approve HTTP/1.1" 200 373
[20/Nov/2026 11:43:18] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:43:18] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:18] "POST /api/v1/placement/records/off-campus HTTP/1.1" 201 442
[20/Nov/2026 11:43:19] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
[20/Nov/2026 11:43:19] "GET /api/v1/placement/records/office HTTP/1.1" 200 9846
[20/Nov/2026 11:43:19] "PATCH /api/v1/placement/records/25 HTTP/1.1" 200 396
[20/Nov/2026 11:43:19] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
[20/Nov/2026 11:43:19] "GET /api/v1/placement/records/office HTTP/1.1" 200 9847
[20/Nov/2026 11:43:19] "GET /api/v1/placement/records/25/revisions HTTP/1.1" 200 237
```

**Row 10: PC-UC-011: the officer reads the reports, salary bands and trends**

```text
[20/Nov/2026 11:43:21] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:22] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:22] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:22] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:22] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:22] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:22] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:22] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:22] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:43:22] "POST /api/v1/placement/companies/187/approve HTTP/1.1" 200 373
[20/Nov/2026 11:43:22] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:43:23] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:24] "GET /api/v1/placement/stats HTTP/1.1" 200 530
[20/Nov/2026 11:43:24] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
[20/Nov/2026 11:43:24] "GET /api/v1/placement/stats/trends HTTP/1.1" 200 108
[20/Nov/2026 11:43:24] "GET /api/v1/placement/records/outstanding HTTP/1.1" 200 10994
```

**Row 11: PC-UC-020: the officer publishes an announcement**

```text
[20/Nov/2026 11:43:25] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:26] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:26] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:26] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:26] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:26] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:27] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:27] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:27] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:43:27] "POST /api/v1/placement/companies/188/approve HTTP/1.1" 200 373
[20/Nov/2026 11:43:27] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:43:27] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:28] "GET /api/v1/placement/announcements HTTP/1.1" 200 8170
[20/Nov/2026 11:43:28] "POST /api/v1/placement/announcements HTTP/1.1" 201 312
[20/Nov/2026 11:43:28] "GET /api/v1/placement/announcements HTTP/1.1" 200 8170
```

**Row 12: PC-UC-012: the chairman views oversight reports and company engagement**

```text
[20/Nov/2026 11:43:30] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:31] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:31] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:31] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:31] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:31] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:32] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:33] "GET /api/v1/placement/stats HTTP/1.1" 200 530
[20/Nov/2026 11:43:33] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
[20/Nov/2026 11:43:33] "GET /api/v1/placement/stats/trends HTTP/1.1" 200 108
[20/Nov/2026 11:43:33] "GET /api/v1/placement/records/outstanding HTTP/1.1" 200 10994
```

**Row 13: PC-UC-013: the chairman publishes an official announcement**

```text
[20/Nov/2026 11:43:34] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:35] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:35] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:35] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:35] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:35] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:36] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:37] "GET /api/v1/placement/announcements HTTP/1.1" 200 8170
[20/Nov/2026 11:43:37] "POST /api/v1/placement/announcements HTTP/1.1" 201 330
[20/Nov/2026 11:43:37] "GET /api/v1/placement/announcements HTTP/1.1" 200 8170
```

**Row 14: PC-UC-017: an alumnus reads statistics and sees no active workflow**

```text
[20/Nov/2026 11:43:39] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:40] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:40] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:40] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:40] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:40] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:40] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:41] "GET /api/v1/placement/stats HTTP/1.1" 200 98
[20/Nov/2026 11:43:41] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
[20/Nov/2026 11:43:41] "GET /api/v1/me HTTP/1.1" 200 1611
```

**Row 15: PC-UC-014: a company registers itself and waits for approval**

```text
[20/Nov/2026 11:43:43] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:44] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:44] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:44] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:44] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:44] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:44] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:45] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:45] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:43:45] "GET /api/v1/placement/recruiters/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:45] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:47] "GET /api/v1/placement/recruiters/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:47] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:47] "POST /api/v1/placement/companies/register HTTP/1.1" 201 99
[20/Nov/2026 11:43:47] "GET /api/v1/placement/companies HTTP/1.1" 200 9911
```

**Row 16: PC-UC-015: the recruiter submits a posting to the placement office**

```text
[20/Nov/2026 11:43:49] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:51] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:51] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:51] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:51] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:51] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:51] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:51] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:51] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:43:52] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:43:52] "POST /api/v1/placement/companies/190/approve HTTP/1.1" 200 373
[20/Nov/2026 11:43:52] "POST /api/v1/placement/recruiters/invite HTTP/1.1" 201 167
[20/Nov/2026 11:43:52] "POST /api/v1/placement/recruiters/accept HTTP/1.1" 200 47
[20/Nov/2026 11:43:52] "POST /api/v1/placement/recruiters/login HTTP/1.1" 200 141
[20/Nov/2026 11:43:52] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:52] "GET /api/v1/placement/recruiters/me HTTP/1.1" 200 250
[20/Nov/2026 11:43:53] "GET /api/v1/placement/postings HTTP/1.1" 200 42
[20/Nov/2026 11:43:53] "POST /api/v1/placement/postings HTTP/1.1" 201 628
[20/Nov/2026 11:43:53] "GET /api/v1/placement/postings HTTP/1.1" 200 670
[20/Nov/2026 11:43:53] "GET /api/v1/placement/recruiters/me HTTP/1.1" 200 250
[20/Nov/2026 11:43:54] "POST /api/v1/placement/postings/158/submit HTTP/1.1" 200 639
[20/Nov/2026 11:43:54] "GET /api/v1/placement/postings HTTP/1.1" 200 681
[20/Nov/2026 11:43:54] "GET /api/v1/placement/recruiters/me HTTP/1.1" 200 250
```

**Row 17: PC-UC-016, PC-UC-021, PC-UC-022: the recruiter shortlists, schedules and offers**

```text
[20/Nov/2026 11:43:56] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:57] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:57] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:57] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:57] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:43:57] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:43:58] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:43:58] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:43:58] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:43:58] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:43:58] "POST /api/v1/placement/companies/191/approve HTTP/1.1" 200 373
[20/Nov/2026 11:43:58] "POST /api/v1/placement/recruiters/invite HTTP/1.1" 201 167
[20/Nov/2026 11:43:58] "POST /api/v1/placement/recruiters/accept HTTP/1.1" 200 47
[20/Nov/2026 11:43:58] "POST /api/v1/placement/recruiters/login HTTP/1.1" 200 141
[20/Nov/2026 11:43:59] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:43:59] "GET /api/v1/placement/recruiters/me HTTP/1.1" 200 250
[20/Nov/2026 11:43:59] "GET /api/v1/placement/postings HTTP/1.1" 200 42
[20/Nov/2026 11:43:59] "POST /api/v1/placement/postings HTTP/1.1" 201 628
[20/Nov/2026 11:43:59] "GET /api/v1/placement/recruiters/me HTTP/1.1" 200 250
[20/Nov/2026 11:43:59] "GET /api/v1/placement/postings HTTP/1.1" 200 670
[20/Nov/2026 11:44:00] "POST /api/v1/placement/postings/159/publish HTTP/1.1" 200 661
[20/Nov/2026 11:44:00] "GET /api/v1/placement/postings HTTP/1.1" 200 703
[20/Nov/2026 11:44:00] "GET /api/v1/placement/recruiters/me HTTP/1.1" 200 250
[20/Nov/2026 11:44:00] "GET /api/v1/placement/postings HTTP/1.1" 200 703
[20/Nov/2026 11:44:00] "POST /api/v1/placement/applications/apply HTTP/1.1" 201 1344
[20/Nov/2026 11:44:00] "GET /api/v1/placement/applications HTTP/1.1" 200 330
[20/Nov/2026 11:44:01] "POST /api/v1/placement/applications/108/transition HTTP/1.1" 200 1382
[20/Nov/2026 11:44:01] "GET /api/v1/placement/postings HTTP/1.1" 200 703
[20/Nov/2026 11:44:01] "GET /api/v1/placement/recruiters/me HTTP/1.1" 200 250
[20/Nov/2026 11:44:01] "GET /api/v1/placement/applications HTTP/1.1" 200 332
[20/Nov/2026 11:44:01] "GET /api/v1/placement/interviews/rounds HTTP/1.1" 200 42
[20/Nov/2026 11:44:01] "GET /api/v1/placement/applications HTTP/1.1" 200 332
[20/Nov/2026 11:44:05] "POST /api/v1/placement/interviews/rounds HTTP/1.1" 201 294
[20/Nov/2026 11:44:05] "GET /api/v1/placement/recruiters/me HTTP/1.1" 200 250
[20/Nov/2026 11:44:05] "GET /api/v1/placement/postings HTTP/1.1" 200 703
[20/Nov/2026 11:44:05] "GET /api/v1/placement/interviews/rounds HTTP/1.1" 200 336
[20/Nov/2026 11:44:05] "GET /api/v1/placement/applications HTTP/1.1" 200 332
[20/Nov/2026 11:44:05] "GET /api/v1/placement/applications?posting=159&status=shortlisted HTTP/1.1" 200 332
[20/Nov/2026 11:44:05] "POST /api/v1/placement/interviews/rounds/40/candidates HTTP/1.1" 201 15
[20/Nov/2026 11:44:05] "GET /api/v1/placement/applications?posting=159&status=shortlisted HTTP/1.1" 200 42
[20/Nov/2026 11:44:05] "GET /api/v1/placement/postings HTTP/1.1" 200 703
[20/Nov/2026 11:44:05] "GET /api/v1/placement/interviews/rounds HTTP/1.1" 200 336
[20/Nov/2026 11:44:05] "GET /api/v1/placement/recruiters/me HTTP/1.1" 200 250
[20/Nov/2026 11:44:05] "GET /api/v1/placement/applications HTTP/1.1" 200 340
[20/Nov/2026 11:44:06] "GET /api/v1/placement/applications HTTP/1.1" 200 340
[20/Nov/2026 11:44:09] "POST /api/v1/placement/offers/issue HTTP/1.1" 201 882
[20/Nov/2026 11:44:09] "GET /api/v1/placement/recruiters/me HTTP/1.1" 200 250
[20/Nov/2026 11:44:09] "GET /api/v1/placement/postings HTTP/1.1" 200 703
[20/Nov/2026 11:44:10] "GET /api/v1/placement/applications HTTP/1.1" 200 333
```

**Row 18: PC-UC-001, PC-UC-023: the student opens the profile and its structured resume**

```text
[20/Nov/2026 11:44:12] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:44:13] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:13] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:13] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:13] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:44:13] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:44:14] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:14] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:14] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:44:14] "POST /api/v1/placement/companies/192/approve HTTP/1.1" 200 373
[20/Nov/2026 11:44:14] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:44:15] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:16] "GET /api/v1/placement/profile/resume HTTP/1.1" 200 361
[20/Nov/2026 11:44:16] "GET /api/v1/placement/documents HTTP/1.1" 200 262
[20/Nov/2026 11:44:16] "POST /api/v1/placement/documents HTTP/1.1" 201 248
[20/Nov/2026 11:44:16] "GET /api/v1/placement/documents HTTP/1.1" 200 262
[20/Nov/2026 11:44:16] "GET /api/v1/placement/profile/resume HTTP/1.1" 200 361
```

**Row 19: PC-UC-002, PC-UC-003: the student browses, checks eligibility and applies**

```text
[20/Nov/2026 11:44:19] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:44:21] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:21] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:21] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:21] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:44:21] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:44:21] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:21] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:21] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:44:21] "POST /api/v1/placement/companies/193/approve HTTP/1.1" 200 373
[20/Nov/2026 11:44:21] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:44:22] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:22] "POST /api/v1/placement/postings HTTP/1.1" 201 635
[20/Nov/2026 11:44:22] "POST /api/v1/placement/postings/160/publish HTTP/1.1" 200 668
[20/Nov/2026 11:44:23] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
[20/Nov/2026 11:44:23] "GET /api/v1/placement/companies HTTP/1.1" 200 9434
[20/Nov/2026 11:44:23] "GET /api/v1/placement/postings HTTP/1.1" 200 16667
[20/Nov/2026 11:44:23] "GET /api/v1/placement/postings/160/eligibility HTTP/1.1" 200 371
[20/Nov/2026 11:44:24] "POST /api/v1/placement/applications/apply HTTP/1.1" 201 1351
[20/Nov/2026 11:44:24] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
[20/Nov/2026 11:44:24] "GET /api/v1/placement/postings HTTP/1.1" 200 16667
[20/Nov/2026 11:44:24] "GET /api/v1/placement/companies HTTP/1.1" 200 9434
[20/Nov/2026 11:44:24] "GET /api/v1/placement/postings/160/eligibility HTTP/1.1" 200 371
```

**Row 20: PC-UC-004: the student tracks the application**

```text
[20/Nov/2026 11:44:26] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:44:27] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:27] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:27] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:27] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:44:27] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:44:27] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:27] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:27] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:44:28] "POST /api/v1/placement/companies/194/approve HTTP/1.1" 200 373
[20/Nov/2026 11:44:28] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:44:28] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:28] "POST /api/v1/placement/postings HTTP/1.1" 201 635
[20/Nov/2026 11:44:28] "POST /api/v1/placement/postings/161/publish HTTP/1.1" 200 668
[20/Nov/2026 11:44:28] "POST /api/v1/placement/applications/apply HTTP/1.1" 201 1351
[20/Nov/2026 11:44:29] "GET /api/v1/placement/applications HTTP/1.1" 200 33881
```

**Row 21: PC-UC-005: the student answers an offer before its deadline**

```text
[20/Nov/2026 11:44:35] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:44:37] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:37] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:37] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:37] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:44:37] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:44:37] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:37] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:37] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:44:37] "POST /api/v1/placement/companies/195/approve HTTP/1.1" 200 373
[20/Nov/2026 11:44:37] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:44:38] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:38] "POST /api/v1/placement/postings HTTP/1.1" 201 635
[20/Nov/2026 11:44:38] "POST /api/v1/placement/postings/162/publish HTTP/1.1" 200 668
[20/Nov/2026 11:44:38] "POST /api/v1/placement/applications/apply HTTP/1.1" 201 1351
[20/Nov/2026 11:44:38] "POST /api/v1/placement/applications/111/transition HTTP/1.1" 200 1389
[20/Nov/2026 11:44:38] "POST /api/v1/placement/offers/issue HTTP/1.1" 201 910
[20/Nov/2026 11:44:39] "GET /api/v1/placement/records HTTP/1.1" 200 14
[20/Nov/2026 11:44:39] "GET /api/v1/placement/offers HTTP/1.1" 200 23655
[20/Nov/2026 11:44:39] "GET /api/v1/placement/records/clearance HTTP/1.1" 200 97
[20/Nov/2026 11:44:39] "GET /api/v1/placement/documents HTTP/1.1" 200 262
[20/Nov/2026 11:44:39] "POST /api/v1/placement/offers/40/respond HTTP/1.1" 200 985
[20/Nov/2026 11:44:39] "GET /api/v1/placement/records HTTP/1.1" 200 14
[20/Nov/2026 11:44:39] "GET /api/v1/placement/records/clearance HTTP/1.1" 200 97
[20/Nov/2026 11:44:39] "GET /api/v1/placement/documents HTTP/1.1" 200 262
[20/Nov/2026 11:44:39] "GET /api/v1/placement/offers HTTP/1.1" 200 23730
```

**Row 22: PC-UC-024: the student reads anonymised statistics for a season**

```text
[20/Nov/2026 11:44:41] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:44:42] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:42] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:42] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:42] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:44:42] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:44:42] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:42] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:42] "POST /api/v1/placement/companies HTTP/1.1" 201 342
[20/Nov/2026 11:44:42] "POST /api/v1/placement/companies/196/approve HTTP/1.1" 200 373
[20/Nov/2026 11:44:42] "GET /api/v1/placement/registrations HTTP/1.1" 200 317
[20/Nov/2026 11:44:43] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:43] "GET /api/v1/placement/stats HTTP/1.1" 200 98
[20/Nov/2026 11:44:43] "GET /api/v1/placement/seasons HTTP/1.1" 200 74
```

**Row 23: the collapsed sidebar names each module for a screen reader**

```text
[20/Nov/2026 11:44:45] "GET /api/v1/me HTTP/1.1" 401 161
[20/Nov/2026 11:44:46] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:46] "GET /api/v1/me HTTP/1.1" 200 1604
[20/Nov/2026 11:44:46] "GET /api/v1/me HTTP/1.1" 200 2025
[20/Nov/2026 11:44:46] "GET /api/v1/me HTTP/1.1" 200 1295
[20/Nov/2026 11:44:46] "GET /api/v1/me HTTP/1.1" 200 1611
[20/Nov/2026 11:44:47] "GET /api/v1/me HTTP/1.1" 200 1604
```

## 9. Scheduled work run by hand

Each task was called once in `manage.py shell` on the development database.

```text
deliver_notifications
  before: {'pending': 58, 'sent': 224, 'suppressed': 291}
  result: expanded=19 sent=4 failed=0 capped=54 deferred=0
  after:  {'sent': 247, 'suppressed': 345}
expire_overdue_offers
  before: offer 12 status=issued, respond_by moved 1 minute into the past
  result: 1
  after:  offer 12 status=expired, application=offer_expired
rebuild_active_stats
  before: rows 1 computed_at [datetime.datetime(2026, 11, 20, 5, 47, 19, 545471, tzinfo=datetime.timezone.utc)]
  result: 1
  after:  rows 1 computed_at [datetime.datetime(2026, 11, 20, 6, 12, 26, 143598, tzinfo=datetime.timezone.utc)]
```

Notification delivery sent what was pending and suppressed the rest under the daily limit of 20 emails per recipient.
Offer expiry turned an offer whose deadline had passed into `expired` and its application into `offer_expired`.
The statistics rebuild replaced the season's snapshot.

## 10. Known gaps

| Spec id | Gap | Reason | Approval |
|---|---|---|---|
| PC-BR-004 | Skills are not a posting criterion. | The IAM does not project skills, so no rule could check them. | Approved by Masabathini Saketh (24BCS147), 2026-11-20. |
| ISS-PC-025 | Notification recipients are the applicant only. | The spec does not name the recipient. | Approved by Masabathini Saketh (24BCS147), 2026-11-20. |
| ISS-PC-026 | The office records company approval. | The spec does not name who records it. | Approved by Masabathini Saketh (24BCS147), 2026-11-20. |
| none | A student who also holds `alumini` keeps student access. | The IAM session joins every role's grants; the fix is outside the module (blueprint decision 8). | Approved by Masabathini Saketh (24BCS147), 2026-11-20. |

The full list of open questions and decisions is section (h) of `placement-blueprint.md`.

## 11. Approvals

Student 2, Masabathini Saketh (24BCS147), approved each item below in writing on 2026-11-20.

| Item | Status |
|---|---|
| The blueprint, `placement-blueprint.md` | Approved by Masabathini Saketh (24BCS147), 2026-11-20. The code was written before the blueprint, which breaks the prompt's order; this is recorded here. |
| Each decision in blueprint section (h), items 1 to 11 | Approved by Masabathini Saketh (24BCS147), 2026-11-20. |
| Each known gap in section 10 | Approved by Masabathini Saketh (24BCS147), 2026-11-20. |
| Shared-file changes, listed below | Approved by Masabathini Saketh (24BCS147), 2026-11-20. |
| New dependencies | None needed. |

Shared-file changes outside the module's own folders:

| File | Change |
|---|---|
| `config/settings/base.py` | Three throttle rates (`placement_write`, `placement_record_write`, `company_register`) and one enum name for the schema. |
| `client/src/app/registry.ts`, `README.md`, `modules/accesscontrol/models.py`, `modules/accesscontrol/management/commands/permission_manifest.py` | The module code renamed from `placement_cell` to `placement`. |
| `core/tests/test_csrf.py`, `fusion_auth/tests/test_auth.py`, `modules/accesscontrol/tests/test_navigation.py`, `modules/directory/tests/test_search_api.py`, `client/src/auth/RequirePermission.test.tsx` | Test data follows the renamed module code and permissions. |
| `modules/directory/registry.py` | Grants keyed by the ERP's spelling, "placement officer" and "placement chairman"; the old keys matched no real user. |
| `modules/accesscontrol/management/commands/seed_modules.py` | Prints the status it saved, not the status it was asked for. |
| `client/src/app/router.tsx` | The company self-registration page. |
| `client/src/recruiter/` (8 files, plus `RegisterCompanyPage.tsx` and its test) | The company's own login lane (blueprint decision 3): the self-registration page, recruiter forms through the UI, and accessible names. |
| `client/src/auth/AuthProvider.tsx` | An institute 401 no longer sends a recruiter page to the institute login. |
| `client/src/ui/components/StatusBadge.tsx` | Colours for three application states. |
| `client/src/ui/components/DataTable.tsx`, `DataTable.module.css` | A badge in a table keeps its full text. |
| `client/src/ui/components/FormModal.tsx` | The dialog title is `Modal.Title`, so every form dialog has an accessible name. |
| `client/src/ui/icons.ts`, `icons.test.ts` | Phosphor icon names from module registries draw their Font Awesome twin, not a grey circle. |
| `client/src/ui/theme/theme.ts` | Names for the date picker's month arrows and confirm button. |
| `client/e2e/accounts.ts`, `client/e2e/auth.spec.ts` | Three test accounts; the sign-in test waits out the IAM's login limit, and the student's sidebar list includes the new links. |
| `ops/docs/module_structure.py`, `ops/docs/placement_reference.py` | The structure reference drops a deleted file; a new generator writes `placement-reference.md`. |
| `.github/workflows/e2e.yml` | Creates `examination_student_grades` as a view of the dump's `online_cms_student_grades`, so the latest IAM can sync, and opens season 2026-27 with `open_placement_season`. Added after Student 2's approval; waits for Student 2's approval. |
| `fusion_auth/views.py`, `fusion_auth/tests/test_auth.py`, `conftest.py` | A role switch answered with the role from before the switch, so the shell kept showing the old role. It now answers with the session as it is after the switch. Added after Student 2's approval; waits for Student 2's approval. |
| `openapi/fusion-integrated.v1.yaml`, `registry/permissions.json`, `docs/02-iam/permission-catalog.generated.md`, `docs/_diagrams/application-state-machine.mmd` | Regenerated. |

## 12. Review rounds

Student 2 reviewed the code on 2026-11-20.
No scorecard was recorded.
The spec tests (Step 8) are not on the branch yet.

## Notes for the next run

- The IAM allows five sign-ins a minute from one address. A cold `make e2e` uses all five in global setup, so the sign-in tests wait up to a minute.
- The module limits applications to 30 per student per hour, and one `make e2e` run applies about six times as one student. More than about five full runs in an hour on one database are refused. Clear the counters with `docker compose exec -T redis-cache sh -c "redis-cli -n 1 --scan --pattern '*throttle*' | xargs -r redis-cli -n 1 del"`.
