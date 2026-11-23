# Spec tests: psm

Student 1 (git author name): TECHN0HACKER
Student 2 (git author name): 24BCS237
Design commit (hash and subject): 589ad54 test(psm): freeze specification-derived test designs
Baseline commit (hash and subject): pending (baseline commit of modules/psm/tests/spec/ + triage.md)
Student 1's 10/10 commit the baseline ran on (hash): 302081dea00a5d7f3fc496060950b2c4db0e0341

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 52 | 51 | 0 | 1 | 77.76% | 50.85% |
| baseline | UC | 83 | 78 | 0 | 5 | 79.52% | 50.51% |
| baseline | BR | 47 | 47 | 0 | 0 | 90.63% | 66.44% |
| baseline | WF | 8 | 8 | 0 | 0 | 82.90% | 51.02% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| PSM-008 | AFR-PSM-011 | FR | Confirmed implementation defect | `test_psm_008` skipped (`NOT_AUTOMATED: the available edit operation submits a draft as part of saving, so the specified editable-before-submission state cannot be inspected.`) | Pending Student 1 fix (allow saving repeated draft edits while keeping draft status) & Student 2 automation | Yes |
| TC-009-A1 | PSM-UC-008 / PSM-UC-009 | UC | Unresolved | `test_tc_009_a1_psm_uc_009_alternative_a1` skipped (`NOT_AUTOMATED: A8_BASE has no interface to apply a verified inventory correction below an active reservation; adjustment validation blocks it first.`) | Pending pair spec review (BR-PSM-013 vs PSM-UC-008/009) | Yes |
| TC-003-A2 | PSM-UC-003 | UC | Confirmed implementation defect | `test_tc_003_a2_psm_uc_003_alternative_a2` skipped (`NOT_AUTOMATED: the indent status API serializer does not expose SLA reminder, escalation, or discrepancy status for this assertion.`) | Pending Student 1 fix (expose SLA/escalation/discrepancy status in indent serializer) & Student 2 automation | Yes |
| TC-007-A2 | PSM-UC-007 | UC | Unresolved | `test_tc_007_a2_psm_uc_007_alternative_a2` skipped (`NOT_AUTOMATED: A8_BASE stock checks read the local database and provide no supported unavailable-stock-service state to exercise.`) | Pending pair spec review / test-implementation check (mocking unavailable dependency or spec check) | Yes |
| TC-014-A1 | PSM-UC-014 | UC | Unresolved | `test_tc_014_a1_psm_uc_014_alternative_a1` skipped (`NOT_AUTOMATED: A8_BASE audit access is granted role-wide and has no per-record scope input to represent excluded audit records.`) | Pending pair spec review (PSM-UC-014 Alternative A1 vs role-wide audit scope) | Yes |
| TC-035-A2 | PSM-UC-035 | UC | Confirmed implementation defect | `test_tc_035_a2_psm_uc_035_alternative_a2` skipped (`NOT_AUTOMATED: the scheduled-report runner has no failure injection or logged-failure path; report generation errors propagate without a failed log.`) | Pending Student 1 fix (log failed scheduled report execution per BR-PSM-024) & Student 2 automation | Yes |
