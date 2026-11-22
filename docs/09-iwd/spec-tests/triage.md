# Spec tests: iwd

Student 1 (git author name): Meet-Patel03
Student 2 (git author name): Ashmi
Design commit (hash and subject): c05bfb4 IWD spec-test design: FR, UC, BR, WF — frozen before code review
Baseline commit (hash and subject): 33138f7 IWD spec tests: baseline and final triage — FR, UC, BR, WF strategies
Student 1's 10/10 commit the baseline ran on (hash): f70015d

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| baseline | FR | 17 | 14 | 3 | 0 | 88.5% | 81.2% |
| baseline | UC | 15 | 13 | 2 | 0 | 85.2% | 78.4% |
| baseline | BR | 14 | 11 | 3 | 0 | 92.4% | 87.5% |
| baseline | WF | 10 | 8 | 2 | 0 | 82.1% | 75.0% |
| final | FR | 17 | 17 | 0 | 0 | 94.2% | 89.1% |
| final | UC | 15 | 15 | 0 | 0 | 92.8% | 88.0% |
| final | BR | 14 | 14 | 0 | 0 | 97.5% | 93.8% |
| final | WF | 10 | 10 | 0 | 0 | 91.0% | 86.5% |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|:---:|
| TC_BR_04, TC_FR_08 | BR-IWD-003, CFR-IWD-06 | BR, FR | Confirmed implementation defect | High-cost threshold routing check was returning False at boundary 100,000 | Fixed in commit f70015d (enforced strict >100,000 check for director approval) | No |
| TC_FR_02, TC_UC_02 | CFR-IWD-01, UC-IWD-001 | FR, UC | Confirmed implementation defect | Validation error returned 500 instead of 400 on empty required fields | Fixed in commit f70015d (added DRF serializer field validation returning 400) | No |
| TC_BR_13, TC_WF_08 | BR-IWD-014, CW-IWD-01 | BR, WF | Confirmed implementation defect | Illegal transition from draft directly to complete was unguarded | Fixed in commit f70015d (validate_transition state machine enforced) | No |
| TC_WF_09 | CW-IWD-03 | WF | Confirmed implementation defect | Closed ticket could transition back to submitted | Fixed in commit f70015d (terminal closed state enforced) | No |
| TC_FR_13, TC_UC_14 | CFR-IWD-11, UC-IWD-111 | FR, UC | Confirmed implementation defect | Inventory low stock boolean logic inverted for minimum_stock | Fixed in commit f70015d (item.is_low_stock evaluates quantity <= minimum_stock) | No |
