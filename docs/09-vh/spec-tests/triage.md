# Spec tests: vh


Student 1 (git author name): demo
Student 2 (git author name): Bellam Gayathri
Design commit (hash and subject): e882dc31c8660bb4d53966c24cf5b8837b4f2883 — VH: freeze Student 2 spec test designs
Baseline commit (hash and subject): b869a14becb02f7aac26c5cfc08d3a731cda044b — VH module using AI
Student 1's 10/10 commit the baseline ran on (hash): not established; the baseline used b869a14becb02f7aac26c5cfc08d3a731cda044b


> Environment note: the repository test settings target PostgreSQL, but this workstation had no Docker or usable PostgreSQL credentials. The independent Q2 rerun used Python 3.13 with the SQLite test fallback (`USE_SQLITE=1`) and `MIGRATION_MODULES = {"placement": None}` to bypass the PostgreSQL-specific index drop migration. Logs, JUnit XML, and coverage XML are in the local, untracked `work/spec-results/Q2/` directory. Ruff reported 0 errors in `modules/vh/tests/spec`; repository-wide Ruff reported 126 errors. GitHub CI/E2E checks for commit `36f343a` were awaiting maintainer approval when checked.


## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | fr | 92 | 46 | 45 | 1 | 65.45 | 26.73 |
| baseline | uc | 50 | 20 | 30 | 0 | 63.21 | 24.26 |
| baseline | br | 38 | 22 | 16 | 0 | 59.02 | 21.78 |
| baseline | wf | 10 | 0 | 10 | 0 | 47.05 | 1.49 |
| Q2 (independent rerun) | fr | 92 | 91 | 0 | 1 | 76.94 | 48.05 |
| Q2 (independent rerun) | uc | 50 | 50 | 0 | 0 | 76.63 | 46.88 |
| Q2 (independent rerun) | br | 38 | 38 | 0 | 0 | 67.08 | 37.50 |
| Q2 (independent rerun) | wf | 10 | 10 | 0 | 0 | 60.56 | 24.22 |


## Q2 review status
The Q2 rerun was performed against commit `36f343a313428b3de94e89a078c56d527cede265` (Student 1 latest upload). Results: 189 passed, 1 skipped, 0 failed. FR-076 remains skipped (`NOT_AUTOMATED`); both students still need to agree on the UC-VH-024 exception reading or specify the reminder trigger. The assignment gate requiring no skipped spec tests is therefore not met. The previous `verified` coverage figures did not match this independent rerun and have been replaced with the measured Q2 coverage above.

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| BR-002-01 | BR-VH-002 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-003-01 | BR-VH-003 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-004-01 | BR-VH-004 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-005-01 | BR-VH-005 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-006-01 | BR-VH-006 stated outcome | br | Resolved | Resolved cancellation charge calculation and DRF permission instantiation. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-007-01 | BR-VH-007 stated outcome | br | Resolved | Resolved cancellation charge calculation and DRF permission instantiation. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-008-01 | BR-VH-008 stated outcome | br | Resolved | Resolved cancellation charge calculation and DRF permission instantiation. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-009-01 | BR-VH-009 stated outcome | br | Resolved | Resolved cancellation charge calculation and DRF permission instantiation. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-011-01 | BR-VH-011 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-012-01 | BR-VH-012 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-023-01 | BR-VH-023 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-024-01 | BR-VH-024 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-032-01 | BR-VH-032 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-033-01 | BR-VH-033 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| BR-034-01 | BR-VH-034 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
