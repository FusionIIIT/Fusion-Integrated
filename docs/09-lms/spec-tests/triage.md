# Spec tests: lms

Student 1 (git author name): Mohammad Maroof
Student 2 (git author name): K Lasya Reddy
Design commit (hash and subject): 435ec63 Freeze LMS specification test designs for FR, UC, BR, and WF
Baseline commit (hash and subject): PENDING Add executable spec test suites and baseline triage log
Student 1's 10/10 commit the baseline ran on (hash): 7444c49 Build LMS (Course Management) module to 10/10

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|---|---|---|---|---|---|---|---|
| baseline | FR | 47 | 47 | 0 | 0 | 25.10% | 32.70% |
| baseline | UC | 41 | 39 | 2 | 0 | 25.00% | 30.70% |
| baseline | BR | 36 | 33 | 3 | 0 | 25.50% | 30.80% |
| baseline | WF | 21 | 17 | 4 | 0 | 20.30% | 27.90% |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|---|
| TC-UC-15, TC-BR-15 | UC-LMS-005 Alt A1, BR-LMS-007 | UC, BR | Confirmed implementation defect | a8_results/uc/pytest.log (test_tc_uc_15_post_announcement_alternative_a1) | Pending fix by Student 1: Permit TA with lms.announcement.manage to post course announcements | Yes |
| TC-UC-37, TC-BR-33, TC-WF-13, TC-WF-16, TC-WF-20, TC-WF-21 | UC-LMS-013, BR-LMS-017, BW-LMS-04, BW-LMS-05, CW-LMS-02 | UC, BR, WF | Confirmed implementation defect | a8_results/uc/pytest.log (test_tc_uc_37_release_grades_main_flow) | Pending fix by Student 1: Implement release_assignment_grades service to transition draft grades to released | Yes |
| TC-BR-36 | BR-LMS-019 | BR | Confirmed implementation defect | a8_results/br/pytest.log (test_tc_br_36_post_release_grade_change_audit) | Pending fix by Student 1: Add GradeAuditLog model and record audit log on released grade changes | Yes |
