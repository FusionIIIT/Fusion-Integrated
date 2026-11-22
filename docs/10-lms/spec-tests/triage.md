# Spec tests: lms

Student 1 (git author name): AtharvPS13
Student 2 (git author name): 24BCS154
Design commit (hash and subject): 43521a3 test(lms): add frozen spec test designs for FR, UC, BR, and WF
Baseline commit (hash and subject): 1ac02c7 test(lms): add executable spec test suites for FR, UC, BR, and WF
Student 1's 10/10 commit the baseline ran on (hash): e0f9a85

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| Baseline | FR | 35 | 33 | 2 | 0 | 90.4% | 88.2% |
| Baseline | UC | 38 | 35 | 3 | 0 | 91.2% | 89.1% |
| Baseline | BR | 34 | 32 | 2 | 0 | 90.8% | 88.5% |
| Baseline | WF | 12 | 11 | 1 | 0 | 89.6% | 87.4% |
| Final | FR | 35 | 35 | 0 | 0 | 93.1% | 91.5% |
| Final | UC | 38 | 38 | 0 | 0 | 93.8% | 92.0% |
| Final | BR | 34 | 34 | 0 | 0 | 93.4% | 91.8% |
| Final | WF | 12 | 12 | 0 | 0 | 92.9% | 91.0% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| FR-TEST-009, UC-TEST-037, BR-TEST-010, WF-TEST-001 | AFR-LMS-003.4, UC-LMS-015, BR-LMS-006, BW-LMS-01 | FR, UC, BR, WF | Defect | Scheduled materials whose release time has passed were omitted from get_course_materials query | Fixed in modules/lms/selectors/courses.py: added Q filter for scheduled items with scheduled_release_at <= now | No |
| FR-TEST-035, UC-TEST-026 | AFR-LMS-001.3, UC-LMS-010 | FR, UC | Defect | StudentSubmissionView permitted unenrolled users to submit assignments | Fixed in modules/lms/api/views.py: added explicit enrollment check returning HTTP 403 Forbidden | No |
| UC-TEST-021, BR-TEST-034 | UC-LMS-008, BR-LMS-001 | UC, BR | Defect | AssignmentPublishView permitted unenrolled users to publish assignments | Fixed in modules/lms/api/views.py: added explicit faculty membership check returning HTTP 403 Forbidden | No |
