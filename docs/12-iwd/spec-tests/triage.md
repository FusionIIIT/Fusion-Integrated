# Spec tests: iwd

Student 1 (git author name): Student 1
Student 2 (git author name): Student 2
Design commit (hash and subject): 4f1a28c test(iwd): freeze spec test designs for FR, UC, BR, and WF
Baseline commit (hash and subject): 8c3e91a test(iwd): baseline spec test suite and initial triage log
Student 1's 10/10 commit the baseline ran on (hash): 2d9b40f

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|---|---|---|---|---|---|---|---|
| baseline | FR | 6 | 5 | 1 | 0 | 89% | 82% |
| baseline | UC | 4 | 3 | 1 | 0 | 90% | 84% |
| baseline | BR | 8 | 6 | 2 | 0 | 92% | 85% |
| baseline | WF | 4 | 3 | 1 | 0 | 88% | 80% |
| final (Q2) | FR | 6 | 6 | 0 | 0 | 96% | 91% |
| final (Q2) | UC | 4 | 4 | 0 | 0 | 97% | 93% |
| final (Q2) | BR | 8 | 8 | 0 | 0 | 98% | 94% |
| final (Q2) | WF | 4 | 4 | 0 | 0 | 95% | 90% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome | Open? |
|---|---|---|---|---|---|---|
| test_br_009_rejection_reason_mandatory | BR-IWD-009 rejection-reason | BR | Confirmed implementation defect | Returned 200 on empty rejection reason | Fixed in commit 5a2109e: Added validate_rejection validator in EstimateViewSet | No |
| test_br_018_dean_hod_separation | BR-IWD-018 role-separation | BR | Confirmed implementation defect | Dean permitted to approve mid-range | Fixed in commit 6c8311a: Explicit check separating Dean from HOD in can_approve_estimate | No |
| test_fr_02_refuse_short_title | AFR-IWD-002 validation | FR | Confirmed implementation defect | Accepted single-character title | Fixed in commit 7d9422b: Added min_length=3 in ComplaintSerializer | No |
| test_wf_11_billing_audit_settlement | BW-IWD-11 settlement-flow | WF | Confirmed implementation defect | Settled directly without auditor verification flag | Fixed in commit 9e0533c: Added can_settle_payment guard check | No |
