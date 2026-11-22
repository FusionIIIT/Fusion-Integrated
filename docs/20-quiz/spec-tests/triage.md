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

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| FR-AFR-QZ-* | AFR-QZ-* | FR | Unresolved coverage | 54 design cases require unavailable UI/API/persistence/proctoring or orchestration interfaces in the frozen baseline | Marked `NOT_AUTOMATED` with explicit interface reasons; no expected results or test cases changed | Yes |
| UC-UC-QZ-* | UC-QZ-* | UC | Unresolved coverage | 11 use-case flows require unavailable service/API/UI/persistence interfaces | Marked `NOT_AUTOMATED` with explicit interface reasons; no expected results or test cases changed | Yes |
| BR-BR-QZ-* | BR-QZ-* | BR | Unresolved coverage | 12 business-rule cases require unavailable UI/API/persistence/audit/notification interfaces | Marked `NOT_AUTOMATED` with explicit interface reasons; no expected results or test cases changed | Yes |
| WF-BW-QZ-* / WF-CW-QZ-* | BW-QZ-* / CW-QZ-* | WF | Unresolved coverage | 3 composite workflow cases require unavailable evaluation or orchestration interfaces | Marked `NOT_AUTOMATED` with explicit interface reasons; no expected results or test cases changed | Yes |

