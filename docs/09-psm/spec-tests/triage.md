# Spec tests: psm

Student 1 (git author name): Mohammad Waqaar Ahsab / TECHN0HACKER
Student 2 (git author name): shubham-ssrj-999
Design commit (hash and subject): 589ad54 test(psm): freeze specification-derived test designs
Baseline commit (hash and subject): c628c54 test(psm): add baseline spec test suites and triage log
Student 1's 10/10 commit the baseline ran on (hash): 302081dea00a5d7f3fc496060950b2c4db0e0341

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 52 | 51 | 0 | 1 | 77.76% | 50.85% |
| baseline | UC | 83 | 78 | 0 | 5 | 79.52% | 50.51% |
| baseline | BR | 47 | 47 | 0 | 0 | 90.63% | 66.44% |
| baseline | WF | 8 | 8 | 0 | 0 | 82.90% | 51.02% |
| Q2 | FR | 52 | 52 | 0 | 0 | 77.31% | 50.00% |
| Q2 | UC | 83 | 83 | 0 | 0 | 79.13% | 50.49% |
| Q2 | BR | 47 | 47 | 0 | 0 | 90.04% | 65.86% |
| Q2 | WF | 8 | 8 | 0 | 0 | 81.94% | 50.16% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| PSM-008 | AFR-PSM-011 | FR | Confirmed implementation defect | `test_psm_008` automates repeated draft edits and explicit submission. | 6d939fb; `test_psm_008` | No |
| TC-009-A1 | PSM-UC-008 / PSM-UC-009 | UC | Test-generation / test-implementation problem | `test_tc_009_a1_psm_uc_009_alternative_a1` verifies an adjustment below active reservations is refused with ledger and reservation integrity preserved. | Automated refusal test `test_tc_009_a1_psm_uc_009_alternative_a1` | No |
| TC-003-A2 | PSM-UC-003 | UC | Confirmed implementation defect | `test_tc_003_a2_psm_uc_003_alternative_a2` checks SLA flags, open discrepancies, and role-restricted detail fields from indent GET. | 6d939fb; `test_tc_003_a2_psm_uc_003_alternative_a2` | No |
| TC-007-A2 | PSM-UC-007 | UC | Test-generation / test-implementation problem | `test_tc_007_a2_psm_uc_007_alternative_a2` mocks unavailable stock balance reads and verifies no state or reservation is persisted. | Automated with mock `test_tc_007_a2_psm_uc_007_alternative_a2` | No |
| TC-014-A1 | PSM-UC-014 | UC | Test-generation / test-implementation problem | `test_tc_014_a1_psm_uc_014_alternative_a1` verifies faculty receives 403 and Auditor can read audit records. | Automated scope refusal test `test_tc_014_a1_psm_uc_014_alternative_a1` | No |
| TC-035-A2 | PSM-UC-035 | UC | Confirmed implementation defect | `test_tc_035_a2_psm_uc_035_alternative_a2` forces report row generation to fail and verifies failed logging with no success log. | 6d939fb; `test_tc_035_a2_psm_uc_035_alternative_a2` | No |
