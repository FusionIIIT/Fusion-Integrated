# Spec tests: complaints

Student 1 (git author name): kushagra-005
Student 2 (git author name): ashish20513
Design commit (hash and subject): 1df9db8 feat(complaints): add Prompt A spec test designs for FR, UC, BR, and WF strategies
Baseline commit (hash and subject): a5ea561 feat(complaints): implement spec tests and establish baseline triage for Q1
Student 1's 10/10 commit the baseline ran on (hash): 802f91e

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 26 | 24 | 2 | 0 | 75.7% | 68.2% |
| baseline | UC | 25 | 24 | 1 | 0 | 73.5% | 71.0% |
| baseline | BR | 23 | 21 | 2 | 0 | 63.0% | 65.4% |
| baseline | WF | 21 | 21 | 0 | 0 | 74.3% | 70.8% |
| Q2 | FR | 26 | 26 | 0 | 0 | 75.7% | 68.2% |
| Q2 | UC | 25 | 25 | 0 | 0 | 73.5% | 71.0% |
| Q2 | BR | 23 | 23 | 0 | 0 | 63.0% | 65.4% |
| Q2 | WF | 21 | 21 | 0 | 0 | 74.3% | 70.8% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| FR-010 | CFR-010 sla-automatic-escalation | FR, BR | Confirmed implementation defect | SLA check background execution required explicit transactional lock when resolving simultaneous overdue complaints | Resolved in commit a8fc01d via select_for_update; verified passing in Q2. | No |
| BR-005 | BR-005 feedback-uniqueness-constraint | BR, FR | Confirmed implementation defect | Duplicate post-closure feedback submission must strictly return 400 with validation error rather than database IntegrityError | Resolved in commit a8fc01d in ComplaintFeedbackSerializer; verified passing in Q2. | No |
| UC-010 | UC-CMS-010 manual-escalation-limit | UC, BR | Confirmed implementation defect | Attempting to escalate an already escalated complaint should return HTTP 400 validation error | Resolved in commit a8fc01d in domain guard; verified passing in Q2. | No |
