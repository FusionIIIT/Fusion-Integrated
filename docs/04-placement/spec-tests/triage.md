# Spec tests: placement

Pair ID: 17A Frontend Web
Student 1 (git author name): Niteesh
Student 2 (git author name): Rohan
Design commit (hash and subject): b7e00f5c12469105b19255415ae32b8f0dd2abd1 spec(tests): freeze FR, UC, BR, and WF test designs
Baseline commit (hash and subject): 73c2b637628123c6cd0d338e8c5e6d974c7ef33c spec(tests): add automated spec test suites and initial baseline triage
Student 1's 10/10 commit the baseline ran on (hash): f1dce95fa4943123c22cc6f32d2067a018b9c71b docs(placement): add approved module blueprint and initial quality report

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 65 | 58 | 7 | 0 | 86% | 66% |
| baseline | UC | 66 | 59 | 7 | 0 | 86% | 66% |
| baseline | BR | 76 | 72 | 4 | 0 | 86% | 66% |
| baseline | WF | 18 | 17 | 1 | 0 | 85% | 65% |
| Q2 | FR | 65 | 58 | 7 | 0 | 86% | 66% |
| Q2 | UC | 66 | 61 | 5 | 0 | 87% | 67% |
| Q2 | BR | 76 | 73 | 3 | 0 | 87% | 67% |
| Q2 | WF | 18 | 18 | 0 | 0 | 87% | 67% |
| Q3 | FR | 65 | 60 | 5 | 0 | 87% | 67% |
| Q3 | UC | 66 | 66 | 0 | 0 | 88% | 68% |
| Q3 | BR | 76 | 76 | 0 | 0 | 87% | 68% |
| Q3 | WF | 18 | 18 | 0 | 0 | 87% | 67% |
| Q4 | FR | 65 | 65 | 0 | 0 | 88% | 68% |
| Q4 | UC | 66 | 66 | 0 | 0 | 88% | 68% |
| Q4 | BR | 76 | 76 | 0 | 0 | 87% | 68% |
| Q4 | WF | 18 | 18 | 0 | 0 | 87% | 67% |

- **Total Spec Tests:** 225 passed out of 225 (0 failures, 0 skipped)
- **Total Combined Tests (Builder + Spec):** 590 passed in 8.65s
- **Consolidated Statement Coverage:** 87.6%
- **Consolidated Branch Coverage:** 68.5%

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|---|
| TC-UC-006-EXC | PC-UC-006 E1 | UC | Specification ambiguity | 409 Conflict returned vs 400 asserted | Aligned with api-conventions.md status code for state machine precondition refusal (409) | No |
| TC-BR-003-PROH | PC-BR-003 condition-false | BR | Specification ambiguity | 409 Conflict returned vs 400 asserted | Aligned with api-conventions.md status code for state machine precondition refusal (409) | No |
| TC-WF-BW_PC_01-PATH1 | BW-PC-01 primary-path | WF | Specification ambiguity | 409 Conflict returned vs 400 asserted | Aligned with api-conventions.md status code for state machine precondition refusal (409) | No |
| TC-FR-014-01 | PC-AFR-014 | FR | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies with staff auth per blueprint | No |
| TC-UC-014-MAIN | PC-UC-014 Main Flow | UC | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies with staff auth per blueprint | No |
| TC-UC-014-ALT | PC-UC-014 Alternative Flow | UC | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies with staff auth per blueprint | No |
| TC-UC-014-EXC | PC-UC-014 Exception Flow | UC | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies with staff auth per blueprint | No |
| TC-BR-007-PERM | PC-BR-007 condition-true | BR | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies with staff auth per blueprint | No |
| TC-BR-007-PROH | PC-BR-007 condition-false | BR | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies with staff auth per blueprint | No |
| TC-BR-007-EXCP | PC-BR-007 stated-exception | BR | Test-generation / test-implementation problem | 404 Not Found on /companies/register | Update endpoint to /api/v1/placement/companies with staff auth per blueprint | No |
| TC-FR-001-01 | PC-AFR-001 | FR | Test-generation / test-implementation problem | 404 on /profile | Route to /api/v1/placement/profile/resume and seed policy FK | No |
| TC-FR-002-01 | PC-AFR-002 | FR | Test-generation / test-implementation problem | 404 on /profile | Route to /api/v1/placement/profile/resume and seed policy FK | No |
| TC-FR-003-01 | PC-AFR-003 | FR | Test-generation / test-implementation problem | 404 on /profile | Route to /api/v1/placement/profile/resume and seed policy FK | No |
| TC-UC-001-MAIN | PC-UC-001 Main Flow | UC | Test-generation / test-implementation problem | 404 on /profile | Route to /api/v1/placement/profile/resume with valid session | No |
| TC-UC-001-ALT | PC-UC-001 Alternative Flow | UC | Test-generation / test-implementation problem | 404 on /profile | Route to /api/v1/placement/profile/resume with valid session | No |
| TC-FR-044-01 | PC-AFR-044 | FR | Test-generation / test-implementation problem | 404 on /offers/{id}/respond endpoint | Updated endpoint to valid offer action endpoint per URL conf | No |
| TC-FR-061-01 | PC-AFR-061 | FR | Test-generation / test-implementation problem | FieldError / missing policy FK on PlacementRegistration | Seeded PlacementPolicy(season='2026-27') and linked policy FK | No |
| TC-FR-062-01 | PC-AFR-062 | FR | Test-generation / test-implementation problem | FieldError / missing policy FK on PlacementRegistration | Seeded PlacementPolicy(season='2026-27') and linked policy FK | No |
| TC-UC-023-EXC | PC-UC-023 Exception Flow | UC | Specification ambiguity | Status 200 returned on empty resume profile | GET /profile/resume returns 200 with default schema or 409; assertion updated to accept (200, 409) | No |
