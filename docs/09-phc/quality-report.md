# PHC implementation and specification test report

**Run date:** 2026-11-22  
**Specification:** PHC synchronized v1.1 bundle supplied by the project pair  
**Test scope:** PHC Django module and its registered API integration

## Observed strategy results

| Strategy | Tests | Passed | Failed | Skipped | PHC line coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| FR | 4 | 4 | 0 | 0 | 21.49% |
| UC | 7 | 7 | 0 | 0 | 62.73% |
| BR | 6 | 6 | 0 | 0 | 59.73% |
| WF | 4 | 4 | 0 | 0 | 60.33% |
| **Combined** | **21** | **21** | **0** | **0** | **86.93%** |

The combined coverage is for `modules.phc` under the combined PHC suite. The four strategy coverage values are each from that strategy run alone; they are not additive.

## Commands executed

Each strategy used the matching `test_<strategy>.py` file and the same result options shown below, substituting `fr`, `uc`, `br`, or `wf`:

```powershell
.\.venv\Scripts\python.exe -m pytest modules\phc\tests\test_fr.py -q --ds=config.settings.test_phc_sqlite --junitxml=docs\09-phc\spec-tests\results\fr\junit.xml --cov=modules.phc --cov-report=xml:docs\09-phc\spec-tests\results\fr\coverage.xml --cov-report=term
.\.venv\Scripts\python.exe -m pytest modules\phc\tests -q --ds=config.settings.test_phc_sqlite --junitxml=docs\09-phc\spec-tests\results\all\junit.xml --cov=modules.phc --cov-report=xml:docs\09-phc\spec-tests\results\all\coverage.xml --cov-report=term
.\.venv\Scripts\python.exe manage.py check --settings=config.settings.test_phc_sqlite
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.test_phc_sqlite
.\.venv\Scripts\python.exe manage.py permission_manifest --check --settings=config.settings.test_phc_sqlite
.\.venv\Scripts\ruff.exe check modules\phc --no-cache
.\.venv\Scripts\lint-imports.exe
.\.venv\Scripts\python.exe ops\checks\no_cross_module_fk.py
```

## Requirement-to-test traceability

| Strategy file | Requirement areas exercised |
| --- | --- |
| `test_fr.py` | CFR-PHC-003 reimbursement eligibility/window; CFR-PHC-004 and CFR-PHC-011 transition actor/order; CFR-PHC-006 strict low-stock boundary |
| `test_uc.py` | PHC-UC-01/02/03/06/11/12/13; AFR-PHC-006/007/008/009/010/011/034; patient ownership and staff authorization |
| `test_br.py` | PHC-BR-02/03/04/05/06/07/09/12; claim eligibility/ownership/window, role access, audit, low-stock alert, report privacy |
| `test_wf.py` | BW-PHC-01/02, CW-PHC-01; BW-PHC-03/04, CW-PHC-02; audit, notification, terminal-state, and no-stock-autoupdate behavior |

This is the coverage of the current tests, not an assertion that every active requirement is fully verified. The open requirement areas below remain visible.

## Checks run

| Check | Result |
| --- | --- |
| `manage.py check` | Passed: no issues reported |
| `makemigrations --check --dry-run` | Passed: no changes detected |
| Permission manifest check | Passed: manifest matches module registries |
| Ruff on `modules/phc` | Passed |
| Import Linter | Passed: 5 contracts kept, 0 broken |
| Cross-module foreign-key check | Passed: no cross-module foreign keys |

## Environment and limits

The repository's Docker Postgres service could not start because Docker Desktop's Linux engine was unavailable. The PHC tests and Django checks therefore used a temporary local `config.settings.test_phc_sqlite` override. This runner kept the PHC migration enabled and disabled unrelated directory, placement, and access-control migrations, which fail on SQLite. That temporary settings file was removed from the PR contents; the recorded results do not substitute for running the repository's PostgreSQL CI job.

The implementation was already visible while the test designs were being prepared. These are specification-derived tests created after implementation, not blind or pre-implementation designs. The suite covers selected high-risk paths and is not a claim that every active AFR has a test.

## Remaining specification gaps

- The demographics report groups aggregate patient and visit counts by student/employee category using the Directory contract. It does not claim age/gender dimensions that the supplied requirements do not define.
- Schedule and current-day attendance are exposed through separate API endpoints. The module has no PHC client UI that demonstrates their combined presentation to patients (CFR-PHC-001).
- The local run used SQLite. PostgreSQL migration/application behavior remains to be confirmed by GitHub Actions or a local PostgreSQL run.
- No client-side PHC routes or screens were part of this backend test scope.

## Evidence

Raw per-strategy logs, JUnit XML, and coverage XML are in `spec-tests/results/{fr,uc,br,wf}/`. The combined run is in `spec-tests/results/all/`. Initial failures and their triage are retained under `spec-tests/results/initial/`.
