# HR-EIS quality report — builder evidence

This report records builder evidence; it is not an independent review scorecard or a claim that the assignment has passed. The branch is `module/hr_eis`; the pre-submission base `HEAD` was `5595be6628b4cdc6f8b47cf74bac267a2470f780`. A committed, clean checkout is required before Student 2's independent review. The final OpenAPI regeneration also contains unrelated `/me` and Placement schema rewrites, so that shared generated file is intentionally excluded from the focused HR-EIS commit and remains an unresolved working-tree change.

## 1. Repository gates

`make check` and `make check-client` were not invoked because `make` is not installed in this Windows environment. Their relevant available components were run directly; see the gate results below. The deployment check with local settings fails on the OpenAPI enum warning and deployment security warnings; shared configuration was not changed.

## 2. Backend coverage

Both prescribed coverage gates now pass against PostgreSQL at 100% statement and branch coverage. Before this test expansion, `modules/hr` was 62.57% and `modules/hr/domain` was 71.09%. Added meaningful state-machine, service, selector/contract, serializer, task, model-invariant, and authenticated API workflow tests; all 165 HR tests pass. Exact baseline uncovered lines/arcs and post-test results are in [the HR coverage analysis](hr_eis-coverage-analysis.md). PostgreSQL is reached using the ignored root `.env`; Django uses the isolated `test_fusion_integrated` database. The configured `fusion_integrated` database was not tested against or migrated.

## 3. Test inventory and journeys

The HR suite now contains 165 tests across the existing and added module test files. `pytest modules/hr -q --tb=short` passed all 165 against PostgreSQL. The broader `pytest -q --tb=short` completed previously with one failure: `modules/accesscontrol/tests/test_navigation.py::test_seed_modules_retires_a_module_no_code_declares_any_more`. Its fixture uses `hr`, which is now declared by `modules/hr/registry.py`, so `seed_modules` correctly retains it as `planned` instead of deprecating it. This is a stale fixture assumption, not an HR production defect; the unrelated shared test was not modified.

Leave requirement references appear in `test_leaves.py`: HR-AFR-029–043, HR-UC-003/004, BR-HR-007–011/023/024/034, BW-HR-01/02/03, CW-HR-01. Parameterized assertions cover the six types, required fields, balance/eligibility, route/deduction, rejection, audit/ledger immutability, and reminder deduplication. The broader module's test-to-ID inventory remains incomplete. There is no `modules/hr/tests/test_journeys.py`, and `client/e2e/hr` does not exist; end-to-end use-case coverage is not complete.

Frontend test results: 8 files, 57 tests passed. File counts: download 10; Placement hooks 4; auth 6; HR route guards 15; login 17; Placement companies 1; HR-EIS leaves 4. These are builder tests, not Student 2's independent spec tests.

## 4. Break-on-purpose checks

The five mutation checks required by Step 5.15 were not run. No production file was intentionally altered to test whether a test fails.

## 5. Adversarial pass

The leave workflow review found two defects and corrected them: configured leave routes could exceed one forwarding traversal, and the scheduled pending-reminder task processed claims but not leave requests. The leave state machine/configuration now caps routes at two authorities and refuses a second forward; the reminder task now creates a deduplicated, audited leave reminder after the configured delay. New tests exercise valid and invalid balance changes, missing eligibility/balance/route conditions, authority checks, approval-time revalidation, audit-ledger immutability, reminders, and authenticated API workflows. All pass against PostgreSQL. No production code needed changes during this coverage pass. The full Step 5.11 adversarial checklist remains incomplete.

Questions left to the pair: the specifications do not define entitlement/accrual formulas, leave date-range or backdating semantics, or a cancellation workflow. BR-HR-009 states that the exact approval matrix is institutional policy/configuration outside the problem statement. The assignment/task workspace uses `hr_eis` in the branch and documentation path, while the module registry and API permission prefix use `hr`; the module code value supplied in Step 1 is not recorded here. Confirm the assigned module code before the independent reviewer applies folder-boundary checks. No behavior was invented for these questions, and none is recorded as an approved gap.

## 6. Security self-audit

Static review confirms module grant and permission gates at the HR views, service-level permission checks on leave writes, actor/current-authority matching, submitter self-approval refusal, scoped leave selectors, positive duration/justification validation, and transactional balance deduction with a locked balance. Final diff inspection found a client permission-key typo on the leave-balance route and panel; both now use the registered `hr.leave_balance.manage` key, and the route guard test asserts that exact key. Route-guard and database-backed API permission/leave tests passed in the earlier PostgreSQL run. Dedicated concurrency, CSRF, and ledger-trigger probes were not verified. Deployment checks previously reported `drf_spectacular.W001` plus `security.W004`, `security.W008`, `security.W009`, and `security.W018` under local/test settings; no shared security setting was altered.

The registered client module is `hr`, but the route module's page imports and their API hooks/types live under `client/src/modules/hr_eis/`, while duplicate HR hooks/types also exist under `client/src/modules/hr/`. This split does not match the review prompt's single module-folder shape if the assigned code is `hr`; the implementation was preserved pending confirmation of the assigned module code.

## 7. Fresh-install proof

Not run. The documented procedure requires Docker Compose, a disposable PostgreSQL database, IAM seeding, and a readiness check. The local Windows PostgreSQL service is reachable now, but the full stack/IAM proof was not run. The repository-root `.env` is ignored and contains the local DB settings. No services were started or modified; the existing `fusion_integrated` database was not migrated.

## 8. Browser walkthrough

Not run. The IAM/API stack was unavailable, and there are no HR-EIS Playwright journeys. Although PostgreSQL connectivity is now verified, the current leave frontend unit tests do not substitute for the required role-by-role and keyboard walkthrough.

## 9. Scheduled tasks

`hr.deliver_notifications` and `hr.generate_pending_reminders` are registered in the current schedule. The latter now considers leave requests as well as claims. Neither task was run manually against a database; effect and idempotency remain unverified in this environment.

## 10. Known gaps

No gap has written Student 2 approval. Specification silence listed in section 5 is not treated as an accepted gap. Remaining implementation/verification gaps include the broader suite's stale HR fixture failure, missing journeys, incomplete full-module requirement-ID mapping, incomplete operator/browser proofs, and a multi-file migration history for an unmerged module. Coverage gates are met at 100%. The configured `fusion_integrated` database still has unapplied HR migrations; it was deliberately not migrated during validation. No migration files were removed or rewritten.

## 11. Required approvals

The user reports that labmate approval to proceed has been obtained. No dated/linkable written approval from Student 2 is present in the repository evidence, and the scope of that reported approval is not specified; this report does not treat it as approval for the pre-code blueprint or each shared-file change. The pre-code blueprint was not created before implementation and cannot be backdated. Shared integration changes currently present in the worktree are:

- `config/settings/base.py` — HR registration, write throttle, and HR enum names;
- `config/urls.py` — HR API registration;
- `config/celery.py` — HR task registration;
- `.importlinter` — HR module boundaries;
- `client/src/app/registry.ts` — HR client registration;
- `registry/permissions.json`, `docs/02-iam/permission-catalog.generated.md`, and `openapi/fusion-integrated.v1.yaml` — generated manifests/schema.

No Python or npm dependency was added to the repository manifests. The missing pre-code blueprint approval cannot be backdated or recreated as if it happened. For the OpenAPI warning, drf-spectacular itself recommends an `ENUM_NAME_OVERRIDES` entry; changing that shared setting and regenerating the schema still requires Student 2's recorded approval.

## 12. Review rounds

No prescribed review round has been run and no scorecard is recorded. `new-module-prompt.md` §10 prohibits the builder from scoring its own work. The prescribed reviewer is a fresh session on a clean committed revision; the current dirty worktree is not eligible. The last reviewer's scorecard belongs in the pull request description, not this report.

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
| `manage.py spectacular --validate --file <temp>` | Schema validation passed, 0 errors; 1 warning, `drf_spectacular.W001` duplicate `action` choice-set naming. |
| `manage.py check --deploy --fail-level WARNING` | Failed with `drf_spectacular.W001`, `security.W004`, `security.W008`, `security.W009`, and `security.W018` under local/test settings (5 warnings, 2 silenced). No shared settings were changed. |
| `npm run lint` | Could not run: package script calls `eslint .`, but `eslint` is not declared in `client/package.json` and no ESLint executable is installed. No dependency/configuration change was made without approval. |
| `pytest modules/hr -q --tb=short` | Passed: 165 tests against PostgreSQL. |
| `pytest -q --tb=short` | One failure: `modules/accesscontrol/tests/test_navigation.py::test_seed_modules_retires_a_module_no_code_declares_any_more`; the fixture uses code `hr`, which is now declared. The rest of the broader suite passed. No unrelated test was changed. |
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

The model and workflow references are documented in `hr_eis-domain-model.md` and `hr_eis-state-machine.md`. The required approved blueprint, generated live-ID reference script, complete quality-report evidence, pair run record, and formal review scorecards are not present yet.
