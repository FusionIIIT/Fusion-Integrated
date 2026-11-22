# Spec tests: lms

Student 1 (git author name): Mohammad Maroof
Student 2 (git author name): K Lasya Reddy
Design commit (hash and subject): 435ec63 Freeze LMS specification test designs for FR, UC, BR, and WF
Baseline commit (hash and subject): c260594 Add executable spec test suites and baseline triage log
Student 1's 10/10 commit the baseline ran on (hash): 7444c49 Build LMS (Course Management) module to 10/10

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|---|---|---|---|---|---|---|---|
| baseline | FR | 47 | 47 | 0 | 0 | 25.10% | 32.70% |
| baseline | UC | 41 | 39 | 2 | 0 | 25.00% | 30.70% |
| baseline | BR | 36 | 33 | 3 | 0 | 25.50% | 30.80% |
| baseline | WF | 21 | 17 | 4 | 0 | 20.30% | 27.90% |
| q2 | FR | 47 | 47 | 0 | 0 | 42.90% | 37.50% |
| q2 | UC | 41 | 41 | 0 | 0 | 43.20% | 38.70% |
| q2 | BR | 36 | 36 | 0 | 0 | 37.60% | 33.70% |
| q2 | WF | 21 | 21 | 0 | 0 | 31.40% | 29.60% |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|---|
| TC-UC-15, TC-BR-15 | UC-LMS-005 Alt A1, BR-LMS-007 | UC, BR | Confirmed implementation defect | a8_results/uc/pytest.log (test_tc_uc_15_post_announcement_alternative_a1) | Fixed in 6333960: Permitted TA with lms.announcement.manage to post course announcements; verified by TC-UC-15 and TC-BR-15 passing | No |
| TC-UC-37, TC-BR-33, TC-WF-13, TC-WF-16, TC-WF-20, TC-WF-21 | UC-LMS-013, BR-LMS-017, BW-LMS-04, BW-LMS-05, CW-LMS-02 | UC, BR, WF | Confirmed implementation defect | a8_results/uc/pytest.log (test_tc_uc_37_release_grades_main_flow) | Fixed in 6333960: Implemented release_assignment_grades service to transition draft grades to released; verified by TC-UC-37, TC-BR-33, TC-WF-13, TC-WF-16, TC-WF-20, TC-WF-21 passing | No |
| TC-BR-36 | BR-LMS-019 | BR | Confirmed implementation defect | a8_results/br/pytest.log (test_tc_br_36_post_release_grade_change_audit) | Fixed in 6333960: Added GradeAuditLog model and recorded audit log on released grade changes; verified by TC-BR-36 passing | No |
