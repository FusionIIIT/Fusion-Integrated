# Spec tests: pms

Student 1 (git author name): RajivSarma7 (user-certified 10/10 review)
Student 2 (git author name): RajivSarma7
Design commit (hash and subject): 34049e2 Add frozen PMS test designs (pre-squash design-freeze commit)
Baseline commit (hash and subject): Not separately labeled; Q18 is the final full run
Student 1's 10/10 commit the baseline ran on (hash): 56c6c8b Implement PMS patent management module (user-certified; Q18 used this implementation)

The frozen designs are unchanged. Q18 is the latest full run; its pytest, JUnit, and coverage files are in `../spec-results/Q18/<strategy>/`.

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| Q18 | FR | 203 | 200 | 0 | 3 | 73.45 | 52.33 |
| Q18 | UC | 107 | 107 | 0 | 0 | 61.04 | 33.02 |
| Q18 | BR | 84 | 84 | 0 | 0 | 58.36 | 32.56 |
| Q18 | WF | 21 | 21 | 0 | 0 | 53.72 | 22.33 |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| FR-214 | PMS-AFR-214 | FR | Environment / setup | The frozen requirement concerns encryption at rest at the platform boundary; the isolated PMS database test environment exposes no underlying storage-encryption control. | Requires validation in the deployed database/storage environment. | Yes |
| FR-215 | PMS-AFR-215 | FR | Environment / setup | The frozen requirement concerns encryption in transit at the platform boundary; the Django API test client does not traverse the deployed TLS termination boundary. | Requires validation in the deployed API/database TLS environment. | Yes |
| FR-227 | PMS-AFR-227 | FR | Specification ambiguity | The frozen design identifies no concrete parallel process or callable process-level interface to exercise. | Needs an agreed interpretation or a specified process interface before an observable test can be written. | Yes |

No test failures remain. The three rows above remain open, so the all-pass assignment gate is not met. The independent cross-provider review and its nine-dimension 10/10 score are also not recorded.
