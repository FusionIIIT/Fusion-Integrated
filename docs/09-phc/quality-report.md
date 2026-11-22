# PHC implementation and specification test report

**Specification:** PHC synchronized v1.1 bundle supplied by the project pair  
**Test design timing:** The implementation was visible during test design. The tests are specification-derived, but they were not designed blind.
**Scope:** PHC API, domain rules, workflows, reporting, and PHC model behavior covered by the four pytest strategies.

## Final observed test results

| Strategy | Cases | Passed | Failed | Skipped | Line coverage | Branch coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FR | 60 | 60 | 0 | 0 | 58.32% | 17.65% |
| UC | 76 | 76 | 0 | 0 | 81.63% | 52.94% |
| BR | 54 | 54 | 0 | 0 | 69.84% | 44.12% |
| WF | 25 | 25 | 0 | 0 | 65.90% | 14.71% |
| **Combined** | **215** | **215** | **0** | **0** | **97.71%** | **93.14%** |

The combined coverage is calculated from the single combined PHC test run and excludes the test files themselves. Per-strategy coverage uses the same PHC production-source denominator, so those percentages are not additive. Coverage is measured, not an estimate.

## Areas exercised

- Published and draft doctor schedules; weekday and time-range boundaries; attendance updates, status validation, and date handling.
- Patient record ownership, prescription ownership, staff search and record creation, PDF selection and content, and missing-record behavior.
- Employee reimbursement eligibility, prescription ownership and evidence, submission-window boundaries, configuration, ordered decisions, terminal states, audit history, and notifications.
- Inventory creation, stock thresholds, adjustments, audit rows, low-stock alerts, consumption reporting, requisition decisions, fulfillment, and stock separation.
- Ambulance logging, announcements and publication visibility, report anonymization and aggregation, notification recipient scoping, and missing-resource responses.

## Initial findings and fixes

See [`spec-tests/triage.md`](spec-tests/triage.md) for the actual initial runs and classification. The expanded test run found a monthly utilization-report error when Django returned a `date` value. The output formatting now accepts both `date` and `datetime`; the regression case passes in the final run. Initial test-import errors are recorded separately and were corrected without changing production code.

## Reproduction commands

The saved machine reports are in `spec-tests/results/expanded-final/{fr,uc,br,wf,all}/`. The final commands used a temporary SQLite test settings override because Docker Desktop could not start its Linux engine on this machine. That override was removed after the runs; it is not checked into the branch. The PHC migration remained enabled; unrelated Directory, Placement, and Access Control migrations were disabled for SQLite.

Equivalent commands for each strategy (substitute `uc`, `br`, or `wf` for `fr`) were:

```powershell
.\.venv\Scripts\python.exe -m pytest modules\phc\tests\test_fr.py `
  --ds=config.settings.test_phc_sqlite `
  --junitxml=docs\09-phc\spec-tests\results\expanded-final\fr\junit.xml `
  --cov=modules.phc.api --cov=modules.phc.domain --cov=modules.phc.models `
  --cov=modules.phc.selectors --cov=modules.phc.services --cov-branch `
  --cov-report=term `
  --cov-report=xml:docs\09-phc\spec-tests\results\expanded-final\fr\coverage.xml
```

The combined command was:

```powershell
.\.venv\Scripts\python.exe -m pytest modules\phc\tests `
  --ds=config.settings.test_phc_sqlite `
  --junitxml=docs\09-phc\spec-tests\results\expanded-final\all\junit.xml `
  --cov=modules.phc.api --cov=modules.phc.domain --cov=modules.phc.models `
  --cov=modules.phc.selectors --cov=modules.phc.services --cov-branch `
  --cov-report=term `
  --cov-report=xml:docs\09-phc\spec-tests\results\expanded-final\all\coverage.xml
```

## Other checks and limits

- The final PHC test run completed with **215 passed** and **15 Django REST Framework validator warnings** (`min_value should be an integer or Decimal instance`).
- Docker Desktop displayed **“Virtual Machine Platform not enabled”**. Starting the repository's PostgreSQL container therefore failed before PostgreSQL could start; enabling that Windows feature requires administrator access and a restart. These local results are SQLite results, not PostgreSQL results.
- The PR's GitHub Actions status must be read from the actual checks before reporting a PostgreSQL result.
- Final observed checks passed: `manage.py check`, `makemigrations --check --dry-run`, permission-manifest check, Ruff, Import Linter (5 contracts kept, 0 broken), and cross-module foreign-key check. Machine logs are in `spec-tests/results/expanded-final/checks/`.
- The module has backend endpoints; no PHC client screens were added in this test expansion.
