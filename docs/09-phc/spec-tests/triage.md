# PHC specification test triage

This log records the first observed failures and the reruns. “Initial” refers to the first run of these tests against the existing PHC branch; implementation was visible during test design.

## Initial findings and actions

| Finding | Evidence | Classification | Action / result |
| --- | --- | --- | --- |
| SQLite setup stopped in an unrelated placement migration while dropping `document_profile_idx`. | Initial command output is summarized in `results/initial/environment-and-checks.md`; no raw pytest artifact was retained for this attempt. | Local test-environment incompatibility; not a PHC failure. | Used a temporary SQLite settings module that skips unrelated app migrations and keeps PHC migration active. Docker Postgres was unavailable because Docker Desktop's engine was stopped. |
| First BR/WF API tests used multiple clients created before requests; the shared IAM test stub then authenticated requests as the last configured actor. | `results/initial/br/pytest.log`, `results/initial/wf/pytest.log`. | Test harness isolation defect. | Changed tests to configure each actor immediately before its request. Corrected strategy suites pass. |
| Inventory-consumption report request returned HTTP 400 because the report type was unsupported. | `results/initial/uc/pytest.log`. | Product defect; AFR-PHC-034 / CFR-PHC-010. | Added aggregate consumed quantities derived from negative `InventoryAudit.delta` rows. UC test passes after the fix. |
| Demographics report returned only total visits and did not group patients by category. | `results/initial/br/demographics-baseline.log`. | Product defect; AFR-PHC-034 / CFR-PHC-010. | Added anonymized student/employee aggregates using the Directory public contract; the focused BR test passes after the fix. |
| Staff patient search returned 404 because PHC had no patient-search endpoint. | `results/initial/uc/patient-search-baseline.log`. | Product defect; AFR-PHC-006 / PHC-UC-06. | Added staff-only patient search through the directory public contract, returning minimal profile fields. UC test passes after the fix. |
| One first post-fix consumption assertion expected a formatted decimal string (`5.00`) while the database returned the equivalent numeric string (`5`). | `results/initial/uc/post-fix-format-assertion.log`. | Test oracle formatting assumption. | Compare parsed `Decimal` values; the behavioral assertion passes. |
| Permission manifest check found the generated manifest stale because PHC had no `modules/phc/registry.py`. | Initial command output is summarized in `results/initial/environment-and-checks.md`. | Product integration defect; PHC-BR-03 / AFR-PHC-036. | Added PHC module permissions, role grants, and navigation registry, then generated and checked the manifest successfully. |
| Migration check proposed an expense-date `help_text` alteration after style cleanup. | Initial command output is summarized in `results/initial/environment-and-checks.md`. | Migration/model drift. | Updated the initial PHC migration to match the model; final check reports no changes. |
| Import Linter found a direct PHC-test import from `modules.directory.models`. | Initial command output is summarized in `results/initial/environment-and-checks.md`. | Test architecture boundary violation. | Replaced it with a stub of the public directory contract. Final import check passes. |

## Final expanded rerun

| Strategy | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| FR | 60 | 0 | 0 | 0 |
| UC | 76 | 0 | 0 | 0 |
| BR | 54 | 0 | 0 | 0 |
| WF | 25 | 0 | 0 | 0 |
| Combined | 215 | 0 | 0 | 0 |

The final expanded reports are under `results/expanded-final/`. The combined run measured 97.71% line coverage and 93.14% branch coverage. Its log records 15 Django REST Framework `min_value` validator warnings. Remaining limits are listed in [`../quality-report.md`](../quality-report.md); these results do not claim that every possible defect is absent.

## Earlier 160-case run

The first 160-case expansion produced 142 passing and 18 failing test items. All 18 were test-harness `NameError`s: two UC items lacked a `Decimal` import, and 16 WF items lacked a `ReimbursementClaim` import. No PHC product defect was exposed by those failures. The imports were corrected, and the 160-case rerun passed. Its raw reports remain under `results/expanded-initial/` and are superseded by the 215-case reports above.

## Expanded coverage run (initial)

The expanded suite was run against the unchanged implementation before making any new production-code fix. The run produced 215 collected cases: 213 passed, 2 failed, 0 errors, and 0 skipped. The combined coverage report measured 97.71% line coverage and 93.14% branch coverage. These are initial results with failing tests, not final passing results. Machine output is preserved under `results/expanded-initial-coverage/`.

| Finding | Evidence | Classification | Proposed smallest fix |
| --- | --- | --- | --- |
| Utilization report raised `AttributeError: 'datetime.date' object has no attribute 'date'` when month aggregation returned a `date`. | `results/expanded-initial-coverage/br/pytest.log`; `results/expanded-initial-coverage/all/pytest.log` | Product defect in the monthly utilization output path. | Format the `TruncMonth` value with a type-safe conversion that accepts both `date` and `datetime`; add a regression assertion for month grouping. |
| Inventory report test referenced `InventoryItem` without importing it. | `results/expanded-initial-coverage/br/pytest.log` | Test-harness import error; not a product defect. | Import the model in the test, then rerun. |

No production changes were made before preserving this initial evidence. After recording it, the utilization formatting fix was applied and the missing test import was corrected. The post-fix combined run passed all 215 cases; its logs and coverage are under `results/expanded-final/`.
