# Spec tests: badms

Student 1 (git author name): Adepu Srinidh
Student 2 (git author name): Ansh Prajapati
Design commit (hash and subject): 4305130 test(badms): freeze specification test designs for FR, UC, BR, WF
Baseline commit (hash and subject): 86a1f09 test(badms): add executable spec tests and baseline triage log
Student 1's 10/10 commit the baseline ran on (hash): 95856b3

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| baseline | FR | 74 | 73 | 0 | 1 | 48.43% | 42.96% |
| baseline | UC | 63 | 63 | 0 | 0 | 51.87% | 51.41% |
| baseline | BR | 64 | 64 | 0 | 0 | 48.62% | 47.18% |
| baseline | WF | 20 | 20 | 0 | 0 | 43.21% | 29.58% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|:---|:---|:---|:---|:---|:---|:---:|
| TC-BADMS-008 | AFR-08 | FR | Environment / setup problem | External background daemon execution requires separate system process | Handled via Celery beat scheduler in platform configuration | No |

## Student 2 follow-up verification (2026-11-16)

The checked-in baseline above is historical evidence from the baseline commit; it is not a result from this verification attempt. On the current `module/badms` checkout (`be4c043`), all four strategy suites were attempted individually but could not be executed because this checkout had no usable pytest installation. The repository has no pre-existing `.venv`; `uv` could create the environment but could not complete dependency synchronization in this session. No current pass, fail, or coverage counts are claimed.

| Test id | Source id | Strategies | Category | Evidence | Outcome | Open? |
|:---|:---|:---|:---|:---|:---|:---:|
| FR suite | AFR-BA-001–AFR-BA-074 | FR | Environment / setup problem | `pytest` is absent from `.venv`; dependency installation did not complete, so the suite could not be collected or run. | Requires an environment with project dev dependencies installed; no test result inferred. | Yes |
| UC suite | BA-UC-001–BA-UC-023 | UC | Environment / setup problem | `pytest` is absent from `.venv`; dependency installation did not complete, so the suite could not be collected or run. | Requires an environment with project dev dependencies installed; no test result inferred. | Yes |
| BR suite | BR-BA-001–BR-BA-021 | BR | Environment / setup problem | `pytest` is absent from `.venv`; dependency installation did not complete, so the suite could not be collected or run. | Requires an environment with project dev dependencies installed; no test result inferred. | Yes |
| WF suite | CW-BA-01–CW-BA-03 | WF | Environment / setup problem | `pytest` is absent from `.venv`; dependency installation did not complete, so the suite could not be collected or run. | Requires an environment with project dev dependencies installed; no test result inferred. | Yes |
| TC-BADMS-008 | AFR-BA-006 | FR | Unimplemented / skipped test | The test body calls `pytest.skip`; the historical entry above marks this handled by platform Celery configuration, but no executed test verifies scheduled BADMS backup execution. | Still skipped; Step 9's no-skip requirement is not met. | Yes |

The spec-test database fixtures were also changed to use per-run unique files in the system temporary directory. Previously they attempted to delete fixed files beneath `C:\Users\DELL\.gemini\antigravity\scratch`, outside the authorized workspace. The suites must be rerun after installing dependencies to establish executable results.
