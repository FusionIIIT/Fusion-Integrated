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
| BR-035-01 | BR-VH-035 stated outcome | br | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. All BR tests passing. | No |
| FR-001 | AFR-VH-001; CFR roll-up CFR-VH-001 | fr | Resolved | Resolved DRF permission instantiation and added status history fields to `BookingSerializer`. | Fixed in `modules/vh/api/serializers.py` and `views.py`. | No |
| FR-002 | AFR-VH-002; CFR roll-up CFR-VH-001 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-003 | AFR-VH-003; CFR roll-up CFR-VH-001 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-004 | AFR-VH-005; CFR roll-up CFR-VH-002 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-005 | AFR-VH-006; CFR roll-up CFR-VH-002 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-006 | AFR-VH-007; CFR roll-up CFR-VH-002 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-007 | AFR-VH-008; CFR roll-up CFR-VH-002 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-008 | AFR-VH-009; CFR roll-up CFR-VH-002 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-009 | AFR-VH-010; CFR roll-up CFR-VH-002 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-010 | AFR-VH-011; CFR roll-up CFR-VH-002 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-011 | AFR-VH-012; CFR roll-up CFR-VH-002 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-012 | AFR-VH-013; CFR roll-up CFR-VH-002 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-013 | AFR-VH-014; CFR roll-up CFR-VH-003 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-015 | AFR-VH-016; CFR roll-up CFR-VH-003 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-016 | AFR-VH-017; CFR roll-up CFR-VH-003 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-017 | AFR-VH-018; CFR roll-up CFR-VH-003 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-018 | AFR-VH-019; CFR roll-up CFR-VH-003 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-019 | AFR-VH-020; CFR roll-up CFR-VH-003 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-020 | AFR-VH-021; CFR roll-up CFR-VH-004 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-021 | AFR-VH-022; CFR roll-up CFR-VH-004 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-022 | AFR-VH-023; CFR roll-up CFR-VH-004 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-023 | AFR-VH-024; CFR roll-up CFR-VH-004 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-024 | AFR-VH-025; CFR roll-up CFR-VH-004 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-026 | AFR-VH-027; CFR roll-up CFR-VH-006 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-027 | AFR-VH-028; CFR roll-up CFR-VH-006 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-028 | AFR-VH-029; CFR roll-up CFR-VH-006 | fr | Resolved | Resolved cancellation charge tiered rate computation. | Fixed in `modules/vh/api/views.py`. | No |
| FR-029 | AFR-VH-030; CFR roll-up CFR-VH-006 | fr | Resolved | Resolved cancellation charge tiered rate computation. | Fixed in `modules/vh/api/views.py`. | No |
| FR-030 | AFR-VH-031; CFR roll-up CFR-VH-006 | fr | Resolved | Resolved cancellation charge tiered rate computation. | Fixed in `modules/vh/api/views.py`. | No |
| FR-031 | AFR-VH-032; CFR roll-up CFR-VH-006 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-032 | AFR-VH-033; CFR roll-up CFR-VH-006 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-034 | AFR-VH-035; CFR roll-up CFR-VH-006 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-035 | AFR-VH-036; CFR roll-up CFR-VH-007 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-040 | AFR-VH-041; CFR roll-up CFR-VH-008 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-041 | AFR-VH-042; CFR roll-up CFR-VH-008 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-048 | AFR-VH-049; CFR roll-up CFR-VH-009 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-049 | AFR-VH-050; CFR roll-up CFR-VH-009 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-057 | AFR-VH-058; CFR roll-up CFR-VH-010 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-058 | AFR-VH-059; CFR roll-up CFR-VH-011 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-059 | AFR-VH-060; CFR roll-up CFR-VH-011 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-060 | AFR-VH-061; CFR roll-up CFR-VH-011 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-061 | AFR-VH-062; CFR roll-up CFR-VH-011 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-064 | AFR-VH-065; CFR roll-up CFR-VH-011 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-073 | AFR-VH-076; CFR roll-up CFR-VH-014 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-074 | AFR-VH-077; CFR roll-up CFR-VH-014 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-075 | AFR-VH-078; CFR roll-up CFR-VH-014 | fr | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-001-ALT-01 | UC-VH-001 Alternative Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-001-ALT-02 | UC-VH-001 Alternative Flow 2 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-001-MAIN | UC-VH-001 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-002-ALT-01 | UC-VH-002 Alternative Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-002-MAIN | UC-VH-002 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-003-ALT-01 | UC-VH-003 Alternative Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-003-ALT-02 | UC-VH-003 Alternative Flow 2 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-003-MAIN | UC-VH-003 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-004-ALT-01 | UC-VH-004 Alternative Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-004-ALT-02 | UC-VH-004 Alternative Flow 2 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-004-MAIN | UC-VH-004 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-005-ALT-01 | UC-VH-005 Alternative Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-005-MAIN | UC-VH-005 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-007-ALT-01 | UC-VH-007 Alternative Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-007-ALT-02 | UC-VH-007 Alternative Flow 2 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-007-ALT-03 | UC-VH-007 Alternative Flow 3 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-007-MAIN | UC-VH-007 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-008-ALT-01 | UC-VH-008 Alternative Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-008-MAIN | UC-VH-008 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-009-MAIN | UC-VH-009 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-013-ALT-01 | UC-VH-013 Alternative Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-013-ALT-02 | UC-VH-013 Alternative Flow 2 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-013-MAIN | UC-VH-013 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-020-EXC-01 | UC-VH-020 Exception Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-020-MAIN | UC-VH-020 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-021-EXC-01 | UC-VH-021 Exception Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-021-MAIN | UC-VH-021 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-023-ALT-01 | UC-VH-023 Alternative Flow 1 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-023-ALT-02 | UC-VH-023 Alternative Flow 2 | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| UC-023-MAIN | UC-VH-023 Main Flow | uc | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| WF-BW-VH-10 | BW-VH-10 approved stay path | wf | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| WF-CW-VH-01-OFF-04 | CW-VH-01 offline direct caretaker rejection; BW-VH-04 path | wf | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| WF-CW-VH-01-OFF-05 | CW-VH-01 offline forwarded approval; BW-VH-05 path | wf | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| WF-CW-VH-01-OFF-06 | CW-VH-01 offline forwarded rejection; BW-VH-06 path | wf | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| WF-CW-VH-01-ON-01 | CW-VH-01 online direct caretaker rejection; BW-VH-01 path | wf | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| WF-CW-VH-01-ON-02 | CW-VH-01 online forwarded approval; BW-VH-02 path | wf | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| WF-CW-VH-01-ON-03 | CW-VH-01 online forwarded rejection; BW-VH-03 path | wf | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| WF-CW-VH-02-07 | CW-VH-02 exactly 7 days before arrival branch; BW-VH-07 path | wf | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| WF-CW-VH-02-08 | CW-VH-02 within 7 days before arrival, excluding same-day branch; BW-VH-08 path | wf | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| WF-CW-VH-02-09 | CW-VH-02 on the day of arrival branch; BW-VH-09 path | wf | Resolved | Resolved DRF permission instantiation in `BookingViewSet.get_permissions()`. | Fixed in `modules/vh/api/views.py`. | No |
| FR-076 | AFR-VH-079; CFR roll-up CFR-VH-014 | fr | Unresolved | The test design asks to trigger check-in/check-out reminders, but the specification set does not define the reminder schedule or a triggering condition; UC-VH-024 Exception Flow 1 says the exact reminder schedule is not defined. | `NOT_AUTOMATED` (Agreed skip) pending both students' agreement on the UC-VH-024 exception reading. | No (Agreed skip) |
