# Spec tests: mms

Student 1 (git author name): Nathan Dcunha
Student 2 (git author name): Gajji Sai Pavan Kumar
Design commit (hash and subject): 2cfe205 test(mms): freeze specification test designs for BR, WF, UC, and FR
Baseline commit (hash and subject): bee327a test(mms): add automated spec test suites and initial triage log
Student 1's 10/10 commit the baseline ran on (hash): 4bec614

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | BR | 41 | 18 | 0 | 23 | 24.4% | 0.0% |
| baseline | WF | 21 | 7 | 0 | 14 | 17.9% | 0.0% |
| baseline | UC | 70 | 23 | 0 | 47 | 29.0% | 0.0% |
| baseline | FR | 123 | 52 | 0 | 71 | 41.3% | 0.0% |
| final (Q2) | BR | 41 | 41 | 0 | 0 | 63.2% | 75.3% |
| final (Q2) | WF | 21 | 21 | 0 | 0 | 56.4% | 65.1% |
| final (Q2) | UC | 70 | 70 | 0 | 0 | 69.1% | 73.9% |
| final (Q2) | FR | 123 | 123 | 0 | 0 | 68.4% | 71.8% |
| **TOTAL** | **ALL** | **255** | **255** | **0** | **0** | **93.1%** | **78.2%** |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| DEF-001 | BR-MMS-014 | BR | Production bug | update_menu_item positional arguments mismatch | Fixed in modules/mms/services/mms.py to support flexible call signatures | No |
| DEF-002 | BR-MMS-021 | BR | Production bug | submit_rebate_request positional mess_name handling | Fixed in modules/mms/services/mms.py to parse both positional and keyword arguments | No |
| DEF-003 | MMS-UC-012 | UC | Production bug | FeedbackView required submit permission on GET endpoint | Fixed in modules/mms/api/views.py by scoping permission check to method | No |
| SKP-001..023 | BR-MMS-001..042 | BR | Unimplemented boundary tests | Auxiliary business rule enforcement skipped in baseline | Automated as executable Python/Django spec tests against rules and services (41/41 passing) | No |
| SKP-024..037 | CW-MMS-03..06 | WF | Unimplemented boundary tests | Vacation survey and special food workflows skipped in baseline | Automated as executable Django workflow tests against domain services (21/21 passing) | No |
| SKP-038..084 | MMS-UC-003..031 | UC | Unimplemented boundary tests | Core and auxiliary use case main flows skipped in baseline | Automated as executable Django/DRF tests against live services and selectors (70/70 passing) | No |
| SKP-085..155 | CFR/AFR-MMS-001..095 | FR | Unimplemented boundary tests | Extended functional requirements skipped in baseline | Automated as executable functional tests against rules, services, and audit logs (123/123 passing) | No |
