# Spec tests: iaa
Student 1 (git author name): MUTTENI RISHITHA
Student 2 (git author name): charankudithi-cyber
Design commit (hash and subject): 7962144 Assignment 7 implementation
Baseline commit (hash and subject): 7962144 Assignment 7 implementation
Student 1's 10/10 commit the baseline ran on (hash): 7962144af4fadc20399726b29f2e4fd6c82693ff

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 46 | 45 | 1 | 0 | 47.0% | 44.2% |
| baseline | UC | 46 | 45 | 1 | 0 | 45.6% | 40.8% |
| baseline | BR | 39 | 38 | 1 | 0 | 34.9% | 24.8% |
| baseline | WF | 25 | 25 | 0 | 0 | 26.7% | 28.6% |
| Q2 | FR | 46 | 46 | 0 | 0 | 47.1% | 44.7% |
| Q2 | UC | 46 | 46 | 0 | 0 | 45.7% | 41.3% |
| Q2 | BR | 39 | 39 | 0 | 0 | 35.0% | 25.5% |
| Q2 | WF | 25 | 25 | 0 | 0 | 26.7% | 28.8% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with spec quote) |
|---|---|---|---|---|---|
| T-FR-29 | AFR-IAA-029 | FR | Confirmed implementation defect | `validate_travel_completeness` permitted arrival date earlier than departure date without raising `DomainValidationError` | Fixed in `modules/iaa/domain/rules.py` by validating `arrival_date >= departure_date` |
| T-UC-26 | IAA-UC-103 Exception E1 | UC | Confirmed implementation defect | `submit_travel_claim` permitted return date earlier than departure date without raising `DomainValidationError` | Fixed in `modules/iaa/domain/rules.py` by validating `arrival_date >= departure_date` |
| T-BR-26 | IAA-BR-015 arrival-lt-departure | BR | Confirmed implementation defect | `validate_travel_completeness` failed to reject arrival date earlier than departure date | Fixed in `modules/iaa/domain/rules.py` by validating `arrival_date >= departure_date` |
