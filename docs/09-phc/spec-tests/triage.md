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

## Final rerun

| Strategy | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| FR | 4 | 0 | 0 | 0 |
| UC | 7 | 0 | 0 | 0 |
| BR | 6 | 0 | 0 | 0 |
| WF | 4 | 0 | 0 | 0 |
| Combined | 21 | 0 | 0 | 0 |

The final results and machine-generated reports are under `results/`. Remaining specification gaps are listed in [`../quality-report.md`](../quality-report.md); no zero-findings claim is made.
