# HR-EIS quality report — builder evidence

This report records builder evidence; it is not an independent review scorecard or a claim that the assignment has passed. The branch is `module/hr_eis`; commit `28e4815389a234b6e51bc32eca82846c8db3d1ff` removes the shared enum override and updates an obsolete navigation-test fixture. A generated OpenAPI file remains modified in the worktree and was intentionally not included in that commit. Semantic comparison found 29 HR API paths and 53 HR schemas added, with no existing paths deleted or changed; existing entries were reordered by regeneration. `.venv-system/` is an untracked local environment excluded from commits and reviewer copies.

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

Static review confirms module grant and permission gates at the HR views, service-level permission checks on leave writes, actor/current-authority matching, submitter self-approval refusal, scoped leave selectors, positive duration/justification validation, and transactional balance deduction with a locked balance. The leave-balance route/panel and route-guard test use the registered `hr.leave_balance.manage` key. The three OpenAPI enum-name collisions are resolved in HR serializer annotations; the deploy check now reports only the four deployment security warnings (`security.W004`, `security.W008`, `security.W009`, `security.W018`) under local/test settings. Dedicated concurrency, CSRF, and ledger-trigger probes were not verified. No shared security or schema setting was altered.

The registered client module and all HR pages, API hooks/types, route guards, and leave page tests now live under `client/src/modules/hr/`. The former split under `client/src/modules/hr_eis/` was removed in the current remediation worktree.

## 7. Fresh-install proof

Not run. The documented procedure requires Docker Compose, a disposable PostgreSQL database, IAM seeding, and a readiness check. The local Windows PostgreSQL service is reachable now, but the full stack/IAM proof was not run. The repository-root `.env` is ignored and contains the local DB settings. No services were started or modified; the existing `fusion_integrated` database was not migrated.

## 8. Browser walkthrough

Not run. The IAM/API stack was unavailable, and there are no HR-EIS Playwright journeys. Although PostgreSQL connectivity is now verified, the current leave frontend unit tests do not substitute for the required role-by-role and keyboard walkthrough.

## 9. Scheduled tasks

`hr.deliver_notifications` and `hr.generate_pending_reminders` are registered in the current schedule. The latter now considers leave requests as well as claims. Neither task was run manually against a database; effect and idempotency remain unverified in this environment.

## 10. Known gaps

No direct written Student 2 approval for the pre-code blueprint or each required shared-file change is present in this record. Specification silence listed in section 5 is not treated as an accepted gap. Remaining verification gaps include missing journeys, incomplete full-module requirement-ID mapping, incomplete operator/browser proofs, and a multi-file migration history for an unmerged module. Coverage gates were met at 100% in the last complete PostgreSQL run. The configured `fusion_integrated` database still has unapplied HR migrations; it was deliberately not migrated during validation. No migration files were removed or rewritten.

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

No completed prescribed review scorecard is recorded. A fresh reviewer session was started against commit `19f2847`; its first checkout was rejected because it lived beneath the home `.codex` instruction tree. A clean checkout was recreated under `C:\Temp`, but the reviewer could not run required gates because `make`, the project `.venv`, and DOCX tooling were unavailable; no scorecard was returned. `new-module-prompt.md` §10 prohibits the builder from scoring its own work. The current remediation changes need a separate commit and fresh reviewer session.

## Gate results

| Command | Result and output |
|---|---|
| `manage.py check` (`config.settings.test`) | Passed: “System check identified no issues (0 silenced).” |
| PostgreSQL connectivity probe (`config.settings.test`) | Passed: connected to PostgreSQL at `localhost:5432`, database `fusion_integrated`, role `fusion_admin`; credentials were not printed. |
| PostgreSQL test database preflight | Before HR tests, `test_fusion_integrated` was absent; role reported `CREATEDB=True`, `SUPERUSER=False` after the user's grant. HR test and coverage runs completed against the isolated test DB. |
| `manage.py check --database default` | Passed: “System check identified no issues (0 silenced).” |
| `manage.py showmigrations hr` | Read-only: `0001_initial`, `0002_audit_event_immutable`, and `0003_leave_management` are unapplied on the current `fusion_integrated` database. No `migrate` command was run against it. |
| `manage.py makemigrations hr --check --dry-run --noinput` | Passed: “No changes detected in app 'hr'.” |
| `manage.py permission_manifest --check` | Passed: “permission manifest matches the registries”. |
| `manage.py spectacular --validate --file <temp>` before module-local fix | Schema validation passed, 0 errors; 3 `drf_spectacular.W001` naming collisions (`action`, `employee_category`, and `request_type`). |
| `manage.py spectacular --validate --file <temp>` after module-local fix | Passed: 0 errors and 0 warnings. Schema was written only to a temp path; the working-tree OpenAPI file was not touched. |
| `manage.py check --deploy --fail-level WARNING` | Failed with 4 deployment security warnings: `security.W004`, `security.W008`, `security.W009`, and `security.W018`. The 3 `drf_spectacular.W001` warnings are absent. No shared settings were changed to suppress warnings. |
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
| Final PostgreSQL HR/coverage rerun | Not completed in this session. `.venv-system` is incomplete (`coverage` and `sqlparse` missing); the prior temporary test venv path is unavailable here. No packages were installed. The previous PostgreSQL evidence above remains the last successful backend run. |
| Final structural-check rerun | Not completed in this session: the available system Python lacks Django, and `.venv-system` lacks `sqlparse`; `ops/checks/no_cross_module_fk.py` and `ops/checks/nav_matches_routes.py` stop during Django import/setup. These checks passed in the earlier validation run recorded above. |
| Module-local OpenAPI schema annotation | Passed `manage.py spectacular --validate`: 0 errors and 0 warnings after naming colliding HR choice-field schemas locally. |
| Current `manage.py check` | Passed: “System check identified no issues (0 silenced).” |
| Current migration consistency rerun | `manage.py makemigrations hr --check --dry-run --noinput` did not complete promptly and was interrupted; no migration was run against the configured database. The previous completed result was “No changes detected”. |
| Current permission manifest check | Passed: “permission manifest matches the registries”. |
| Current focused frontend tests | Passed: `npm run test -- src/modules/hr/routes.test.tsx src/modules/hr/pages/LeavesPage.test.tsx`; 2 files, 19 tests after the folder move. |
| Current frontend typecheck | Passed: `npm run typecheck` (application and E2E TypeScript projects). |
| Current Ruff and whitespace checks | Passed: Ruff check and formatting for `modules/hr/api/serializers.py`; `git diff --check` passed. |
| Current full HR backend rerun | Not run this turn; the preceding migration consistency check stalled before reaching pytest. Previous PostgreSQL run: 165/165 and 100% coverage gates. |

The model and workflow references are documented in `hr_eis-domain-model.md` and `hr_eis-state-machine.md`. The required approved blueprint, generated live-ID reference script, complete quality-report evidence, pair run record, and formal review scorecards are not present yet.
