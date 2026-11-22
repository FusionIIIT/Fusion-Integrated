# PSM Module Quality Report

Date: 2026-11-22
Module: `psm` (`Procurement & Stores Management`)
Environment Mode: `module-only` (`Fusion_System_Administrator` and `Fusion-Integrated` present; no `Fusion-client` checkout)

## 1. Blueprint Approval Record

On 2026-11-22, the user explicitly approved `docs/09-psm/psm-blueprint.md` before implementation began:

> "yes i approve the entirety of `docs/09-psm/psm-blueprint.md` so you can proceed now"

All six spec clarifications (Procurement Committee metadata via `ps_admin`/`SectionHead_PS`, Vendor master-data without a separate vendor login pool, department scoping with strict least-privilege `ROLE_GRANTS`, configurable default `PsmPolicy` values seeded via `seed_psm_policy`, standard positive-value input validation without citing retired `BR-PSM-002`, and literal `BW-PSM-01` internal-issue GRN sequence) were explicitly confirmed on 2026-11-22.

## 2. Specification Coverage and Traceability

Generated and verified by `ops/docs/psm_reference.py` (`docs/09-psm/psm-reference.md`):

- **180 / 180 live specification IDs** verified with live `file:line` links in both implementation and tests:
  - `CFR-PSM-001` through `CFR-PSM-020` (20/20)
  - `AFR-PSM-001` through `AFR-PSM-092` (92/92)
  - 25 active `BR-PSM-*` rules (retired `BR-PSM-002`, `BR-PSM-011`, `BR-PSM-016` absent from code and tests)
  - 32 active `PSM-UC-*` use cases (31 actor-triggered + 1 event-triggered `PSM-UC-035`; retired `PSM-UC-004`, `PSM-UC-006`, `PSM-UC-018` absent from code and tests)
  - 9 business workflows (`BW-PSM-01`..`08`, `BW-PSM-10`) and 2 cross-cutting workflows (`CW-PSM-01`, `CW-PSM-02`)
- **Retired ID check:** 0 occurrences of any retired ID in `modules/psm/`, `client/src/modules/psm/`, `client/e2e/psm/`, or `docs/09-psm/psm-reference.md`.

## 3. Verification Commands and Observed Output

| Check | Command | Exit | Key Observed Output |
| --- | --- | --- | --- |
| PSM pytest + branch coverage | `pytest modules/psm --cov=modules/psm --cov-branch --cov-report=term-missing --cov-fail-under=90` | `0` | `Required test coverage of 90% reached. Total coverage: 91.18%` / `73 passed in 203.54s` (`modules/psm/domain/`: 100% branch coverage across all 8 files) |
| Platform & Placement regression | `pytest core modules/placement -q --no-cov` | `0` | 100% passed (zero regressions in `core` or `modules/placement`) |
| Ruff lint | `ruff check .` | `0` | `All checks passed!` |
| Import-linter architecture | `lint-imports` | `0` | `Contracts: 5 kept, 0 broken.` (`Layering inside psm KEPT`, `domain/ must not import Django, DRF or Celery KEPT`) |
| Cross-module FK check | `python ops/checks/no_cross_module_fk.py` | `0` | `no cross-module foreign keys` |
| Plural contracts check | `python ops/checks/contracts_are_plural.py` | `0` | `all contract getters are plural` |
| Nav-to-routes check | `python ops/checks/nav_matches_routes.py` | `0` | `nav items and client routes agree` |
| Permission manifest check | `python manage.py permission_manifest --check` | `0` | `permission manifest matches the registries` (43 PSM permissions, 22 designations) |
| Migration drift check | `python manage.py makemigrations --check --dry-run` | `0` | `No changes detected` |
| OpenAPI schema generation | `python manage.py spectacular --fail-on-warn --file openapi/fusion-integrated.v1.yaml` | `0` | Zero warnings, zero errors |
| Production deploy check | `DJANGO_SETTINGS_MODULE=config.settings.prod ... python manage.py check --deploy --fail-level WARNING` | `0` | `System check identified no issues (2 silenced).` |
| Reference link verification | `python ops/docs/psm_reference.py` | `0` | `Verified 180 live spec IDs -> docs/09-psm/psm-reference.md` |
| Client typecheck + Vitest + Vite build | `cd client && npm run typecheck && npm test && npm run build` | `0` | 0 TS errors (including `e2e`), 19 test files / 87 tests passed, `built in 9.08s` (each lazy PSM page chunk 1.25–2.03 kB gzip, total PSM < 20 kB gzip) |
| Hygiene audit | Automated scan across all PSM backend, frontend, E2E, ops, and doc files | `0` | `Hygiene issues: 0 []` (zero lint/type/coverage suppressions, untyped casts, debug logs, unfinished markers, or multiline docstrings) |

## 4. Mutation Proof (Step 5.15 — Five Critical Rules Broken on Purpose)

Each rule was broken one at a time in `modules/psm/domain/` (backed up outside the repository and restored immediately after each run):

1. **Self-approval ban (`BR-PSM-005`)** in `modules/psm/domain/approval_policy.py` (`if requestor_user_id == actor_user_id:` disabled): `exit=1`, caught by `modules/psm/tests/test_domain.py::test_approval_policy_method_final_priority_and_sla`.
2. **Unverified vendor gate (`BR-PSM-012`)** in `modules/psm/domain/vendor_rules.py` (`if not is_verified:` disabled): `exit=1`, caught by `modules/psm/tests/test_domain.py::test_vendor_master_validation_and_gate`.
3. **Stock adjustment zero-delta guard (`BR-PSM-026`)** in `modules/psm/domain/stock_rules.py` (`if delta == 0:` disabled): `exit=1`, caught by `modules/psm/tests/test_domain.py::test_stock_adjustment_blocks_zero_and_below_reserved`.
4. **Open discrepancy payment hold (`BR-PSM-017` / `BR-PSM-022`)** in `modules/psm/domain/finance_rules.py` (`if data.has_open_discrepancy:` disabled): `exit=1`, caught by `modules/psm/tests/test_domain.py::test_three_way_match_and_payment_release_rules`.
5. **State machine invalid transition guard** in `modules/psm/domain/state_machine.py` (`if transition is None:` disabled): `exit=1`, caught by all 5 parametrized cases of `modules/psm/tests/test_state_machine.py::test_every_illegal_transition_is_refused`.

## 5. Adversarial and Concurrency Testing Summary

- **Plain-user and privilege-escalation suites** (`test_plain_user.py`, `test_privilege_escalation.py`): verified every PSM endpoint refuses unauthenticated callers (401), authenticated users without the `psm` module grant (403), and authenticated PSM users lacking the specific action permission (403); verified zero permission-string drift between views and `registry.py`.
- **Department scoping isolation** (`test_scoping_isolation.py`): verified CSE `deptadmin_cse` / `HOD (CSE)` cannot view or mutate ECE indents, stock locations, or transfers, and generic `dept_admin` falls back safely to `UserRef.department`.
- **Real-thread Postgres concurrency** (`test_concurrency.py`): verified with `threading.Barrier` that concurrent stock reservations against the same balance and concurrent full-amount payments against the same invoice allow exactly one winner and refuse the race contender (`select_for_update(of=("self",))` + DB check constraints).
- **Adversarial cases** (`test_adversarial.py`, `test_coverage_and_traceability.py`): verified self-approval refusal, unverified-vendor refusal, open-discrepancy payment hold, CSV formula-injection neutralization (`'=` prefix), invalid evidence Drive-link rejection, missing active policy refusal, and `psm_export` HTTP 429 rate-limit enforcement.
- **Query budgets** (`test_query_budgets.py`): verified constant query count (no N+1 scaling between 1 and 20 rows) on list and dashboard endpoints.
- **Celery schedule & idempotency** (`test_schedule.py`): verified `BEAT_SCHEDULE` and `TASK_ROUTES` registration, idempotent SLA sweep and scheduled-report execution, and `psm_readiness` / `seed_psm_policy` management commands.

## 6. Security Self-Audit

- **Authentication & Authorization:** Every PSM view declares `HasModuleGrant("psm")` and a specific `HasPermission("psm.<resource>.<action>")`; no `AllowAny` or unauthenticated endpoints exist.
- **CSRF & Throttling:** Cookie sessions enforce CSRF via platform middleware; write views apply `psm_write` throttle scope and CSV export applies `psm_export` throttle scope via `PrincipalScopedThrottle`.
- **Input & File Safety:** Positive quantity/cost validation enforced on all financial/stock inputs; discrepancy evidence URLs validated through `core.files.drive.parse_drive_link` (HTTPS Google Drive only) and filenames sanitized through `core.files.validators.sanitise_filename`; CSV exports escape formula-leading characters (`=`, `+`, `-`, `@`, tab, CR).
- **Data Integrity & Auditability:** All state transitions flow through `modules/psm/domain/state_machine.py`; every mutation emits an append-only `PsmAuditLog` entry (`BR-PSM-019`) and deduplicated `PsmNotification` outbox row (`BR-PSM-006`).
- **Cross-Module Isolation:** Zero cross-module foreign keys; public surface exposed strictly through plural getters in `modules/psm/contracts.py` (`get_indent_summaries`, `get_pending_receipt_obligations`).

## 7. Items Not Run in This Environment

The following runtime-stack steps were not executed because the full multi-service Docker/IAM/browser stack was not started in this session:

- **Live IAM permission seeding (`seed_iam_permissions`):** `registry/permissions.json` is generated and verified via `permission_manifest --check`; run `manage.py seed_iam_permissions --manifest <path-to-registry/permissions.json>` against the running `Fusion_System_Administrator` IAM database during deployment.
- **Fresh throwaway database install proof (`fusion_integrated_fresh`):** Not run against a separate throwaway Postgres database in this session; `0001_initial.py` migration ran cleanly during pytest DB creation and `makemigrations --check --dry-run` reported `No changes detected`.
- **Live Playwright E2E suite (`make e2e`) and interactive browser walkthrough:** Playwright specs (`client/e2e/psm/office-pages.spec.ts` and `client/e2e/psm/procurement-flow.spec.ts`) are written and pass TypeScript typechecking (`tsc --noEmit -p e2e`), but were not executed against a live browser/backend stack. Please run `make e2e` and walk the `/psm` routes in a live stack before merging.
