# PHC quality report

Status: implementation remains open. This report records commands actually run in the current session and outstanding gates; it does not claim release readiness.

## Approvals

- 2026-11-23: Apurva Verma, 24BEC013, approved the PHC blueprint and decisions in the user-provided written approval in this session.
- 2026-11-23: Apurva Verma, 24BEC013, approved IAM manifest version 2 with version 1 compatibility and ReportLab for medical record PDF export in the user-provided written approval in this session.
- 2026-11-23: Apurva Verma, 24BEC013, approved “a Unicode-capable font (such as DejaVu Sans if available in the environment or standard fallback without unapproved external downloads)” and the IAM `assign_role` command.
- `reportlab>=4.4,<5` is approved; the local environment resolved ReportLab 4.5.1 and Pillow 13.0.0.
- PDF generation now registers locally installed DejaVu Sans (or FreeSans fallback) as an embedded shapable Unicode font. No font was downloaded or added as a dependency.

## Current verification evidence

| Gate | Command | Result |
|---|---|---|
| Main repository | `make check` | Passed after adding query-budget tests: system check clean, migrations check “No changes detected”, Ruff passed, 5 import contracts kept / 0 broken, all three ops checks passed, manifest/schema checks passed, pytest reached 100% and exited 0. |
| Client | `make check-client` | Passed after PDF test changes: both TypeScript checks completed, 20 test files passed and Vite build succeeded. PHC chunks are below 2.8 kB gzip. The main app bundle is 163.71 kB gzip. |
| PHC coverage | `.venv/bin/pytest --create-db modules/phc --cov=modules/phc --cov-branch --cov-report=term-missing --cov-fail-under=90 -q` | Passed: 58 tests; total coverage 93.03%, required 90%. Final line: `Required test coverage of 90% reached. Total coverage: 93.03%`. |
| Domain coverage | `.venv/bin/pytest modules/phc --cov=modules/phc/domain --cov-branch --cov-report=term-missing --cov-fail-under=95 -q` | Passed: 58 tests; domain coverage 100.00%. Final line: `Required test coverage of 95% reached. Total coverage: 100.00%`. |
| PDF + query budgets | `.venv/bin/pytest modules/phc/tests/test_records.py modules/phc/tests/test_query_budgets.py -q` | Passed: 6 tests, including Devanagari notes/prescription PDF embedding and 2-vs-20 record query count. |
| Deploy check | `DJANGO_SETTINGS_MODULE=config.settings.prod DB_PASSWORD=local-check-only DJANGO_SECRET_KEY=local-check-only-key-long-enough-to-satisfy-the-length-check DJANGO_ALLOWED_HOSTS=local.invalid IAM_SERVICE_TOKEN=local PLACEMENT_UPLOAD_ROOT=/tmp/check-uploads REDIS_CACHE_URL=redis://127.0.0.1:6379/1 REDIS_BROKER_URL=redis://127.0.0.1:6380/0 .venv/bin/python manage.py check --deploy --fail-level WARNING` | Passed: `System check identified no issues (2 silenced).` |
| IAM manifest v2 | IAM `seed_iam_permissions --manifest .../registry/permissions.json` | Passed: `53 added, 6 revoked; 87 total`. A subsequent dry run reported `0 to add, 0 to revoke`. A v1 compatibility dry run also passed. |
| IAM assignment command | `manage.py assign_role --help` in fetched upstream IAM `main` | The command and its ERP-backed tests are already present in upstream IAM `main`; the local IAM checkout was fast-forwarded to that commit. The earlier isolated tests exercised a temporary implementation and are not represented as tests of the upstream version. The broader IAM Django suite was not rerun after the fast-forward. |
| IAM manifest v1/v2 | IAM `seed_iam_permissions --manifest .../registry/permissions.json` | Passed: `53 added, 6 revoked; 87 total`; later dry run `0 to add, 0 to revoke`; version 1 compatibility dry run passed. |
| Browser E2E | `E2E_IAM_DIR=/home/apurva/Documents/Fusion/Fusion_System_Administrator npm run e2e` | Failed in global setup after the new command ran: ERP designation `placement_officer` does not exist. The actual designation is `placement officer`. Approval to correct the shared E2E account mapping is pending. |

## Adversarial and mutation checks

The following five checks were run by copying the source file to `/tmp`, introducing one deliberate defect, running the named test, restoring the copy, and confirming the test passed again:

| Rule deliberately broken | Test that caught it | Result |
|---|---|---|
| Patient visit scoping removed | `test_phc_br_02_patient_list_search_and_report_keep_patient_data_scoped` | Failed with both patient rows visible; passed after restore. |
| PDF endpoint permission gate removed | `test_phc_br_03_module_and_permission_are_independent_gates[records/pdf-phc.record.export]` | Failed when a principal with module access but no permission reached the missing-record refusal; passed after restore. The test was corrected to POST and refresh the fake principal for each gate. |
| Non-negative stock boundary changed to reject zero | `test_phc_br_07_stock_stays_nonnegative_and_alert_uses_strict_threshold` | Failed on the exact-zero stock case; passed after restore. |
| Requisition actor check removed | `test_phc_br_10_and_phc_br_11_requisition_table_rejects_unlisted_paths` | Failed because an unauthorized actor was accepted; passed after restore. |
| Inventory item unique constraint removed from the migration | `test_phc_br_07_uc_09_inventory_api_creates_items_adjusts_stock_and_lists_alerts` | Failed because duplicate creation returned 201; passed after restoring the constraint. This uncovered and fixed a transaction savepoint bug when the duplicate conflict is handled. |

## Scheduled work

On `fusion_integrated_fresh`, created one synthetic requisition outbox row and called `deliver_notifications.run()` twice. Output: `{'first_delivery_count': 1, 'second_delivery_count': 0, 'notification_count': 1, 'outbox_delivered': True}`. The task delivered once and marked its outbox row complete; the second run was idempotent.

## Fresh-install proof

On the throwaway `fusion_integrated_fresh` database, the command sequence created the database, applied all app migrations (including `phc.0001_initial`), migrated PHC to zero, reapplied all migrations, seeded modules, seeded the PHC policy, and ran readiness. Observed final output: `2 module(s) registered`, `PHC is ready.`, `PHC is ready.` The database remains available for the required first browser action. The active development database already had PHC migration records 0001–0003 but lacked the corresponding PHC table, so it was not used for the fresh-install proof.

## Dependency audit

`UV_CACHE_DIR=/tmp/phc-uv-cache UV_TOOL_DIR=/tmp/phc-uv-tools uvx --from pip-audit pip-audit` exited 0: `No known vulnerabilities found`.

## Remaining work

- After the E2E account correction is approved and applied, run Playwright journeys, deep-link E2E, and the browser walkthrough including keyboard-only use. Record account names and server request logs for each journey.
- Complete the itemized security self-audit, list per-file test counts and journeys mapped to live use cases, and record independent review scorecards.
- Fresh install is proved on throwaway database `fusion_integrated_fresh`: all apps migrated, `phc.0001_initial` applied, PHC migrated to zero and reapplied, `seed_modules` printed `2 module(s) registered` / PHC active, policy seed and readiness each printed `PHC is ready.` The database remains available for the required first browser action.
- The ephemeral pip-audit run passed: `No known vulnerabilities found`.

The PHC implementation is committed as `2133ebc` on `module/phc` and pushed to the author's fork. Draft pull request: https://github.com/FusionIIIT/Fusion-Integrated/pull/656. The IAM manifest v2 seeder and `assign_role` command were already merged into upstream IAM `main` before this PHC PR was opened; no IAM-specific PR was needed.
