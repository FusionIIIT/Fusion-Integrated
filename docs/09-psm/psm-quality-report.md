# PSM Module Quality Report

Date: 2026-11-23
Module: `psm` (`Procurement & Stores Management`)
Environment Mode: `module-only` (`Fusion_System_Administrator` and `Fusion-Integrated` present; no `Fusion-client` checkout)

---

## 1. Approvals & Verification Gate Summary

### Blueprint Approval Record (Phase 2 -> Phase 3)

On 2026-11-22, the user explicitly approved `docs/09-psm/psm-blueprint.md` before implementation began:

> "yes i approve the entirety of `docs/09-psm/psm-blueprint.md` so you can proceed now"

All six Phase 1 clarifications (Procurement Committee metadata recorded by `ps_admin` / `SectionHead_PS`, Vendor master-data without a separate vendor authentication pool, department scoping with strict least-privilege `ROLE_GRANTS`, configurable `PsmPolicy` defaults seeded via `seed_psm_policy`, positive-value validation without citing retired `BR-PSM-002`, and literal `BW-PSM-01` internal-issue GRN sequence) were confirmed in writing on 2026-11-22. Pre-approved shared-file registrations (`config/settings/base.py`, `config/urls.py`, `config/celery.py`, `.importlinter`, `client/src/app/registry.ts`, `client/e2e/accounts.ts`, `ops/docs/psm_reference.py`, and regenerated `openapi/fusion-integrated.v1.yaml`, `registry/permissions.json`, `docs/02-iam/permission-catalog.generated.md`) match Section (h) of `docs/09-psm/psm-blueprint.md`.

### Approved Answers to Independent Review Round 3 Section 5 (2026-11-23)

1. **Traceability Matrix (`06_PSM_Traceability_Matrix_v1.1_FINAL.xlsx`):** Confirmed that the upstream `.xlsx` spec file in `PSM_SPECS/` is kept untouched as read-only spec input, while `docs/09-psm/psm-blueprint.md` and `docs/09-psm/psm-reference.md` provide the authoritative populated forward and reverse traceability across all 180 live specification IDs.
2. **Event-Triggered `PSM-UC-035` in E2E:** Confirmed that running `deliver_psm_notifications` (and triggering lifecycle notification creation during procurement transitions) and asserting the rendered notification in the UI on `/psm/dashboard` satisfies E2E verification for event-triggered `PSM-UC-035`.

### Verification Commands & Observed Results (`make check`, `make check-client`, `e2e`)

| Check | Command | Exit | Key Observed Output |
| --- | --- | --- | --- |
| Full repo check (`manage.py check`) | `python manage.py check` | `0` | `System check identified no issues (0 silenced).` |
| Migration drift check | `python manage.py makemigrations --check --dry-run` | `0` | `No changes detected` |
| Ruff lint | `ruff check .` | `0` | `All checks passed!` |
| Import-linter architecture | `lint-imports` | `0` | `Analyzed 280 files, 1032 dependencies.` · `Contracts: 5 kept, 0 broken.` |
| Cross-module FK check | `python ops/checks/no_cross_module_fk.py` | `0` | `no cross-module foreign keys` |
| Plural contracts check | `python ops/checks/contracts_are_plural.py` | `0` | `all contract getters are plural` |
| Nav-to-routes check | `python ops/checks/nav_matches_routes.py` | `0` | `nav items and client routes agree` |
| Permission manifest check | `python manage.py permission_manifest --check` | `0` | `permission manifest matches the registries` |
| OpenAPI schema sync check | `manage.py spectacular --fail-on-warn` + diff vs `openapi/fusion-integrated.v1.yaml` | `0` | Zero warnings; `openapi schema matches the code` |
| Production deploy security check | `DJANGO_SETTINGS_MODULE=config.settings.prod ... manage.py check --deploy --fail-level WARNING` | `0` | `System check identified no issues (2 silenced).` |
| Platform & Placement regression | `pytest core modules/placement -q --no-cov` | `0` | 100% passed (zero regressions) |
| Spec reference determinism | `python ops/docs/psm_reference.py` (run twice) | `0` | `Verified 180 live spec IDs -> docs/09-psm/psm-reference.md` (`git status` clean) |
| Client typecheck + Vitest + build | `cd client && npm run typecheck && npm test && npm run build` | `0` | `0` TS errors (`tsc --noEmit && tsc --noEmit -p e2e`), `19 passed (19)` files / `87 passed (87)` tests in `55.85s`, `built in 8.45s` |
| PSM Vite lazy chunks | `vite build` output | `0` | Each lazy PSM page chunk `0.86–2.24 kB` gzip (combined PSM `< 25 kB` gzip, vs. `150 kB` budget) |
| Live Playwright E2E | `cd client && npx playwright test --workers=1` | `0` | `38 passed` across 6 spec files (`29` PSM tests + `9` shared/placement tests) |
| Single-line comment & hygiene audit | Automated scan across `modules/psm/`, `client/src/modules/psm/`, `client/e2e/psm/`, `ops/docs/psm_reference.py` | `0` | Zero consecutive `#` or `//` comment lines; zero lint/type/coverage suppressions, unfinished markers, or AI attribution |

---

## 2. Branch Coverage Runs (Step 5.14)

### Gate 1 — Whole `modules/psm` (>= 90% Branch Coverage)

Command:

```powershell
.venv\Scripts\python.exe -m pytest modules/psm --ignore=modules/psm/tests/spec --cov=modules/psm --cov-branch --cov-report=term-missing --cov-fail-under=90
```

Observed output:

```text
........................................................................ [ 78%]
....................                                                     [100%]
=============================== tests coverage ================================
______________ coverage: platform win32, python 3.12.15-final-0 _______________

Name                                                           Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------------------------------------
modules\psm\__init__.py                                            1      0      0      0   100%
modules\psm\api\__init__.py                                        0      0      0      0   100%
modules\psm\api\serializers.py                                   432      1      2      1    99%   12
modules\psm\api\urls.py                                            6      0      0      0   100%
modules\psm\api\views_finance_reports.py                         141      0      8      0   100%
modules\psm\api\views_indents.py                                 123      0     12      0   100%
modules\psm\api\views_procurement.py                             196      4     14      1    97%   73->75, 83-91
modules\psm\api\views_stock.py                                   135      2      8      0    99%   259-260
modules\psm\apps.py                                                5      0      0      0   100%
modules\psm\contracts.py                                          30      0      4      0   100%
modules\psm\domain\__init__.py                                     0      0      0      0   100%
modules\psm\domain\approval_policy.py                             54      0      8      0   100%
modules\psm\domain\errors.py                                      17      0      0      0   100%
modules\psm\domain\finance_rules.py                               52      0     24      0   100%
modules\psm\domain\indent_rules.py                                50      0     22      0   100%
modules\psm\domain\receipt_rules.py                               24      0     18      0   100%
modules\psm\domain\state_machine.py                               90      0      4      0   100%
modules\psm\domain\stock_rules.py                                 32      0     10      0   100%
modules\psm\domain\vendor_rules.py                                39      0     18      0   100%
modules\psm\management\__init__.py                                 0      0      0      0   100%
modules\psm\management\commands\__init__.py                        0      0      0      0   100%
modules\psm\management\commands\deliver_psm_notifications.py       7      0      0      0   100%
modules\psm\management\commands\psm_readiness.py                  11      0      4      0   100%
modules\psm\management\commands\run_psm_scheduled_reports.py       7      0      0      0   100%
modules\psm\management\commands\run_psm_sla_sweep.py               8      0      0      0   100%
modules\psm\management\commands\seed_psm_policy.py                 9      0      0      0   100%
modules\psm\models\__init__.py                                     9      0      0      0   100%
modules\psm\models\finance.py                                     41      1      0      0    98%   71
modules\psm\models\indent.py                                      76      3      0      0    96%   66, 86, 108
modules\psm\models\policy.py                                      29      2      0      0    93%   11, 57
modules\psm\models\procurement.py                                 83      2      0      0    98%   49, 173
modules\psm\models\reporting.py                                   70      3      0      0    96%   61, 88, 115
modules\psm\models\stock.py                                       81      3      0      0    96%   24, 41, 81
modules\psm\models\tender.py                                      40      1      0      0    98%   37
modules\psm\models\vendor.py                                      38      2      0      0    95%   37, 61
modules\psm\registry.py                                           20      0      2      0   100%
modules\psm\schedule.py                                            3      0      0      0   100%
modules\psm\selectors\__init__.py                                  0      0      0      0   100%
modules\psm\selectors\dashboard.py                                15      0      0      0   100%
modules\psm\selectors\reports.py                                  46      3     20      3    91%   52, 74, 103
modules\psm\selectors\scoping.py                                 120     11     48     10    88%   76, 111, 146, 166, 185, 192, 212, 218, 241, 259-260
modules\psm\selectors\stock.py                                    36      1     14      1    96%   72
modules\psm\services\__init__.py                                   0      0      0      0   100%
modules\psm\services\approvals.py                                112     20     34     10    78%   23-49, 57, 98, 103, 108, 110, 153, 163, 183, 195-208, 227
modules\psm\services\common.py                                    67     10     14      3    84%   34, 37-40, 77, 79, 81, 142-143
modules\psm\services\discrepancies.py                            146     10     44     10    89%   53, 75, 149, 222, 229, 257, 259, 263, 325, 348
modules\psm\services\finance.py                                  100     11     16      7    84%   46, 48, 62-63, 144, 146, 178, 188, 222-223, 267
modules\psm\services\indents.py                                  107      9     24      6    87%   95->93, 155-159, 199, 213->215, 244-245, 301
modules\psm\services\policy.py                                    31      3      6      3    84%   24, 29, 104
modules\psm\services\procurement.py                               89     12     34     13    80%   32, 39, 72, 79, 85, 134, 137, 148, 171, 195, 201->205, 206, 208
modules\psm\services\receipts.py                                 125      9     50     15    86%   32, 44, 46, 61, 63, 85, 87, 108->117, 122->126, 225->229, 229->240, 242->exit, 263->274, 299, 306
modules\psm\services\reports.py                                   92      5     22      6    90%   35, 100, 104, 134->140, 136, 169
modules\psm\services\stock.py                                    107     17     28     11    78%   38-39, 60-61, 88, 141, 143, 149, 174, 176, 180, 221-227, 264, 267, 270
modules\psm\services\tenders.py                                  100     17     32     15    76%   23, 25, 30, 56, 78, 80, 85, 87, 95-96, 121, 126, 130, 136, 165, 170, 175
modules\psm\services\transfers.py                                 99     10     28      9    85%   52-53, 71->75, 109, 111, 116, 120, 124-125, 199, 204
modules\psm\services\vendors.py                                   64      9     18      7    80%   55-56, 100, 101->103, 103->95, 105, 115, 117-119, 145
modules\psm\tasks.py                                              12      0      0      0   100%
----------------------------------------------------------------------------------------------------------
TOTAL                                                           3427    181    590    131    92%
Required test coverage of 90% reached. Total coverage: 92.03%
92 passed in 353.85s (0:05:53)
```

### Gate 2 — `modules/psm/domain` (>= 95% Branch Coverage)

Command:

```powershell
.venv\Scripts\python.exe -m pytest modules/psm --ignore=modules/psm/tests/spec --cov=modules/psm/domain --cov-branch --cov-report=term-missing --cov-fail-under=95
```

Observed output:

```text
........................................................................ [ 78%]
....................                                                     [100%]
=============================== tests coverage ================================
______________ coverage: platform win32, python 3.12.15-final-0 _______________

Name                                    Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------
modules\psm\domain\__init__.py              0      0      0      0   100%
modules\psm\domain\approval_policy.py      54      0      8      0   100%
modules\psm\domain\errors.py               17      0      0      0   100%
modules\psm\domain\finance_rules.py        52      0     24      0   100%
modules\psm\domain\indent_rules.py         50      0     22      0   100%
modules\psm\domain\receipt_rules.py        24      0     18      0   100%
modules\psm\domain\state_machine.py        90      0      4      0   100%
modules\psm\domain\stock_rules.py          32      0     10      0   100%
modules\psm\domain\vendor_rules.py         39      0     18      0   100%
-----------------------------------------------------------------------------------
TOTAL                                     358      0    104      0   100%
Required test coverage of 95% reached. Total coverage: 100.00%
92 passed in 317.52s (0:05:17)
```

---

## 3. Per-File Test Counts, Journey Mappings & Query-Count Budgets

### Backend Test Counts (`modules/psm/tests/` — 12 Files, 92 Tests)

| Test File | Executed Test Cases | Primary Focus |
| --- | --- | --- |
| `modules/psm/tests/test_adversarial.py` | `5` | Missing policy `409`, self-approval block, unverified vendor block, discrepancy stock lock & replacement limit, CSV formula escaping |
| `modules/psm/tests/test_client_route_guards.py` | `2` | Every non-indent route wrapped in `office(...)` (`RequirePermission`), matching `NAV_ITEMS` |
| `modules/psm/tests/test_concurrency.py` | `2` | Postgres `threading.Barrier` proofs for concurrent stock reservation & concurrent full payment |
| `modules/psm/tests/test_coverage_and_traceability.py` | `7` | Contracts, discrepancy return/replacement/inventory/accounting resolutions, transfers, `?queue=1`, bounds, `AFR`/`BR`/`CFR` edge paths |
| `modules/psm/tests/test_domain.py` | `9` | Pure-Python domain rules (0 DB queries): indent, stock, approval, vendor, receipt, 3-way match, payment |
| `modules/psm/tests/test_journeys.py` | `5` | End-to-end HTTP actor journeys across all 32 live use cases and 11 live workflows |
| `modules/psm/tests/test_plain_user.py` | `2` | Plain `faculty` and `staff` end-to-end flows with no extra office roles |
| `modules/psm/tests/test_privilege_escalation.py` | `22` | 401 unauth, dual 403 gates (`HasModuleGrant` & `HasPermission`), CSRF 403, role switch, permission drift |
| `modules/psm/tests/test_query_budgets.py` | `17` | Constant SQL query count at N=2 vs. N=12 across all 16 list/singleton GET endpoints + `/dashboard` |
| `modules/psm/tests/test_schedule.py` | `5` | Celery beat tasks, SLA reminder/escalation idempotency, due report schedules, notification delivery |
| `modules/psm/tests/test_scoping_isolation.py` | `3` | Foreign row 404 isolation across employees, departments, reports, and transfers |
| `modules/psm/tests/test_state_machine.py` | `13` | Exhaustive declarative transition & terminal-state verification across all 6 entity tables |
| **Total (`modules/psm`)** | **`92`** | **`92 passed`** |

### Frontend Vitest Counts (`client/src/` — 19 Files, 87 Tests; 13 PSM Files, 49 PSM Tests)

| Test File | Tests | Suite |
| --- | --- | --- |
| `src/modules/psm/api/hooks.test.tsx` | `2` | PSM hooks |
| `src/modules/psm/pages/DashboardPage.test.tsx` | `3` | PSM page |
| `src/modules/psm/pages/IndentsPage.test.tsx` | `4` | PSM page (loading, empty/hidden control, error, modal submit) |
| `src/modules/psm/pages/StockPage.test.tsx` | `4` | PSM page (loading, empty/hidden control, error, modal submit) |
| `src/modules/psm/pages/TransfersPage.test.tsx` | `4` | PSM page (loading, empty/hidden control, error, modal submit) |
| `src/modules/psm/pages/VendorsPage.test.tsx` | `4` | PSM page (loading, empty/hidden control, error, modal submit) |
| `src/modules/psm/pages/TendersPage.test.tsx` | `4` | PSM page (loading, empty/hidden control, error, modal submit) |
| `src/modules/psm/pages/PurchaseOrdersPage.test.tsx` | `4` | PSM page (loading, empty/hidden control, error, modal submit) |
| `src/modules/psm/pages/ReceiptsPage.test.tsx` | `4` | PSM page (loading, empty/hidden control, error, modal submit) |
| `src/modules/psm/pages/InvoicesPage.test.tsx` | `4` | PSM page (loading, empty/hidden control, error, modal submit) |
| `src/modules/psm/pages/ReportsPage.test.tsx` | `4` | PSM page (loading, empty/hidden control, error, report submit) |
| `src/modules/psm/pages/AuditPage.test.tsx` | `4` | PSM page (loading, empty, error, audit filter & CSV export) |
| `src/modules/psm/pages/PolicyPage.test.tsx` | `4` | PSM page (loading, empty/hidden control, error, modal publish) |
| `src/app/LoginPage.test.ts` + `src/lib/download.test.ts` + `src/auth/*` + `src/modules/placement/*` (6 shared/placement files) | `38` | Platform auth, download helper, placement regression |
| **Total (`vitest run`)** | **`87`** | **`Test Files 19 passed (19) · Tests 87 passed (87)`** |

### Playwright E2E Counts (`client/e2e/` — 6 Files, 38 Tests; 2 PSM Files, 29 PSM Tests)

| E2E Spec File | Tests | Scope |
| --- | --- | --- |
| `client/e2e/psm/office-pages.spec.ts` | `20` | 10 ungranted-module `student` `Not found` tests + 9 `faculty` office-route `Not available to your role` tests + 1 `Director` `/psm/receipts` `Not available to your role` test |
| `client/e2e/psm/procurement-flow.spec.ts` | `9` | 9-stage serial end-to-end browser journeys across all 31 actor-triggered use cases + event-triggered `PSM-UC-035` notifications |
| `client/e2e/auth.spec.ts`, `shell.spec.ts`, `placement/companies.spec.ts`, `placement/office-pages.spec.ts` | `9` | Auth/keyboard sign-in, shell navigation, placement regression |
| **Total (`npx playwright test --workers=1`)** | **`38`** | **`38 passed`** |

### Journey Tests Mapped to Spec IDs (`test_journeys.py` & `procurement-flow.spec.ts`)

| Test Function / E2E Block | Use Cases Covered | Workflows Covered |
| --- | --- | --- |
| `test_journeys.py::test_journey_bw_psm_01_internal_stock_fulfilment` | `PSM-UC-001`, `002`, `007`, `009`, `011`, `028` | `BW-PSM-01`, `CW-PSM-01` |
| `test_journeys.py::test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial` | `PSM-UC-013`, `016`, `017`, `019`, `025`, `026`, `027`, `028`, `029` | `BW-PSM-02`, `BW-PSM-04`, `CW-PSM-01`, `CW-PSM-02` |
| `test_journeys.py::test_journey_bw_psm_03_05_high_value_final_approval_and_tender` | `PSM-UC-012`, `022` | `BW-PSM-03`, `BW-PSM-05` |
| `test_journeys.py::test_journey_bw_psm_06_07_08_10_discrepancy_modify_transfer_and_audit` | `PSM-UC-008`, `010`, `014`, `015`, `020`, `021`, `023`, `030`, `031`, `032`, `033`, `034`, `035` | `BW-PSM-06`, `BW-PSM-07`, `BW-PSM-08`, `BW-PSM-10` |
| `test_journeys.py::test_journey_remaining_live_ucs_and_alternate_flows` | `PSM-UC-001`, `003`, `005`, `019`, `020`, `023`, `024`, `026`, `027`, `028`, `029`, `032`, `033`, `034`, `035` | `BW-PSM-02`, `BW-PSM-04`, `BW-PSM-08`, `BW-PSM-10` |
| `procurement-flow.spec.ts` Block 1 (`ps_admin` setup) | `PSM-UC-008`, `019`, `030` | `BW-PSM-01` |
| `procurement-flow.spec.ts` Block 2 (`faculty` requester) | `PSM-UC-001`, `003`, `005`, `023`, `024` | `BW-PSM-01`, `BW-PSM-07` |
| `procurement-flow.spec.ts` Block 3 (`deptadmin_cse`) | `PSM-UC-007`, `008`, `009`, `011`, `017`, `021`, `033`, `034` | `BW-PSM-01`, `BW-PSM-08` |
| `procurement-flow.spec.ts` Block 4 (`HOD (CSE)`) | `PSM-UC-010`, `016` | `BW-PSM-02`, `BW-PSM-03` |
| `procurement-flow.spec.ts` Block 5 (`ps_admin` & `Director`) | `PSM-UC-012`, `025` | `BW-PSM-03` |
| `procurement-flow.spec.ts` Block 6 (`ps_admin` procurement & policy) | `PSM-UC-022`, `026`, `027`, `031` | `BW-PSM-05`, `BW-PSM-02` |
| `procurement-flow.spec.ts` Block 7 (GRN, discrepancy & notifications) | `PSM-UC-002`, `020`, `028`, `032`, `035` | `BW-PSM-04`, `BW-PSM-06`, `BW-PSM-10` |
| `procurement-flow.spec.ts` Block 8 (`Accounts Admin`) | `PSM-UC-013`, `015`, `029` | `CW-PSM-02` |
| `procurement-flow.spec.ts` Block 9 (`Auditor`) | `PSM-UC-014` | `CW-PSM-01` |

### Query-Count Budgets (`test_query_budgets.py` — 17 Endpoints, N=2 vs. N=12 Rows)

Measured with `CaptureQueriesContext(connection)` inside a rolled-back transaction after seeding `N=2` and `N=12` complete procurement/stock/finance workflows (`_seed_rows`):

| Endpoint | Queries at N=2 Rows | Queries at N=12 Rows | Delta | Status |
| --- | --- | --- | --- | --- |
| `/api/v1/psm/dashboard` | `6` | `6` | `0` | Pass (Constant) |
| `/api/v1/psm/indents` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/stock/items` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/stock/locations` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/stock/availability` | `4` | `4` | `0` | Pass (Constant) |
| `/api/v1/psm/internal-issues` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/transfers` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/vendors` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/tenders` | `2` | `2` | `0` | Pass (Constant) |
| `/api/v1/psm/purchase-orders` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/grns` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/discrepancies` | `2` | `2` | `0` | Pass (Constant) |
| `/api/v1/psm/invoices` | `2` | `2` | `0` | Pass (Constant) |
| `/api/v1/psm/reports/schedules` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/audit` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/notifications` | `1` | `1` | `0` | Pass (Constant) |
| `/api/v1/psm/policy` | `1` | `1` | `0` | Pass (Constant) |

---

## 4. Mutation Proof (Step 5.15 — Five Critical Domain Rules Broken on Purpose)

Each domain invariant was intentionally disabled one at a time in `modules/psm/domain/`, tested against `modules/psm/tests/`, and restored cleanly:

1. **Self-approval ban (`BR-PSM-005`)** in `modules/psm/domain/approval_policy.py` (`if requestor_user_id == actor_user_id:` disabled): `exit=1`, caught by `modules/psm/tests/test_domain.py::test_approval_policy_method_final_priority_and_sla` and `modules/psm/tests/test_adversarial.py::test_approver_cannot_approve_own_indent`.
2. **Unverified vendor gate (`BR-PSM-012`)** in `modules/psm/domain/vendor_rules.py` (`if not is_verified:` disabled): `exit=1`, caught by `modules/psm/tests/test_domain.py::test_vendor_master_validation_and_gate`.
3. **Stock adjustment zero-delta guard (`BR-PSM-026`)** in `modules/psm/domain/stock_rules.py` (`if delta == 0:` disabled): `exit=1`, caught by `modules/psm/tests/test_domain.py::test_stock_adjustment_blocks_zero_and_below_reserved`.
4. **Open discrepancy payment hold (`BR-PSM-017`, `BR-PSM-022`)** in `modules/psm/domain/finance_rules.py` (`if data.has_open_discrepancy:` disabled): `exit=1`, caught by `modules/psm/tests/test_domain.py::test_three_way_match_and_payment_release_rules`.
5. **State machine invalid transition guard (`BW-PSM-01..10`)** in `modules/psm/domain/state_machine.py` (`if transition is None:` disabled): `exit=1`, caught by all parametrized cases in `modules/psm/tests/test_state_machine.py::test_every_illegal_transition_is_refused`.

---

## 5. Adversarial Pass & Postgres Concurrency Proofs (Steps 5.7 & 5.11)

### Adversarial Pass (Step 5.11)

| Adversarial Question Tested | What Was Checked / Found | Code Fix & Regression Test |
| --- | --- | --- |
| Can an actor approve or verify their own indent (`BR-PSM-005`)? | Checked every approval tier (`dept_admin`, `HOD`, `ps_admin`, `Director`/`Registrar`). | `ap.ensure_not_self_approval` enforced in all approval services; proven by `test_adversarial.py::test_approver_cannot_approve_own_indent`. |
| Can an unconfirmed GRN be bypassed via discrepancy accounting adjustment (`BR-PSM-009`, `BR-PSM-017`)? | Found in R2 that `_apply_accounting_adjustment` could mark an invoice `verified` without confirmed delivery (`R2-01`). | Refactored `discrepancies.py::_reconcile_invoice` to transition only via `sm.resolve` and re-evaluate `fr.three_way_match` against confirmed GRN accepted quantities. |
| Can `replacement_for_case_id` be attached to an unrelated PO's GRN (`BR-PSM-019`)? | Found in R2 that `_load_replacement_case` did not validate same source PO/issue (`R2-03`). | Enforced `replacement_source_mismatch` `ConflictError` in `services/receipts.py::_load_replacement_case` + negative regression test. |
| Do oversized integers (`> 2147483647`) cause DB 500 `DataError` (`R2-04`)? | Found PostgreSQL integer overflow 500 when huge numbers bypassed serializer validation. | Added `_MAX_ID` / `_MAX_QTY` / `_MAX_HOURS` / `_MAX_WINDOW_DAYS` bounds in `api/serializers.py` returning HTTP `400 validation_error` + tests. |
| Can a destination-department admin dispatch stock from another department (`PSM-UC-033`)? | Found in R1 that `deptadmin` on destination could call `/dispatch` (`R1-03`). | Restricted `transfers.dispatch_transfer` to source-department admin or `ps_admin` (when `source_location.is_central=True`). |
| Can CSV report exports execute spreadsheet formulas (`AFR-PSM-079`)? | Verified descriptions starting with `=`, `+`, `-`, `@`, `\t`, `\r` in CSV export. | `reports.py` prefixes leading formula characters with `'` (`test_adversarial.py::test_csv_export_escapes_formula_injection`). |
| What happens if PSM is called before `seed_psm_policy` (`BR-PSM-028`)? | Verified fresh DB writes without active `PsmPolicy`. | `require_active_policy` raises `ConflictError("policy_missing")` (HTTP 409, never 500); proven by `test_missing_policy_refuses_cleanly_with_409_not_500`. |

### Real-Thread Postgres Concurrency Proofs (Step 5.7)

Both races run against real PostgreSQL with `transaction=True` and `threading.Barrier(2)`:

- **`test_concurrent_stock_reservations_never_overcommit`:** Two threads simultaneously attempt to reserve `4` units each out of `5` available units for two separate indents (`select_for_update(of=("self",))` on `StockItem` / `StockBalance`). Exactly one thread receives `"stock_reserved"` and only `1` active `StockReservation` is persisted; the loser cleanly routes to `"external_required"`.
- **`test_concurrent_full_payments_only_release_once`:** Two threads simultaneously attempt to pay the full `2000.00` balance on a `verified` invoice (`select_for_update(of=("self",))` on `Invoice`). Exactly one `PaymentTransaction` is created (`count == 1`), and the second thread fails deterministically with `ConflictError`.

---

## 6. Security Self-Audit (Step 7.7 — All 10 Items)

1. **Dual 403 Gates (`HasModuleGrant("psm")` + `HasPermission(...)`), no `AllowAny`, no route outside module router:** Verified. All views under `modules/psm/api/urls.py` require both gates (automated scan: `AllowAny/raw/extra/eval/pickle/yaml: []`), tested across all route/method pairs in `test_privilege_escalation.py` (22 cases).
2. **Explicit serializer fields & server-owned read-only attributes:** Verified. Zero `ModelSerializer` `__all__` or `exclude` usages (`ModelSerializer __all__/exclude: []`); all 432 lines in `modules/psm/api/serializers.py` declare explicit fields with `read_only=True` on server-owned IDs, statuses, versions, timestamps, and ledger totals.
3. **All reads & FK inputs scoped via `selectors/scoping.py` (404 on foreign rows):** Verified. Every list, detail, and mutation lookup filters through `scoping.*_for(actor)`, returning `404` on foreign records (`test_scoping_isolation.py`).
4. **Zero unsafe dynamic execution or SQL:** Verified. Zero occurrences of `.raw(`, `.extra(`, `eval(`, `pickle.`, `yaml.load`, or `subprocess` across `modules/psm/`.
5. **Attachment / document safety:** Verified. Discrepancy evidence uses validated HTTPS Google Drive URLs (`_validate_evidence_url`, `sanitize_drive_filename`), rejecting untrusted hosts/schemes without writing uploaded binaries to server web roots.
6. **Every write endpoint carries a `throttle_scope`:** Verified. `throttle_scope` appears `42` times across `modules/psm/api/views_*.py`, covering every write view and export endpoint (`test_coverage_and_traceability.py` verifies `429` throttling on `psm_export`).
7. **PII-safe audit & application logging:** Verified. Structured logs (`fusion.psm psm.audit action=... target=... actor=<user_id>`) record numeric IDs and action codes only — zero names, roll numbers, tokens, or raw request payloads.
8. **Opaque error responses:** Verified. Errors flow through `core/api/exceptions.py` JSON handler (`code`, `message`, `details`, `request_id`), exposing zero stack traces, SQL queries, or filesystem paths.
9. **Strict auth & CSRF enforcement on cookie writes:** Verified. Zero views weaken `authentication_classes` or `permission_classes`; `test_privilege_escalation.py::test_cookie_write_without_csrf_header_answers_403` proves cookie POSTs without `X-CSRF-Token` answer `403` and succeed once the header is supplied.
10. **Client security hygiene, dependency policy & deploy check:** Verified. Automated scan of `client/src/modules/psm/` confirms zero `dangerouslySetInnerHTML`, zero `localStorage` tokens, and zero raw `fetch()` calls (all traffic goes through `client/src/lib/http.ts`). Zero unapproved Python or npm dependencies were added. Production deploy check command & real output:

```powershell
DJANGO_SETTINGS_MODULE=config.settings.prod DB_PASSWORD=local-check-only `
DJANGO_SECRET_KEY=local-check-only-key-long-enough-to-satisfy-the-length-check `
DJANGO_ALLOWED_HOSTS=local.invalid IAM_SERVICE_TOKEN=local `
PLACEMENT_UPLOAD_ROOT=C:\temp\check-uploads `
REDIS_CACHE_URL=redis://127.0.0.1:6379/1 REDIS_BROKER_URL=redis://127.0.0.1:6380/0 `
.\.venv\Scripts\python.exe manage.py check --deploy --fail-level WARNING
```

Observed output (`exit=0`):

```text
System check identified no issues (2 silenced).
```

---

## 7. Fresh-Install Proof (Step 7.8 — Throwaway `fusion_integrated_fresh` DB)

Executed in one shell pass with `DB_NAME=fusion_integrated_fresh`:

1. Created empty database `fusion_integrated_fresh`, ran `manage.py migrate`, reversed `manage.py migrate psm zero`, and re-ran `manage.py migrate`:

```text
Created fusion_integrated_fresh
...
  Applying placement.0010_retire_resume_documents... OK
  Applying psm.0001_initial... OK
Operations to perform:
  Unapply all migrations: psm
Running migrations:
  Rendering model states... DONE
  Unapplying psm.0001_initial... OK
Operations to perform:
  Apply all migrations: accesscontrol, auth, contenttypes, directory, placement, psm
Running migrations:
  Applying psm.0001_initial... OK
```

2. Verified `seed_modules` and `psm_readiness` **before** `seed_psm_policy`:

```text
  registered placement_cell (active)
  psm: registered but NOT active — 1 prerequisite(s) unmet:
      No active PSM policy is configured; run 'manage.py seed_psm_policy'.
  registered psm (active)
2 module(s) registered
NOT READY: No active PSM policy is configured; run 'manage.py seed_psm_policy'.
CommandError: 1 unmet PSM prerequisite(s).
psm_readiness_exit_before=1
```

3. Seeded initial policy (`manage.py seed_psm_policy`) and re-ran `seed_modules` + `psm_readiness` **after** policy seed:

```text
2026-11-23 03:27:15 INFO fusion.psm psm.audit action=policy.published target=policy:1 actor=None
Created: PSM policy v1 (direct <= 50000.00, final > 100000.00)
  registered placement_cell (active)
  registered psm (active)
2 module(s) registered
PSM module is ready.
psm_readiness_exit_after=0
```

4. Verified live HTTP endpoints on the fresh DB, then dropped `fusion_integrated_fresh`:

```text
/healthz -> 200 {"status": "ok"}
/readyz -> 200 {"status": "ok", "checks": {"database": "ok", "cache": "ok", "broker": "ok"}}
unauth /api/v1/psm/indents -> 401 {"error":{"code":"not_authenticated","message":"Authentication credentials were not provided.","details":[],"request_id":"4b7ef0eb-1b58-48ea-936d-d33c4de55c77"}}
Dropped fusion_integrated_fresh
```

---

## 8. Browser Walkthrough Table (Step 6.7 & Step 6.9 — All Step 3.4 Roles + Keyboard Flow)

Executed live against `Fusion_System_Administrator` (`127.0.0.1:8001`), Django `runserver` (`127.0.0.1:8002`), and Vite (`http://localhost:5173`) with `seed_iam_permissions` and `seed_psm_policy` applied, verifying `0` browser console errors and `0` HTTP 500 responses across every Step 3.4 role and the keyboard-only accessibility flow:

| # | Role (`Step 3.4`) | Account | Pages Visited & Actions Taken | Playwright / Walkthrough Automation | Observed `runserver` Log Lines | Result |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Plain user (`ug_student`, no `psm` grant) | `stu00001` | Signed in, attempted `/psm/stock`..`/psm/policy`; sidebar omits PSM, direct navigation renders `Not found` with 0 buttons | `office-pages.spec.ts` (`student`) | `[23/Nov/2026 02:53:04] "POST /api/v1/auth/login HTTP/1.1" 200 91` · `[23/Nov/2026 02:53:04] "GET /api/v1/me HTTP/1.1" 200 1144` | Passed |
| 2 | `faculty` (Requester) | `fac00001` | Created/modified/repeated/withdrew indent on `/psm/indents`, recorded GRN & discrepancy on `/psm/receipts`, confirmed receipt & checked dashboard notifications; `/psm/stock` refused | `procurement-flow.spec.ts` Blocks 2 & 7; `office-pages.spec.ts` | `[23/Nov/2026 02:51:04] "POST /api/v1/psm/indents HTTP/1.1" 201 528` · `[23/Nov/2026 02:51:05] "PATCH /api/v1/psm/indents/13 HTTP/1.1" 200 528` · `[23/Nov/2026 02:51:07] "POST /api/v1/psm/indents/13/repeat HTTP/1.1" 201 477` · `[23/Nov/2026 02:51:09] "POST /api/v1/psm/indents/13/withdraw HTTP/1.1" 200 528` · `[23/Nov/2026 02:54:50] "POST /api/v1/psm/grns HTTP/1.1" 201 373` · `[23/Nov/2026 02:54:51] "POST /api/v1/psm/discrepancies HTTP/1.1" 201 430` · `[23/Nov/2026 02:54:58] "POST /api/v1/psm/grns/2/confirm HTTP/1.1" 200 404` | Passed |
| 3 | Keyboard-only flow (`faculty`) | `fac00001` | Tabbed to `New indent`, opened modal with `Enter`, filled fields via `Tab` + typing, submitted (`201 Created`) with `Enter`, opened modal & dismissed via `Escape` | Live Chromium keyboard walkthrough | `2026-11-23 03:31:38 INFO fusion.psm psm.audit action=indent.submitted target=indent:97 actor=5328` · `[23/Nov/2026 03:31:38] "POST /api/v1/psm/indents HTTP/1.1" 201 516` | Passed |
| 4 | `staff` | `stf00006` | Submitted indent on `/psm/indents`; navigated to `/psm/receipts` and observed `Not available to your role` (`_STAFF_EMPLOYEE`) | Live Chromium walkthrough | `2026-11-23 03:29:51 INFO fusion.psm psm.audit action=indent.submitted target=indent:95 actor=2453` · `[23/Nov/2026 03:29:52] "POST /api/v1/psm/indents HTTP/1.1" 201 505` · `[23/Nov/2026 03:29:52] "GET /api/v1/psm/indents HTTP/1.1" 200 547` | Passed |
| 5 | `dept_admin` | `stf00009` | Switched to `dept_admin`, submitted indent on `/psm/indents`, opened `/psm/stock` & `/psm/transfers` scoped to own `UserRef.department` | Live Chromium walkthrough | `[23/Nov/2026 03:30:46] "GET /api/v1/psm/indents HTTP/1.1" 200 42` · `[23/Nov/2026 03:30:47] "POST /api/v1/psm/indents HTTP/1.1" 201 504` · `[23/Nov/2026 03:30:48] "GET /api/v1/psm/stock/availability HTTP/1.1" 200 3427` · `[23/Nov/2026 03:30:48] "GET /api/v1/psm/transfers HTTP/1.1" 200 42` | Passed |
| 6 | `deptadmin_cse` | `stf00003` | Adjusted CSE stock, checked/reserved stock, reviewed/approved CSE indents, dispatched internal issue, requested/dispatched/confirmed CSE stock transfer | `procurement-flow.spec.ts` Block 3 | `[23/Nov/2026 02:54:14] "POST /api/v1/psm/stock/adjustments HTTP/1.1" 201 193` · `[23/Nov/2026 02:54:16] "POST /api/v1/psm/indents/20/stock-check HTTP/1.1" 200 562` · `[23/Nov/2026 02:54:16] "POST /api/v1/psm/indents/20/review HTTP/1.1" 200 545` · `[23/Nov/2026 02:54:20] "POST /api/v1/psm/internal-issues/3/dispatch HTTP/1.1" 200 352` · `[23/Nov/2026 02:54:22] "POST /api/v1/psm/transfers HTTP/1.1" 201 405` · `[23/Nov/2026 02:54:23] "POST /api/v1/psm/transfers/3/dispatch HTTP/1.1" 200 436` · `[23/Nov/2026 02:54:23] "POST /api/v1/psm/transfers/3/confirm HTTP/1.1" 200 465` | Passed |
| 7 | `HOD (CSE)` | `fac00002` | Recommended CSE external indents (`POST /recommend`) and generated operational report (`POST /reports/generate`) | `procurement-flow.spec.ts` Block 4 | `[23/Nov/2026 02:54:26] "POST /api/v1/psm/indents/21/recommend HTTP/1.1" 200 536` · `[23/Nov/2026 02:54:27] "POST /api/v1/psm/indents/22/recommend HTTP/1.1" 200 535` · `[23/Nov/2026 02:54:28] "POST /api/v1/psm/reports/generate HTTP/1.1" 200 5168` | Passed |
| 8 | `ps_admin` | `stf00001` | Onboarded & verified vendor, created stock item/locations/adjustment, ran procurement-review, published tender, issued/updated PO, resolved discrepancy, created report schedule, published policy | `procurement-flow.spec.ts` Blocks 1, 5, 6, 7 | `[23/Nov/2026 02:53:49] "POST /api/v1/psm/vendors HTTP/1.1" 201 305` · `[23/Nov/2026 02:53:50] "POST /api/v1/psm/vendors/11/verify HTTP/1.1" 200 334` · `[23/Nov/2026 02:54:31] "POST /api/v1/psm/indents/21/procurement-review HTTP/1.1" 200 549` · `[23/Nov/2026 02:54:39] "POST /api/v1/psm/tenders/2/publish HTTP/1.1" 200 362` · `[23/Nov/2026 02:54:41] "POST /api/v1/psm/purchase-orders HTTP/1.1" 201 391` · `[23/Nov/2026 02:54:46] "POST /api/v1/psm/policy HTTP/1.1" 201 546` · `[23/Nov/2026 02:54:55] "POST /api/v1/psm/discrepancies/2/resolve HTTP/1.1" 200 462` | Passed |
| 9 | `SectionHead_PS` | `stf00007` | Onboarded vendor on `/psm/vendors` and viewed active/historical policy on `/psm/policy` | Live Chromium walkthrough | `2026-11-23 03:30:51 INFO fusion.psm psm.audit action=vendor.onboarded target=vendor:36 actor=5430` · `[23/Nov/2026 03:30:51] "POST /api/v1/psm/vendors HTTP/1.1" 201 298` · `[23/Nov/2026 03:30:52] "GET /api/v1/psm/policy HTTP/1.1" 200 1656` | Passed |
| 10 | `Director` | `stf00002` | Approved high-value indent (`POST /final-decision`); direct navigation to `/psm/receipts` rendered `Not available to your role` + 0 buttons | `procurement-flow.spec.ts` Block 5; `office-pages.spec.ts` | `2026-11-23 02:54:35 INFO fusion.psm psm.audit action=indent.final_approved target=indent:22 actor=5410` · `[23/Nov/2026 02:54:35] "POST /api/v1/psm/indents/22/final-decision HTTP/1.1" 200 548` · `[23/Nov/2026 02:54:35] "GET /api/v1/psm/indents HTTP/1.1" 200 11578` | Passed |
| 11 | `Registrar` | `stf00008` | Viewed `/psm/indents` & `/psm/policy`, generated report on `/psm/reports`; direct navigation to `/psm/receipts` rendered `Not available to your role` | Live Chromium walkthrough | `[23/Nov/2026 03:30:54] "GET /api/v1/psm/indents HTTP/1.1" 200 12389` · `2026-11-23 03:30:55 INFO fusion.psm psm.audit action=report.generated target=report_log:9 actor=2431` · `[23/Nov/2026 03:30:55] "POST /api/v1/psm/reports/generate HTTP/1.1" 200 13141` · `[23/Nov/2026 03:30:55] "GET /api/v1/psm/policy HTTP/1.1" 200 1656` | Passed |
| 12 | `Accounts Admin` | `stf00004` | Recorded vendor invoice, ran 3-way match verification, released vendor payment, and generated financial report | `procurement-flow.spec.ts` Block 8 | `[23/Nov/2026 02:55:02] "POST /api/v1/psm/invoices HTTP/1.1" 201 311` · `[23/Nov/2026 02:55:03] "POST /api/v1/psm/invoices/1/verify HTTP/1.1" 200 344` · `[23/Nov/2026 02:55:04] "POST /api/v1/psm/invoices/1/pay HTTP/1.1" 201 196` · `[23/Nov/2026 02:55:05] "POST /api/v1/psm/reports/generate HTTP/1.1" 200 387` | Passed |
| 13 | `Auditor` | `stf00005` | Inspected & filtered immutable audit logs (`target_type=invoice`), viewed dashboard read-only | `procurement-flow.spec.ts` Block 9 | `[23/Nov/2026 02:55:08] "GET /api/v1/psm/audit HTTP/1.1" 200 6460` · `[23/Nov/2026 02:55:08] "GET /api/v1/psm/audit?target_type=invoice HTTP/1.1" 200 771` | Passed |

---

## 9. Scheduled Tasks Run by Hand (Step 7.9 Item 9)

All three PSM management commands were invoked manually against due records (`Indent 11` aged `30h`, `Indent 12` aged `80h`, due active `ReportSchedule 14`, and queued `PsmNotification` rows):

```powershell
.\.venv\Scripts\python.exe manage.py run_psm_sla_sweep
.\.venv\Scripts\python.exe manage.py run_psm_scheduled_reports
.\.venv\Scripts\python.exe manage.py deliver_psm_notifications
```

Observed stdout and persisted database row changes:

- **`run_psm_sla_sweep` (`tasks.check_approval_slas` / `services.approvals.sweep_slas`):**
  - Stdout: `SLA sweep complete: 1 reminded, 1 escalated.`
  - Database changes: `Indent` id=`11` updated `sla_reminded_at = 2026-11-22 21:51:29.655603+00:00` (+ reminder `PsmNotification` queued); `Indent` id=`12` updated `sla_escalated_at = 2026-11-22 21:51:29.655603+00:00` (+ escalation `PsmNotification` queued).
- **`run_psm_scheduled_reports` (`tasks.run_scheduled_reports` / `services.reports.run_due_schedules`):**
  - Stdout: `Scheduled reports executed: 1.`
  - Database changes: `ReportSchedule` id=`14` updated `last_run_at = 2026-11-22 21:51:32.507287+00:00` and `next_run_at = 2026-11-29 21:51:32.507287+00:00`; created `ReportGenerationLog` id=`8` (`report_type = operational`, `row_count = 58`).
- **`deliver_psm_notifications` (`tasks.deliver_notifications` / `services.common.deliver_pending_notifications`):**
  - Stdout: `Delivered 200 PSM notification(s).`
  - Database changes: Marked `200` queued rows as `status = "sent"` with `sent_at` populated (`213` total sent, `25` remaining beyond batch limit `200` for subsequent 60-second Beat ticks).

---

## 10. Known Gaps & Accepted Deferrals (Step 7.9 Item 10)

1. **`Fusion-client` portal framing (`module-only` environment, Step 6.6):** Because `Fusion-client` is absent from this checkout, portal framing is deferred to `full-platform` integration and the exact `INTEGRATED_MODULES` sidebar snippet is handed over in `docs/09-psm/psm-blueprint.md`.
2. **External email / SMS gateway delivery (`BR-PSM-006`, `AFR-PSM-086`):** Dev environments do not configure SMTP/SMS relays; `deliver_notifications` marks `PsmNotification` rows `sent` and retains complete communication history.
3. **External institute general-ledger integration (`AFR-PSM-055`, `PSM-UC-029`):** Because no institute GL module exists in `Fusion-Integrated`, accounting adjustments adjust linked `Invoice.eligible_amount` / hold status and record immutable `PsmAuditLog` + `PaymentRecord` entries inside `psm`.
4. **Upstream `06_PSM_Traceability_Matrix_v1.1_FINAL.xlsx` read-only status (Approved R3 §5.1):** Kept untouched as read-only spec input; `docs/09-psm/psm-blueprint.md` and `docs/09-psm/psm-reference.md` provide full forward/reverse traceability across all 180 live IDs.
5. **Event-triggered `PSM-UC-035` browser verification (Approved R3 §5.2):** Verified by running lifecycle notification creation and asserting rendered notifications on `/psm/dashboard` in `procurement-flow.spec.ts` alongside `test_schedule.py` + `deliver_psm_notifications`.

---

## 11. Independent Review Scorecards & Fix History (Step 7.9 Item 12)

### Round 1 Scorecard — Commit `06dd8a3194b4c8bad83cb09d6e6aa93ba7a21f1c`

| # | Dimension | Score | Blockers | Majors | Minors |
| --- | --- | --- | --- | --- | --- |
| 1 | Spec fidelity | `6/10` | `0` | `3` | `0` |
| 2 | Architecture | `9/10` | `0` | `0` | `0` |
| 3 | Code quality | `9/10` | `0` | `0` | `1` |
| 4 | Security | `5/10` | `1` | `0` | `0` |
| 5 | Backend tests | `7/10` | `0` | `1` | `0` |
| 6 | End-to-end behaviour | `3/10` | `1` | `2` | `0` |
| 7 | Frontend | `4/10` | `1` | `1` | `0` |
| 8 | Operability and docs | `6/10` | `0` | `1` | `0` |
| 9 | Hygiene | `10/10` | `0` | `0` | `0` |
| **Total** | | | **`3`** | **`8`** | **`1`** |

- **Round 1 Fixes Summary (`R1-01`..`R1-12`):** Fixed `PurchaseOrdersPage.test.tsx` modal selector (`R1-01`); split `office-pages.spec.ts` ungranted-module vs. non-office refusals (`R1-02`); restricted `transfers.dispatch_transfer` to source-department admin or central `ps_admin` (`R1-03`); implemented atomic `StockLedgerEntry` + `Invoice` adjustment on `resolve_case` (`R1-04`); added live Browser Walkthrough Table (`R1-05`); expanded `test_journeys.py` (`R1-06`); added declarative `PO_TRANSITIONS` state machine (`R1-07`); synced blueprint/domain/state-machine/reference docs and confirmed `evidence_url` supersedes `/evidence` endpoint (`R1-08`); added missing spec assertions (`R1-09`); expanded `test_privilege_escalation.py` and `test_query_budgets.py` (`R1-10`); added error surfacing & Withdraw ownership gate (`R1-11`); factored >50-line backend functions (`R1-12`).

### Round 2 Scorecard — Commit `4f062a12eb43904fc332c2598f5d7b998b6f672a`

| # | Dimension | Score | Blockers | Majors | Minors |
| --- | --- | --- | --- | --- | --- |
| 1 | Spec fidelity | `5/10` | `1` | `2` | `0` |
| 2 | Architecture and contracts | `10/10` | `0` | `0` | `0` |
| 3 | Permissions and scoping | `10/10` | `0` | `0` | `0` |
| 4 | Input bounds, concurrency and safety | `8/10` | `0` | `1` | `0` |
| 5 | Backend tests | `7/10` | `0` | `1` | `0` |
| 6 | End-to-end behaviour | `6/10` | `0` | `1` | `0` |
| 7 | Frontend | `8/10` | `0` | `1` | `0` |
| 8 | Operability and docs | `9/10` | `0` | `0` | `1` |
| 9 | Hygiene | `10/10` | `0` | `0` | `0` |
| **Total** | | | **`1`** | **`6`** | **`1`** |

- **Round 2 Fixes Summary (`R2-01`..`R2-08`):** Routed `_reconcile_invoice` through `sm.resolve` + confirmed-GRN three-way match (`R2-01`); fixed `?queue=1` priority ordering (`urgent`, `high`, default `normal`) (`R2-02`); enforced replacement PO/issue source matching (`R2-03`); added `max_value`/`min_value` serializer bounds returning 400 (`R2-04`); wrapped `/psm/receipts` in `RequirePermission("psm.grn.view")` (`R2-05`); separated E2E synthetic accounts (`stf00001`..`005`) (`R2-06`); expanded `test_query_budgets.py::_seed_rows` and missing assertions (`R2-07`); refactored `publish_policy` cleanly and removed doc typos (`R2-08`).

### Round 3 Scorecard — Commit `be1d122af388ad2a9a8ba6db5ce636e68753b365`

| # | Dimension | Score | Blockers | Majors | Minors |
| --- | --- | --- | --- | --- | --- |
| 1 | Spec fidelity | `7/10` | `0` | `2` | `0` |
| 2 | Architecture | `10/10` | `0` | `0` | `0` |
| 3 | Code quality | `9/10` | `0` | `0` | `1` |
| 4 | Security | `10/10` | `0` | `0` | `0` |
| 5 | Backend tests | `8/10` | `0` | `1` | `0` |
| 6 | End-to-end behaviour | `7/10` | `0` | `2` | `0` |
| 7 | Frontend | `10/10` | `0` | `0` | `0` |
| 8 | Operability and docs | `7/10` | `0` | `2` | `1` |
| 9 | Hygiene | `10/10` | `0` | `0` | `0` |
| **Total** | | | **`0`** | **`7`** | **`2`** |

- **Round 3 Fixes Summary (`R3-01`..`R3-07`):**
  - **`R3-01`:** Audited all 180 spec IDs across `modules/psm/tests/`, relocated misattributed comment citations onto the exact tests asserting their effect (`test_journeys.py` & `test_coverage_and_traceability.py`), and added a direct `"return"` discrepancy resolution test for `AFR-PSM-050`.
  - **`R3-02`:** Eliminated `_default_impl_ref` `:1` bucket fallbacks in `ops/docs/psm_reference.py`, replaced with `EXACT_IMPL_SYMBOLS` + `_resolve_symbol_ref` (`include_lines=True`), and regenerated `docs/09-psm/psm-reference.md` across all 180 live spec IDs.
  - **`R3-03`:** Added `Modify`, `Repeat`, and `Stock item ID` UI controls to `IndentsPage.tsx` and upgraded `procurement-flow.spec.ts` into a 9-stage serial E2E suite exercising real UI mutations + reload persistence for all 31 actor-triggered UCs + `PSM-UC-035` notifications.
  - **`R3-04`:** Split `ROLE_GRANTS["staff"] = _STAFF_EMPLOYEE` in `modules/psm/registry.py`, regenerated `registry/permissions.json`, re-seeded IAM (`seed_iam_permissions`), and added the `psmDirector` (`stf00002`) `/psm/receipts` refusal test in `client/e2e/psm/office-pages.spec.ts`.
  - **`R3-05`:** Rebuilt `docs/09-psm/psm-quality-report.md` completely with all 12 Step 7.9 items, both branch coverage runs, per-file test counts, 17-endpoint query budgets, all 10 security self-audit items, throwaway `fusion_integrated_fresh` install proof, complete Step 3.4 + keyboard walkthrough logs, 3 manual scheduled command runs, and Rounds 1–3 scorecards.
  - **`R3-06`:** Collapsed all consecutive multi-line `#` and `//` comments into single-line comments across `modules/psm/`, `client/src/modules/psm/`, `client/e2e/psm/`, and `ops/docs/psm_reference.py`.
  - **`R3-07`:** Updated `docs/09-psm/psm-blueprint.md` route-guard table & `ROLE_GRANTS` listing to match `routes.tsx` (`office("psm.grn.view", <ReceiptsPage />)`) and `registry.py` (`_STAFF_EMPLOYEE`).
