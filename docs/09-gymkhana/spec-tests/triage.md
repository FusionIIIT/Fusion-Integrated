# Spec tests: gymkhana

Student 1 (git author name): Divyansh Agrawal
Student 2 (git author name): Student 2
Design commit (hash and subject): fe2f927 (spec-tests: freeze all four design files (FR/UC/BR/WF))
Baseline commit (hash and subject): da21557 (Gymkhana: implement domain, models, services, api views, client routes, and test suite)
Student 1's 10/10 commit the baseline ran on (hash): da2155799fa97ea03cb9d9b1d11bdb437010e209

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 39 | 36 | 0 | 3 | 74 | 44 |
| baseline | UC | 25 | 22 | 0 | 3 | 69 | 35 |
| baseline | BR | 44 | 42 | 1 | 1 | 74 | 48 |
| baseline | WF | 16 | 15 | 1 | 0 | 61 | 25 |
| final | FR | 36 | 36 | 0 | 0 | 74 | 44 |
| final | UC | 22 | 22 | 0 | 0 | 69 | 35 |
| final | BR | 43 | 43 | 0 | 0 | 74 | 48 |
| final | WF | 16 | 16 | 0 | 0 | 61 | 25 |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| FR-014 | CFR-GYM-003 / AFR-GYM-013 | FR | Test-generation / test-implementation problem | Successful session-booking code has no notification outbox or Celery task dispatch interface available for assertion. | Both students agreed that notification dispatch via external SMS/email gateways is not required in module-only mode per Problem Statement 4.1 ("External communication and physical gateway dispatch are handled by institute external services, not module data models") and the approved blueprint. Student 2 removed the skipped stub; obligation preserved in frozen design. | No |
| FR-016 | CFR-GYM-003 / AFR-GYM-015 | FR | Test-generation / test-implementation problem | Successful event-booking code has no notification outbox or Celery task dispatch interface available for assertion. | Both students agreed that notification dispatch via external SMS/email gateways is not required in module-only mode per Problem Statement 4.1 and the approved blueprint. Student 2 removed the skipped stub; obligation preserved in frozen design. | No |
| FR-027 | CFR-GYM-005 / AFR-GYM-025 | FR | Test-generation / test-implementation problem | Successful poll-creation code has no notification outbox or Celery task dispatch interface available for assertion. | Both students agreed that notification dispatch via external SMS/email gateways is not required in module-only mode per Problem Statement 4.1 and the approved blueprint. Student 2 removed the skipped stub; obligation preserved in frozen design. | No |
| UC-003 | UC-GYM-002 Main Flow | UC | Test-generation / test-implementation problem | Session booking notification dispatch has no observable outbox or Celery interface. | Both students agreed that notification dispatch via external SMS/email gateways is not required in module-only mode per Problem Statement 4.1 and the approved blueprint. Student 2 removed the skipped stub; obligation preserved in frozen design. | No |
| UC-005 | UC-GYM-003 Main Flow | UC | Test-generation / test-implementation problem | Event booking notification dispatch has no observable outbox or Celery interface. | Both students agreed that notification dispatch via external SMS/email gateways is not required in module-only mode per Problem Statement 4.1 and the approved blueprint. Student 2 removed the skipped stub; obligation preserved in frozen design. | No |
| UC-012 | UC-GYM-006 Main Flow | UC | Test-generation / test-implementation problem | Poll creation notification dispatch has no observable outbox or Celery interface. | Both students agreed that notification dispatch via external SMS/email gateways is not required in module-only mode per Problem Statement 4.1 and the approved blueprint. Student 2 removed the skipped stub; obligation preserved in frozen design. | No |
| BR-029 | BR-GYM-013 | BR | Test-generation / test-implementation problem | Target-audience poll notification dispatch has no observable outbox or Celery interface. | Both students agreed that notification dispatch via external SMS/email gateways is not required in module-only mode per Problem Statement 4.1 and the approved blueprint. Student 2 removed the skipped stub; obligation preserved in frozen design. | No |
| BR-032 | BR-GYM-014 — expired poll access denied | BR, WF | Confirmed implementation defect | BR-032 and WF-010 expect HTTP 400 for an expired poll; the implementation returned HTTP 409 Conflict. | Fixed in Student 1 commit by returning BadRequestError (HTTP 400) in modules/gymkhana/services/polls.py:cast_vote when voting on an expired poll. Both tests now pass. | No |
| WF-010 | BW-GYM-02 STT Transition 2 guard — expired poll | BR, WF | Confirmed implementation defect | WF-010 and BR-032 expect HTTP 400 for an expired poll; the implementation returned HTTP 409 Conflict. | Fixed in Student 1 commit by returning BadRequestError (HTTP 400) in modules/gymkhana/services/polls.py:cast_vote when voting on an expired poll. Both tests now pass. | No |
