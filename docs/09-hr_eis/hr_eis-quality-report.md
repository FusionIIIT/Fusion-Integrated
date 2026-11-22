# HR-EIS quality report — builder evidence

This report records builder evidence; it is not an independent review scorecard or a claim that the assignment has passed. The branch is `module/hr_eis`; commit `28e4815389a234b6e51bc32eca82846c8db3d1ff` removes the shared enum override and updates an obsolete navigation-test fixture, and `0ba97d9e37fbb98a1b932b2b2550675215455875` aligns the client folder and names HR schema components locally. The OpenAPI file was regenerated from the current source and passes the CI `--fail-on-warn` plus byte comparison. Compared with HEAD, it contains 29 HR API paths and 53 schemas added, no paths or schemas removed, and generated updates to 10 existing directory/placement paths and 6 shared schemas. Those shared generated changes are preserved; their approval record is not present, so the file remains unstaged/uncommitted. `.venv-system/` is an untracked local environment excluded from commits and reviewer copies.

## 1. Repository gates

`make check` and `make check-client` were not invoked because `make` is not installed in this Windows environment. Their relevant available components were run directly; see the gate results below. The schema warning is fixed in HR serializer fields using module-local named choice schemas; no shared schema setting was added. Deployment security warnings under local/test settings remain and were not altered.

## 2. Backend coverage

Both prescribed coverage gates now pass against PostgreSQL at 100% statement and branch coverage. Before this test expansion, `modules/hr` was 62.57% and `modules/hr/domain` was 71.09%. Added meaningful state-machine, service, selector/contract, serializer, task, model-invariant, and authenticated API workflow tests; all 165 HR tests pass. Exact baseline uncovered lines/arcs and post-test results are in [the HR coverage analysis](hr_eis-coverage-analysis.md). PostgreSQL is reached using the ignored root `.env`; Django uses the isolated `test_fusion_integrated` database. The configured `fusion_integrated` database was not tested against or migrated.

## 3. Test inventory and journeys

The HR suite contains 165 tests across the module test files. The last full PostgreSQL HR run passed 165/165. The earlier broader suite had one failure in `modules/accesscontrol/tests/test_navigation.py::test_seed_modules_retires_a_module_no_code_declares_any_more`; commit `28e4815` changes that test to use a synthetic `retired_module` code. A passing PostgreSQL rerun of that test is not recorded here.

Leave requirement references appear in `test_leaves.py`: HR-AFR-029–043, HR-UC-003/004, BR-HR-007–011/023/024/034, BW-HR-01/02/03, CW-HR-01. Parameterized assertions cover the six types, required fields, balance/eligibility, route/deduction, rejection, audit/ledger immutability, and reminder deduplication. The broader module's test-to-ID inventory remains incomplete. There is no `modules/hr/tests/test_journeys.py`, and `client/e2e/hr` does not exist; end-to-end use-case coverage is not complete.

Frontend test results recorded before the module-folder correction: 8 files, 57 tests passed. The correction moves the HR API, pages, and leave test into `client/src/modules/hr/` beside its route manifest. These are builder tests, not Student 2's independent spec tests; rerun results after the move are recorded below when available.

## 4. Break-on-purpose checks

The five mutation checks required by Step 5.15 were not run. No production file was intentionally altered to test whether a test fails.

## 5. Adversarial pass

The leave workflow review found two defects and corrected them: configured leave routes could exceed one forwarding traversal, and the scheduled pending-reminder task processed claims but not leave requests. The leave state machine/configuration now caps routes at two authorities and refuses a second forward; the reminder task now creates a deduplicated, audited leave reminder after the configured delay. New tests exercise valid and invalid balance changes, missing eligibility/balance/route conditions, authority checks, approval-time revalidation, audit-ledger immutability, reminders, and authenticated API workflows. All pass against PostgreSQL. No production code needed changes during this coverage pass. The full Step 5.11 adversarial checklist remains incomplete.

Questions left to the pair: the specifications do not define entitlement/accrual formulas, leave date-range or backdating semantics, or a cancellation workflow. BR-HR-009 states that the exact approval matrix is institutional policy/configuration outside the problem statement. The module code is `hr` in the backend registry, API/permission prefix, and frontend folder, following the authoring prompt's lowercase no-underscore convention. The assigned source specification path remains `docs/09-hr_eis/specifications/`. The user reported labmate approval to proceed, but no direct written decision confirming the code name or pre-code blueprint approval is present; neither is fabricated. No behavior was invented for these specification questions.

## 6. Security self-audit

Static review confirms module grant and permission gates at the HR views, service-level permission checks on leave writes, actor/current-authority matching, submitter self-approval refusal, scoped leave selectors, positive duration/justification validation, and transactional balance deduction with a locked balance. The leave-balance route/panel and route-guard test use the registered `hr.leave_balance.manage` key. The three OpenAPI enum-name collisions are resolved in HR serializer annotations. An earlier deploy check under local/test settings showed W004/W008/W009/W018; the later prescribed prod-settings CI check passed with only configured W003/W019 silenced. Dedicated concurrency, CSRF, and ledger-trigger probes were not verified. No shared security setting was altered.

The registered client module and all HR pages, API hooks/types, route guards, and leave page tests now live under `client/src/modules/hr/`. The former split under `client/src/modules/hr_eis/` was removed in the current remediation worktree.

## 7. Fresh-install proof

Not run. The documented procedure requires Docker Compose, a disposable PostgreSQL database, IAM seeding, and a readiness check. The current PostgreSQL connection probe to `localhost:5432` timed out, and service status could not be read from this sandbox. The repository-root `.env` is ignored and contains the local DB settings. No services were started or modified; no database was migrated.

## 8. Browser walkthrough

Not run. The IAM/API stack was unavailable, and there are no HR-EIS Playwright journeys. The previous validation had PostgreSQL connectivity; the current probe timed out. Leave frontend unit tests do not substitute for the required role-by-role and keyboard walkthrough.

## 9. Scheduled tasks

`hr.deliver_notifications` and `hr.generate_pending_reminders` are registered in the current schedule. The latter now considers leave requests as well as claims. Neither task was run manually against a database; effect and idempotency remain unverified in this environment.

## 10. Known gaps

No direct written Student 2 approval for the pre-code blueprint or each required shared-file change is present in this record. Specification silence listed in section 5 is not treated as an accepted gap. Remaining verification gaps include missing journeys, incomplete full-module requirement-ID mapping, incomplete operator/browser proofs, and a multi-file migration history for an unmerged module. Coverage gates were met at 100% in the last complete PostgreSQL run. A previous `showmigrations` output listed unapplied HR migrations on `fusion_integrated`; current applied-history status could not be checked because PostgreSQL timed out. The configured database was not migrated. No migration files were removed or rewritten.

## 11. Required approvals

The user reports that labmate approval to proceed has been obtained. No dated/linkable written approval text from Student 2 is present in the repository evidence, and the scope of that reported approval is unspecified; this report does not extend it to the pre-code blueprint or each required shared-file change. The pre-code blueprint was not created before implementation and cannot be backdated. Shared integration changes in the feature commit are:

- `config/settings/base.py` — HR registration and write throttle (the enum override was removed in `28e4815`);
- `config/urls.py` — HR API registration;
- `config/celery.py` — HR task registration;
- `.importlinter` — HR module boundaries;
- `client/src/app/registry.ts` — HR client registration;
- `registry/permissions.json`, `docs/02-iam/permission-catalog.generated.md`, and `openapi/fusion-integrated.v1.yaml` — generated manifests/schema.

No Python or npm dependency was added to the repository manifests. The missing pre-code blueprint approval cannot be backdated or recreated. The three `drf_spectacular.W001` collisions were resolved with explicitly named schema components on HR serializer choice fields; no shared `ENUM_NAME_OVERRIDES` setting is used.

## 12. Review rounds

No completed prescribed review scorecard is recorded. A fresh reviewer session was started against commit `19f2847`; its first checkout was rejected because it lived beneath the home `.codex` instruction tree. A clean checkout was recreated under `C:\Temp`, but the reviewer could not run required gates because `make`, the project `.venv`, and DOCX tooling were unavailable; no scorecard was returned. `new-module-prompt.md` §10 prohibits the builder from scoring its own work. The later changes are now committed at `0ba97d9`; the official review must use a fresh clean checkout of that revision.

## Gate results

| Command | Result and output |
|---|---|
| `manage.py check` (`config.settings.test`) | Passed: “System check identified no issues (0 silenced).” |
| PostgreSQL connectivity probe (`config.settings.test`) | Passed: connected to PostgreSQL at `localhost:5432`, database `fusion_integrated`, role `fusion_admin`; credentials were not printed. |
| PostgreSQL test database preflight | Before HR tests, `test_fusion_integrated` was absent; role reported `CREATEDB=True`, `SUPERUSER=False` after the user's grant. HR test and coverage runs completed against the isolated test DB. |
| `manage.py check --database default` | Passed: “System check identified no issues (0 silenced).” |
| `manage.py showmigrations hr` | Read-only: `0001_initial`, `0002_audit_event_immutable`, and `0003_leave_management` are unapplied on the current `fusion_integrated` database. No `migrate` command was run against it. |
| `manage.py makemigrations hr --check --dry-run --noinput` | Passed model/migration-state comparison: “No changes detected in app 'hr'.” The first run also warned that consistent applied-migration history could not be checked because PostgreSQL timed out. No migration was run. |
| `manage.py permission_manifest --check` | Passed: “permission manifest matches the registries”. |
| `manage.py spectacular --validate --file <temp>` before module-local fix | Schema validation passed, 0 errors; 3 `drf_spectacular.W001` naming collisions (`action`, `employee_category`, and `request_type`). |
| `manage.py spectacular --validate --file <temp>` after module-local fix | Passed: 0 errors and 0 warnings. Schema was written only to a temp path; the working-tree OpenAPI file was not touched. |
| Earlier `manage.py check --deploy --fail-level WARNING` under local/test settings | Failed with 4 deployment security warnings: `security.W004`, `security.W008`, `security.W009`, and `security.W018`. The 3 `drf_spectacular.W001` warnings were absent. No shared settings were changed to suppress warnings. The later CI-style `config.settings.prod` invocation passed (see section 13). |
| `npm run lint` | Could not run: package script calls `eslint .`, but `eslint` is not declared in `client/package.json` and no ESLint executable is installed. No dependency/configuration change was made without approval. |
| `pytest modules/hr -q --tb=short` | Passed: 165 tests against PostgreSQL. |
| `pytest -q --tb=short` (before `28e4815`) | One failure: `modules/accesscontrol/tests/test_navigation.py::test_seed_modules_retires_a_module_no_code_declares_any_more`; its `hr` fixture conflicted with the declared HR module. `28e4815` updates the fixture to `retired_module`; a passing full-suite rerun is not recorded. |
| `pytest modules/hr --cov=modules/hr --cov-branch --cov-report=term-missing --cov-fail-under=90` | Passed: 165 tests; 100% of 1,400 statements and all 278 branch arcs. |
| `pytest modules/hr --cov=modules/hr/domain --cov-branch --cov-report=term-missing --cov-fail-under=95` | Passed: 165 tests; 100% of 84 statements and all 44 branch arcs in `state_machine.py`. |
| `pytest modules/hr/tests/test_leaves.py -q -k 'leave_decision or route_supports or supported_leave_types or requires_each_specified_field'` | Passed: 21 tests after PostgreSQL `.env` became available; these tests do not require DB fixtures. |
| `ruff check modules/hr`; `ruff format --check modules/hr` | Passed: all checks passed; 39 files already formatted. |
| `ops/checks/no_cross_module_fk.py`; `nav_matches_routes.py`; `contracts_are_plural.py` | Passed: no cross-module foreign keys; nav items and routes agree; all contract getters plural. |
| Import Linter | Passed: 5 contracts kept, 0 broken (invoked through the installed Python entry point because Windows blocked the console executable). |
| `git diff --check` | Passed before final permission-key edit; rerun is recorded in final submission checks. |
| Frontend typecheck, tests, build | Passed: TypeScript exit 0; 8 files/57 tests passed; Vite build succeeded. The leave page chunk is 1.64 kB gzip; Vite also reports the existing 503.20 kB main chunk warning. |
| Final permission-key regression test | Passed: `npm run test -- src/modules/hr/routes.test.tsx`; 1 file, 15 tests. |
| Final frontend typecheck and build | Passed: `npm run typecheck`; `npm run build` succeeded. Existing Vite warning: main chunk exceeds 500 kB. |
| Final PostgreSQL HR/coverage rerun | Not completed: the existing temporary project venv worked, but PostgreSQL test-database setup timed out at `localhost:5432`. No packages were installed. The previous PostgreSQL evidence above remains the last successful full backend run. |
| Final structural-check rerun | Not completed in this session: the available system Python lacks Django, and `.venv-system` lacks `sqlparse`; `ops/checks/no_cross_module_fk.py` and `ops/checks/nav_matches_routes.py` stop during Django import/setup. These checks passed in the earlier validation run recorded above. |
| Module-local OpenAPI schema annotation | Passed `manage.py spectacular --validate`: 0 errors and 0 warnings after naming colliding HR choice-field schemas locally. |
| Current `manage.py check` | Passed: “System check identified no issues (0 silenced).” |
| Current migration consistency rerun | `makemigrations hr --check --dry-run --noinput` returned “No changes detected in app 'hr'” but emitted a PostgreSQL connection-timeout warning while checking applied migration history. No migration was run against the configured database. |
| Current permission manifest check | Passed: “permission manifest matches the registries”. |
| Current focused frontend tests | Passed: `npm run test -- src/modules/hr/routes.test.tsx src/modules/hr/pages/LeavesPage.test.tsx`; 2 files, 19 tests after the folder move. |
| Current frontend typecheck | Passed: `npm run typecheck` (application and E2E TypeScript projects). |
| Current Ruff and whitespace checks | Passed: Ruff check and formatting for `modules/hr/api/serializers.py`; `git diff --check` passed. |
| Current full HR backend rerun | Full run could not initialize its isolated PostgreSQL test DB: `psycopg.errors.ConnectionTimeout` connecting to `localhost:5432`; the first-test `-x` rerun confirms this is setup/environment, not an assertion failure. Focused leave tests passed 21/21 without database fixtures. Previous successful PostgreSQL run: 165/165 and 100% coverage gates. |

The model and workflow references are documented in `hr_eis-domain-model.md` and `hr_eis-state-machine.md`. The required approved blueprint, generated live-ID reference script, complete quality-report evidence, pair run record, and formal review scorecards are not present yet.

## 13. Submission-preparation check (2026-11-22)

The current checkout is on `module/hr_eis` at `35b8d21` (`docs(hr): record remediation review status`), four commits ahead of `upstream/main`. At the start of this sprint, `git status --short --branch` reported the pre-existing modification to `openapi/fusion-integrated.v1.yaml` and untracked `.venv-system/`; neither was changed or included here. This report was then updated with the present sprint evidence. The root `.env` is ignored. `git diff --check` passed after the report update.

A PostgreSQL HR test rerun with `.venv/Scripts/python.exe -m pytest modules/hr -q --tb=short` stopped before collection because Windows Application Control blocked Python's `_overlapped` module. An existing temporary project environment at `C:\Users\jagriti\AppData\Local\Temp\Fusion-HR-A9-system-venv` imports successfully and contains the project test dependencies. In it, focused leave tests passed 21/21. The full HR test run could not initialize its isolated test database; the first-test `-x` run failed with `psycopg.errors.ConnectionTimeout` for `localhost:5432` on both `::1` and `127.0.0.1`. A direct PostgreSQL connection probe also timed out after three seconds. No HR assertions ran in the full attempt, and no migration or write to the configured database was made. The last successful full HR result remains the earlier recorded 165/165 and 100% coverage run; it was not reproduced in this check.

The untracked `.venv-system` can import Django but is incomplete for this repository. With that environment alone, `manage.py check` stops during app loading because `drf_spectacular` is absent. Combining its interpreter with the existing `.venv` site-packages resolves that import, but then Django initialization stops because neither environment contains the `psycopg`/`psycopg2` driver; `coverage` is also absent. No dependencies were installed and no configuration was changed.

The current OpenAPI file was regenerated to a temporary path with `manage.py spectacular --validate`. A semantic comparison confirmed identical paths, top-level content, and non-schema components; every schema delta between the prior working file and fresh generation was an HR component/enum. The generated file was copied back only after those checks, preserving prior non-HR path/schema content. The exact CI check `manage.py spectacular --fail-on-warn --file <temp>` followed by byte comparison passed. Static integrity found 84 paths, 154 schemas, 94 operations, and 320 local references, with no duplicate YAML keys, duplicate operation IDs, or unresolved local references. Compared with HEAD, the generated file includes 29 HR paths and 53 new schemas, and 10 changed directory/placement paths plus 6 changed shared schemas from the existing generated diff. The fresh generation reproduces those non-HR entries exactly; they were preserved, not independently edited. Approval evidence for the shared generated-file change is still not recorded.

Frontend rechecks passed: `npm run typecheck`; the full frontend suite passed (8 files, 57 tests, including HR routes/leaves); and `npm run build` completed. Vite reported its existing main bundle size warning (503.20 kB minified). No frontend source changed during this sprint.

Using the existing temporary project venv, `manage.py check` passed with no issues, `permission_manifest --check` passed, and the CI-style production deploy check passed with W003/W019 silenced by the repository settings. Ruff check and formatting passed for `modules/hr`; `no_cross_module_fk.py`, `contracts_are_plural.py`, and `nav_matches_routes.py` passed. Import Linter passed (5 contracts kept, 0 broken) when its Python entry point was invoked in-process; Windows Application Control blocked the generated `lint-imports.exe` launcher. No dependency was installed.

The four deployment warnings previously observed were produced under local/test settings. Using the exact CI deployment-check environment with `config.settings.prod`, `manage.py check --deploy --fail-level WARNING` passed with two expected silenced checks (W003 and W019). `config/settings/prod.py` sets HTTPS redirect and HSTS and requires a secret and allowed-host values; `.github/workflows/ci.yml` supplies safe throwaway values. W004/W008/W009/W018 therefore do not reproduce under the prescribed production settings. No security setting was disabled or warning silenced.

Student 2's frozen designs are present in commit `6c541b9501685a25f20135d48cf82c37ae5f91c2`, the 309-test suite is present in `modules/hr/tests/spec/`, and triage is recorded in `docs/09-hr/spec-tests/triage.md`. The latest completed full spec run (before the audit serialization fix) recorded 293 passed and 16 failed. The 14 HTTP status disagreements remain unresolved because source specifications state rejection/validation behavior but do not define HTTP codes; the frozen designs/tests provide 400/422 expectations while the API returns 409. The two date failures were confirmed as an implementation defect in employee audit JSON metadata and fixed; post-fix database-backed tests could not run because PostgreSQL at `localhost:5432` timed out. This worktree contains no evidence of independent review approval or a final Student 2 review output, and none is claimed here.

The Student 2 Prompt A source bundle was prepared outside the repository at `C:\Users\jagriti\OneDrive\Documents\HR-EIS-A9-Student2-Spec-Inputs-20261122\{FR,UC,BR,WF}`. Each strategy folder contains only the problem statement and its one permitted strategy specification. Launch details are in [student2-launch-instructions.md](student2-launch-instructions.md). The bundle prepares a valid fresh-session handoff; it is not itself a design artifact.

The prescribed Student 1 reference script `ops/docs/hr_reference.py`, its generated reference at `docs/09-hr/hr-reference.md`, and a pre-code approved blueprint at `docs/09-hr/hr-blueprint.md` are also absent. The blueprint requirement is explicitly temporal (“before any code”); a new document now cannot satisfy that step retroactively. The committed author history also includes the placeholder identity `Your Name <you@example.com>` on `19f2847`, which should be resolved with the course's accepted evidence process rather than rewriting history here. Accordingly this report records builder evidence and blockers only, not submission completion or an official score.

## 14. Assignment 9 deliverables audit

| Deliverable / gate | Status in this checkout | Evidence / next legitimate action |
|---|---|---|
| HR implementation and builder test suite | Present | Committed under `modules/hr/` and `client/src/modules/hr/`; last historical PostgreSQL run is 165/165 with both coverage gates at 100%, but this sprint could not reproduce it. |
| Builder-test source-ID coverage | Incomplete; Step 7 blocker | The traceability matrix lists 14 CFRs, 107 AFRs, 21 active UCs, 34 active BRs and 17 workflows (193 live IDs). `rg` finds 29 unique cited IDs in `modules/hr/tests` (15 AFRs, 2 UCs, 8 BRs, 4 workflows; no CFRs), leaving 164 live IDs without test citations. Each missing ID needs a real enforcing test before Step 7 can be considered complete; adding labels without asserted behavior is insufficient. |
| Six HR source specifications | Present | Five DOCX specification documents plus the traceability workbook under `specifications/`. |
| Pre-code blueprint and its written Student 2 approval | Missing; cannot be backdated | Domain model and state-machine docs are not substitutes for the pre-code blueprint. No recorded approval was found. |
| Generated live-ID reference script and output | Missing | Required paths are `ops/docs/hr_reference.py` and `docs/09-hr/hr-reference.md`; mapping every live requirement/use-case/workflow to resolving code line is still needed. |
| Quality report | Present at the canonical path and retained in the specification directory; incomplete | Canonical assignment file: `docs/09-hr/hr-quality-report.md`; the original evidence copy remains `docs/09-hr_eis/hr_eis-quality-report.md`. Required mutation tests, fresh-install proof, browser walkthrough, full ID traceability and complete approval records remain missing. |
| Student 1 Step 7 independent review rounds | Missing for latest commit | No completed prescribed scorecard for `35b8d21`; use the official fresh reviewer procedure and save every unedited output. |
| Student 2 Prompt A source-only inputs | Prepared outside repository | Four folders under `C:\Users\jagriti\OneDrive\Documents\HR-EIS-A9-Student2-Spec-Inputs-20261122\{FR,UC,BR,WF}`; see [launch instructions](student2-launch-instructions.md). |
| Student 2 frozen designs | Present | `FR_DESIGN.json`, `UC_DESIGN.json`, `BR_DESIGN.json`, and `WF_DESIGN.json` are committed at `6c541b9`; not regenerated or edited during this review. |
| Student 2 executable tests | Present; latest post-fix rerun blocked | 309 tests are present under `modules/hr/tests/spec/{fr,uc,br,wf}/`. Historical latest completed run is 293 passed/16 failed; after the audit fix, all 309 cases were collected but setup failed on PostgreSQL timeout before assertions. |
| Student 2 triage and run evidence | Present; updated | `docs/09-hr/spec-tests/triage.md` preserves the original baseline, accounts for all 16 latest pre-fix failures, records the audit fix and documents each of the 14 status disagreements. Original and post-fix attempt logs are `hr_eis_final_run.log` and `hr_eis_spec_after_audit_fix.log`. |
| Pair run record | Missing | Prepare for hand-in only (not committed); requires both students' identities, model/provider names, plan/cost, sessions, review outputs, and actual test results. |
| OpenAPI schema ownership | Freshly generated and CI byte-check passed; not committed | Fresh output was compared before replacement; only HR schema/enum components differed from the prior working file. The diff vs HEAD also includes 10 generated directory/placement operations and 6 shared schemas. They match current `spectacular` output exactly and were preserved. Written approval evidence for the shared generated-file change is missing. |
| Deploy security warnings W004/W008/W009/W018 | Resolved by the prescribed environment | Exact CI-style `config.settings.prod` check passed with W003 and W019 silenced as configured; W004/W008/W009/W018 did not recur. No shared setting changes were made. |
| Submission PR | Not permitted yet | The post-fix 309-test run is blocked by PostgreSQL, 14 HTTP status disagreements await an agreed interpretation, and independent review outputs are not present. Do not push/open a PR before the assignment's remaining gates are met. |

## 15. Latest Student 2 spec-suite remediation evidence

The full 309-test run captured before this remediation is preserved at `hr_eis_final_run.log` and reports 293 passed / 16 failed / 0 skipped. The two `TypeError: Object of type date is not JSON serializable` failures were caused after DRF `DateField` parsing: `employees.update_employee_record()` passed Python dates in `before`/`after` to `AuditEvent.details`, a JSONField backed by the PostgreSQL JSON adapter. BR-HR-006 and HR-AFR-102 require consistent service-record updates; the valid API request instead failed during audit persistence. The service now stores date values in audit snapshots as ISO 8601 strings. Both affected spec tests assert that audit value, and `test_employee_audit_serialization.py` covers the conversion without a database.

Source/design review also found that `TEST-BR-040` omitted purpose in addition to documents, `TEST-UC-039` omitted documents in addition to purpose, and `TEST-UC-042` used the non-API key `supporting_documents` while also omitting amount. Those three inputs were corrected to isolate the frozen scenario; no expected status assertions were changed. The full latest run was attempted after these corrections.

Post-fix, `pytest modules/hr/tests/test_employee_audit_serialization.py -q` passed (1). The two requested API tests were attempted and blocked at database setup by PostgreSQL connection timeout at `localhost:5432`. A full `pytest modules/hr/tests/spec/ -q --tb=no` attempt collected/executed the suite harness but all 309 cases errored at database setup for the same connection timeout; output is preserved at `hr_eis_spec_after_audit_fix.log`. This is not a post-fix pass/fail assertion result.

The following post-fix checks passed in the existing temporary project environment: Django system check; permission manifest check; `ruff check modules/hr`; `ruff format --check modules/hr` (69 files formatted); the registry regression test; 35 state-machine tests; the new audit serializer unit test; and `git diff --check` after accounting for the repository's existing CRLF files. No database migration was run. The full spec suite must be rerun against PostgreSQL before the outcome of the date fix can be confirmed. The 14 status expectations remain unchanged; their per-case source/design evidence and interpretation are recorded in the triage log. No 10/10 rating is claimed.
