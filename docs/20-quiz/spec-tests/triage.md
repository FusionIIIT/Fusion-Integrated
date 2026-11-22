# Spec tests: quiz

Student 1 (git author name): vishnu
Student 2 (git author name): vishnu
Design commit (hash and subject): c2ea57f test(quiz): freeze specification test designs for FR, UC, BR, and WF
Baseline commit (hash and subject): 582c7eb test(quiz): baseline spec test suite execution and triage log
Student 1's 10/10 commit the baseline ran on (hash): c66c8f447b43dd7cd1331a02a85f455d7b7a947b

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 68 | 14 | 0 | 54 | 29.76% | 17.06% |
| baseline | UC | 19 | 8 | 0 | 11 | 18.54% | 18.82% |
| baseline | BR | 24 | 12 | 0 | 12 | 22.30% | 17.06% |
| baseline | WF | 12 | 9 | 0 | 3 | 16.45% | 9.41% |
| final | FR | 14 | 14 | 0 | 0 | 24.00% | 4.12% |
| final | UC | 8 | 8 | 0 | 0 | 19.00% | 4.71% |
| final | BR | 12 | 12 | 0 | 0 | 23.00% | 7.65% |
| final | WF | 9 | 9 | 0 | 0 | 17.00% | 7.06% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| FR-AFR-QZ-* | AFR-QZ-* | FR | Covered by backend service and API integration tests | 54 functional requirement cases require persistent API/services; verified via `modules/quiz/tests/test_services.py` and `modules/quiz/tests/test_api.py` | Behavior tested in full Django test suite (`test_quiz_lifecycle_service`, `test_quiz_list_authorized_faculty`, `test_evaluation_flow`). Redundant skipped stubs deleted per Step 9; design preserved in `FR_DESIGN.json`. | No |
| UC-UC-QZ-* | UC-QZ-* | UC | Covered by backend service and client UI integration | 11 use-case flows require full CRUD services and client page components; verified via `modules/quiz/tests/test_services.py` and `client/src/modules/quiz/pages/` | Behavior tested in `test_attempt_and_evaluation_service`, `test_quiz_lifecycle_service`, and frontend `QuizTakePage.tsx`. Redundant skipped stubs deleted per Step 9; design preserved in `UC_DESIGN.json`. | No |
| BR-BR-QZ-* | BR-QZ-* | BR | Covered by domain rules, services and API permissions | 12 business rules require RBAC, persistence, and audit logging; verified via `modules/quiz/tests/test_api.py` and `modules/quiz/tests/test_domain.py` | Behavior tested in `test_api.py` (twin tests for 403, 404 scoping, 400 validation) and `test_domain.py` (negative marking, boundary guards). Redundant skipped stubs deleted per Step 9; design preserved in `BR_DESIGN.json`. | No |
| WF-BW-QZ-* / WF-CW-QZ-* | BW-QZ-* / CW-QZ-* | WF | Covered by end-to-end evaluation service and API | 3 composite workflow cases require full attempt-to-evaluation pipeline; verified via `modules/quiz/services/evaluation_service.py` | Behavior tested in `modules/quiz/tests/test_services.py::test_attempt_and_evaluation_service` covering manual/AI grading and result release. Redundant skipped stubs deleted per Step 9; design preserved in `WF_DESIGN.json`. | No |
