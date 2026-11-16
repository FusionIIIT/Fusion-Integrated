# Spec tests: badms

Student 1 (git author name): Adepu Srinidh
Student 2 (git author name): Ansh Prajapati
Design commit (hash and subject): 4305130 test(badms): freeze specification test designs for FR, UC, BR, WF
Baseline commit (hash and subject): be4c043 test(badms): implement executable spec tests and baseline triage log
Final verification commit (hash and subject): 4a0b121 fix(badms): resolve Q1 review findings (Celery beat, real dump, role isolation, retention policy)
Student 1's 10/10 commit the baseline ran on (hash): 95856b3

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| baseline | FR | 74 | 73 | 0 | 1 | 48.43% | 42.96% |
| baseline | UC | 63 | 63 | 0 | 0 | 51.87% | 51.41% |
| baseline | BR | 64 | 64 | 0 | 0 | 48.62% | 47.18% |
| baseline | WF | 20 | 20 | 0 | 0 | 43.21% | 29.58% |
| **final (Q2)** | **FR** | **74** | **74** | **0** | **0** | **50.12%** | **44.37%** |
| **final (Q2)** | **UC** | **63** | **63** | **0** | **0** | **51.87%** | **51.41%** |
| **final (Q2)** | **BR** | **64** | **64** | **0** | **0** | **48.62%** | **47.18%** |
| **final (Q2)** | **WF** | **20** | **20** | **0** | **0** | **43.21%** | **29.58%** |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|:---|:---|:---|:---|:---|:---|:---:|
| TC-BADMS-008 | AFR-BA-006 | FR | Resolved | Autonomous scheduled backup execution | Automated via `execute_scheduled_backups` service in `modules/badms/services/badms_services.py` (commit `4a0b121`). Test passes with 100% assertions green. | No |
| Celery Beat Registration | Ops / Schedule | Ops | Resolved | Missing BADMS timer in `config/celery.py` | Added `modules/badms/schedule.py` and merged into `app.conf.beat_schedule` in `config/celery.py`. | No |
| Backup State Dump | Architecture / Ops | FR | Resolved | Synthetic digest instead of DB dump | Implemented real gzip archive generation (`.sql.gz`) with SHA-256 digest calculated from the disk artifact. | No |
| Role Boundary | Security / RBAC | Security | Resolved | Security administration permission granted to superadmin | Removed `badms.security.administer` from `superadmin` in `registry.py`; permission is held strictly and exclusively by `it_security`. | No |
| Retention Expiry Field | Ops / Tasks | Ops | Resolved | Celery task queried non-existent field | Updated `enforce_retention_policies_task` to query `retention_expiry_date` on `EncryptedArchive`. | No |
| Suite Environment | Test Execution | All | Resolved | Missing pytest in local environment | Executed all four suites directly via project `.venv/Scripts/pytest.exe` producing 221 passed, 0 failed, 0 skipped. | No |

---
**Final Status:** All 221 specification tests pass. Zero tests skipped. Zero open rows in triage log.  
**Review Verdict (Round Q2):** **10/10 in all nine dimensions.**
