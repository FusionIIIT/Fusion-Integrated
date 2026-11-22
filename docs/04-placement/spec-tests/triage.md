# Spec tests: placement

Student 1 (git author name): Rohan
Student 2 (git author name): rohankuthuru27-hub
Design commit (hash and subject): 9ec9e85ee6a9fdec937545e11a8eab9d7cff9c20 spec(tests): freeze FR, UC, BR, and WF test designs
Baseline commit (hash and subject): TBD (baseline run commit)
Student 1's 10/10 commit the baseline ran on (hash): 108c9e5a456f796bdcd1b71ab6226a9a3c5f3ace docs(placement): add approved module blueprint and initial quality report

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 65 | 58 | 7 | 0 | 49.71 | 2.49 |
| baseline | UC | 66 | 59 | 7 | 0 | 50.32 | 4.10 |
| baseline | BR | 76 | 72 | 4 | 0 | 50.27 | 4.10 |
| baseline | WF | 18 | 17 | 1 | 0 | 48.80 | 1.87 |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|---|
| TC-UC-006-EXC | PC-UC-006 E1 | UC | Specification ambiguity | 409 Conflict returned vs 400 asserted | Aligned with api-conventions.md status code for state machine precondition refusal (409) | Yes |
| TC-BR-003-PROH | PC-BR-003 condition-false | BR | Specification ambiguity | 409 Conflict returned vs 400 asserted | Aligned with api-conventions.md status code for state machine precondition refusal (409) | Yes |
| TC-WF-BW_PC_01-PATH1 | BW-PC-01 primary-path | WF | Specification ambiguity | 409 Conflict returned vs 400 asserted | Aligned with api-conventions.md status code for state machine precondition refusal (409) | Yes |
| TC-FR-014-01 | PC-AFR-014 | FR | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies which handles registration | Yes |
| TC-UC-014-MAIN | PC-UC-014 Main Flow | UC | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies | Yes |
| TC-UC-014-ALT | PC-UC-014 Alternative Flow | UC | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies | Yes |
| TC-UC-014-EXC | PC-UC-014 Exception Flow | UC | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies | Yes |
| TC-BR-007-PERM | PC-BR-007 condition-true | BR | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies | Yes |
| TC-BR-007-PROH | PC-BR-007 condition-false | BR | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies | Yes |
| TC-BR-007-EXCP | PC-BR-007 stated-exception | BR | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies | Yes |
| TC-FR-001-01 | PC-AFR-001 | FR | Test-generation / test-implementation problem | 404 on /profile | Route to /api/v1/placement/profile/resume | Yes |
| TC-FR-002-01 | PC-AFR-002 | FR | Test-generation / test-implementation problem | 404 on /profile | Route to /api/v1/placement/profile/resume | Yes |
| TC-FR-003-01 | PC-AFR-003 | FR | Test-generation / test-implementation problem | 404 on /profile | Route to /api/v1/placement/profile/resume | Yes |
| TC-UC-001-MAIN | PC-UC-001 Main Flow | UC | Test-generation / test-implementation problem | 404 on /profile | Route to /api/v1/placement/profile/resume | Yes |
| TC-UC-001-ALT | PC-UC-001 Alternative Flow | UC | Test-generation / test-implementation problem | 404 on /profile | Route to /api/v1/placement/profile/resume | Yes |
| TC-FR-044-01 | PC-AFR-044 | FR | Test-generation / test-implementation problem | 404 on /offers/{id}/respond endpoint | Use correct response action endpoint | Yes |
| TC-FR-061-01 | PC-AFR-061 | FR | Test-generation / test-implementation problem | Unexpected kwarg 'summary' on PlacementRegistration | Use valid PlacementRegistration fields | Yes |
| TC-FR-062-01 | PC-AFR-062 | FR | Test-generation / test-implementation problem | Unexpected kwarg 'summary' on PlacementRegistration | Use valid PlacementRegistration fields | Yes |
| TC-UC-023-EXC | PC-UC-023 Exception Flow | UC | Confirmed implementation defect | Status 200 returned on empty resume profile | Student 1 fixes candidate profile check | Yes |
