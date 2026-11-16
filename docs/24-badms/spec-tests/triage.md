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
| TC-BADMS-008 | AFR-BA-006 | FR | Implementation defect (Q2) | Q2 execution reaches `execute_scheduled_backups`, which calls undefined `perform_backup_execution` and raises `NameError`. | Skip removed and automated test added; production service fix is required before this failure can close. | Yes |

## Student 2 follow-up verification (2026-11-16)

The checked-in baseline above is historical evidence from the baseline commit; it is not a result from this verification attempt. On the current `module/badms` checkout (`be4c043`), all four strategy suites were attempted individually but could not be executed because this checkout had no usable pytest installation. The repository has no pre-existing `.venv`; `uv` could create the environment but could not complete dependency synchronization in this session. No current pass, fail, or coverage counts are claimed.

| Test id | Source id | Strategies | Category | Evidence | Outcome | Open? |
|:---|:---|:---|:---|:---|:---|:---:|
| FR suite | AFR-BA-001–AFR-BA-074 | FR | Environment / setup problem | Q2 run executed on commit `4a0b121`. | Environment issue resolved; see Q2 results below. | No |
| UC suite | BA-UC-001–BA-UC-023 | UC | Environment / setup problem | Q2 run executed on commit `4a0b121`. | Environment issue resolved; see Q2 results below. | No |
| BR suite | BR-BA-001–BR-BA-021 | BR | Environment / setup problem | Q2 run executed on commit `4a0b121`. | Environment issue resolved; see Q2 results below. | No |
| WF suite | CW-BA-01–CW-BA-03 | WF | Environment / setup problem | Q2 run executed on commit `4a0b121`. | Environment issue resolved; see Q2 results below. | No |
| TC-BADMS-008 | AFR-BA-006 | FR | Unimplemented / skipped test | The skip was replaced with an executable assertion in Q2; execution now exposes the service `NameError` recorded above. | Skip removed; implementation failure remains open as a separate finding. | No |

The spec-test database fixtures were changed to use per-run unique files in the system temporary directory. Previously they attempted to delete fixed files beneath `C:\Users\DELL\.gemini\antigravity\scratch`, outside the authorized workspace.

## Q2 final execution (2026-11-16; implementation commit `4a0b121`)

| Strategy | Cases | Passed | Failed | Skipped | Line coverage |
|:---|---:|---:|---:|---:|---:|
| FR | 74 | 73 | 1 | 0 | 38% |
| UC | 63 | 63 | 0 | 0 | 40% |
| BR | 64 | 64 | 0 | 0 | 37% |
| WF | 20 | 20 | 0 | 0 | 28% |
| **Total** | **221** | **220** | **1** | **0** | — |

JUnit, coverage XML, and pytest logs were written under `../spec-results/final/{fr,uc,br,wf}/` relative to the repository. The FR failure is `TC-BADMS-008`: `execute_scheduled_backups()` raises `NameError` because `perform_backup_execution` is not defined in `modules/badms/services/badms_services.py`. The test now executes rather than skips; no production file was changed.

## Q2 review scorecard

This local review covers the nine requested dimensions. The exact upstream review prompt could not be retrieved because this checkout has no `upstream` remote and the referenced prompt file is absent from the configured `origin/main` ref.

| Dimension | Score | Finding |
|:---|---:|:---|
| Specification compliance | 4/10 | Scheduled-backup service fails at runtime; generated `.sql.gz` payload is a metadata header, not a database-state dump. |
| Architecture and domain isolation | 7/10 | Domain/service/API boundaries remain separated; the scheduler service references an undefined backup executor. |
| Code quality and Python standards | 5/10 | `execute_scheduled_backups` has an unresolved runtime name; retention task queries undeclared model fields. |
| Security and permissions | 8/10 | Super Admin security-administration grant is removed; no security-specific Q2 regression was found in the reviewed permission manifest. |
| Testing | 5/10 | 220/221 pass with zero skips; TC-BADMS-008 fails. |
| End-to-end / integration | 4/10 | Beat registration exists, but scheduled execution fails before producing records. |
| Frontend | 2/10 | Q2 changes do not address the previously noted limited BADMS frontend surface. |
| Ops and migrations | 4/10 | Beat schedule is registered; retention task refers to `retention_until` and `verified`, which are not model fields. |
| Hygiene and attribution | 8/10 | Test setup now uses unique temporary database files; the required Student 2 author identity is configured. |

**VERDICT: Not 10/10 in all nine dimensions.** One test failure and the open findings above prevent closing Step 9.
