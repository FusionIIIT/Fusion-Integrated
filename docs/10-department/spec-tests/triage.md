# Spec tests: department

Student 1 (git author name): Siddharth-Ilayaraja24
Student 2 (git author name): Shubham Kulkarni
Design commit (hash and subject): c7f7bf4 Department spec tests: freeze the FR, UC, BR and WF designs
Baseline commit (hash and subject): bc152bc Department spec tests: add the FR, UC, BR and WF suites at baseline
Student 1's 10/10 commit the baseline ran on (hash): 34b8ab5

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 89 | 88 | 0 | 1 | 86.5 | 61.4 |
| baseline | UC | 44 | 43 | 0 | 1 | 86.2 | 61.8 |
| baseline | BR | 45 | 44 | 0 | 1 | 84.7 | 57.7 |
| baseline | WF | 22 | 22 | 0 | 0 | 73.8 | 34.6 |
| Q1 | FR | 89 | 89 | 0 | 0 | 86.6 | 62.1 |
| Q1 | UC | 44 | 44 | 0 | 0 | 86.3 | 62.1 |
| Q1 | BR | 45 | 45 | 0 | 0 | 85.0 | 59.6 |
| Q1 | WF | 22 | 22 | 0 | 0 | 73.1 | 33.3 |

Repair prompts used: 0 for every strategy. Coverage is of `modules/department`, measured per
strategy with `--cov-branch`. The baseline ran on `bc152bc`. The Q1 run is on Student 1's Q2
change (`20cfafb`) with the three tests automated: the commit review Q1 reads.

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| TC-DEPT-056 (FR), TC-DEPT-029 (UC), TC-DEPT-BR-037 (BR) | AFR-DEPT-026; UC-DEPT-015; BR-DEPT-019 | FR, UC, BR | Specification ambiguity | All three are skipped `NOT_AUTOMATED`: no interface links a Faculty member to the Students in their courses. The IAM's `main` has no course-roster endpoint (blueprint Q2). Spec: "The system shall allow Faculty to view detailed profile information for Students in the Faculty member's courses." | Agreed reading, 2026-11-24: the spec does not say where a Faculty member's courses come from, and the IAM has no roster. A Student is in a Faculty member's course when the Student's programme and batch year match a timetable slot that Faculty member teaches in the department (blueprint, "Change to Q2"). Student 1 builds the instructor on timetable slots; Student 1 built it in `20cfafb`; Student 2 automated the three tests without changing their expected results, and all three pass in the Q1 run. | no |
