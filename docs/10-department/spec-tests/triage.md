# Spec tests: department

Student 1 (git author name): Siddharth-Ilayaraja24
Student 2 (git author name): Shubham Kulkarni
Design commit (hash and subject): c7f7bf4 Department spec tests: freeze the FR, UC, BR and WF designs
Baseline commit (hash and subject): the commit that adds this file, "Department spec tests: add the FR, UC, BR and WF suites at baseline" (hash recorded in the next update)
Student 1's 10/10 commit the baseline ran on (hash): 34b8ab5

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 89 | 88 | 0 | 1 | 86.5 | 61.4 |
| baseline | UC | 44 | 43 | 0 | 1 | 86.2 | 61.8 |
| baseline | BR | 45 | 44 | 0 | 1 | 84.7 | 57.7 |
| baseline | WF | 22 | 22 | 0 | 0 | 73.8 | 34.6 |

Repair prompts used: 0 for every strategy. Coverage is of `modules/department`, measured per
strategy with `--cov-branch`.

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| TC-DEPT-056 (FR), TC-DEPT-029 (UC), TC-DEPT-BR-037 (BR) | AFR-DEPT-026; UC-DEPT-015; BR-DEPT-019 | FR, UC, BR | Unresolved | All three are skipped `NOT_AUTOMATED`: no interface links a Faculty member to the Students in their courses. The IAM's `main` has no course-roster endpoint (blueprint Q2). Spec: "The system shall allow Faculty to view detailed profile information for Students in the Faculty member's courses." | To be sorted at step 6. | yes |
