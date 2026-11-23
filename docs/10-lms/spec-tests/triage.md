# Spec tests: lms

Student 1 (git author name): DenishShiroya22
Student 2 (git author name): VedhaSree-S
Design commit (hash and subject): ac8df950a513e5b47e5fe2e0237c1b631e138b85 spec(lms): freeze FR, UC, BR and WF test designs
Baseline commit (hash and subject): badd3a635bef15ef9f38579fc2cf5ba41fa1ee29 spec(lms): record baseline spec tests and triage log
Student 1's 10/10 commit the baseline ran on (hash): f09c49dbb38c0e0328b6668466b009a68b9b5946

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | WF | 20 | 18 | 2 | 0 | 78.5% | 75.7% |
| baseline | BR | 45 | 42 | 3 | 0 | 82.4% | 77.9% |
| baseline | UC | 47 | 44 | 3 | 0 | 84.4% | 76.5% |
| baseline | FR | 51 | 50 | 1 | 0 | 86.1% | 76.5% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| TEST-BR-038 / TEST-UC-038 | BR-LMS-015 condition-false-self-grading / UC-LMS-012 Exception Flow Conflict | BR, UC | Confirmed implementation defect | Approver ruling mandates that grader cannot grade own submission; backend `save_grade` currently lacks self-grading check and returns 200. | Student 1 fixes code in `modules/lms/services/grading.py` to enforce `grader_user_id != submission.user_id` returning 422/403 (`CANNOT_GRADE_OWN_SUBMISSION`). | Yes |
| TEST-WF-002 / TEST-WF-008 / TEST-BR-014 / TEST-UC-045 | BW-LMS-01 Step 2 / BW-LMS-03 Step 3 / BR-LMS-006 condition-true-after-time / UC-LMS-015 Main Flow Assignment | WF, BR, UC | Test-generation / test-implementation problem | Post-release student verification was called outside the `freeze_time` context where `published_at <= timezone.now()` was not satisfied by the scoping selector. | Student 2 encapsulated student verification calls inside active release timestamp. Passing. | No |
| TEST-BR-028 | BR-LMS-012 condition-true-file | BR | Test-generation / test-implementation problem | Test payload used raw BytesIO without valid document magic header (%PDF-1.7), causing file validator to reject with 422. | Student 2 updated test payload to use `SimpleUploadedFile` with valid PDF magic bytes. Passing. | No |
| TEST-UC-046 | UC-LMS-015 Alternative Flow | UC | Test-generation / test-implementation problem | Test asserted on model existence after deletion without calling the withdraw endpoint. | Student 2 updated test to call `POST /api/v1/lms/materials/{id}/withdraw/`. Passing. | No |
| TEST-FR-002 | AFR-LMS-001.2 | FR | Test-generation / test-implementation problem | `world.fake.users` was set before `world.actor("student")`, which re-initialized the IAM fixture and cleared the mock user table. | Student 2 configured `world.fake.users` after instantiating client session. Passing. | No |
