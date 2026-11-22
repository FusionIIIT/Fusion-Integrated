# Spec tests: iwd

Student 1 (git author name): Meet-Patel03
Student 2 (git author name): Ashmi
Design commit (hash and subject): c05bfb4 IWD spec-test design: FR, UC, BR, WF — frozen before code review
Baseline commit (hash and subject): 31d8c94 IWD spec tests: baseline and final triage — FR, UC, BR, WF strategies
Student 1's 10/10 commit the baseline ran on (hash): f70015d

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| baseline | FR | 60 | 52 | 8 | 0 | 90.2% | 83.5% |
| baseline | UC | 35 | 31 | 4 | 0 | 88.6% | 81.0% |
| baseline | BR | 40 | 34 | 6 | 0 | 93.8% | 89.2% |
| baseline | WF | 25 | 21 | 4 | 0 | 85.0% | 79.4% |
| final (Q2) | FR | 60 | 60 | 0 | 0 | 95.8% | 91.2% |
| final (Q2) | UC | 35 | 35 | 0 | 0 | 94.5% | 89.8% |
| final (Q2) | BR | 40 | 40 | 0 | 0 | 98.2% | 94.6% |
| final (Q2) | WF | 25 | 25 | 0 | 0 | 92.4% | 88.0% |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|:---:|
| TC_BR_009, TC_FR_021 | BR-IWD-003, CFR-IWD-04 | BR, FR | Confirmed implementation defect | High-cost threshold routing check was returning False at boundary 100,000 | Fixed in commit f70015d (enforced strict >100,000 check for director approval) | No |
| TC_FR_003, TC_UC_002 | CFR-IWD-01, UC-IWD-001 | FR, UC | Confirmed implementation defect | Validation error returned 500 instead of 400 on empty required fields | Fixed in commit f70015d (added DRF serializer field validation returning 400) | No |
| TC_BR_033, TC_WF_020 | BR-IWD-014, CW-IWD-01 | BR, WF | Confirmed implementation defect | Illegal transition from draft directly to complete was unguarded | Fixed in commit f70015d (validate_transition state machine enforced) | No |
| TC_WF_023 | CW-IWD-03 | WF | Confirmed implementation defect | Closed ticket could transition back to submitted | Fixed in commit f70015d (terminal closed state enforced) | No |
| TC_FR_028, TC_UC_018 | CFR-IWD-09, UC-IWD-061 | FR, UC | Confirmed implementation defect | Inventory low stock boolean logic inverted for minimum_stock | Fixed in commit f70015d (item.is_low_stock evaluates quantity <= minimum_stock) | No |
