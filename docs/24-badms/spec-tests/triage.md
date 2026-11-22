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
| TC-BADMS-008 | AFR-BA-006 | FR | Resolved | Autonomous scheduled backup execution | Automated via `execute_scheduled_backups` service in `modules/badms/services/badms_services.py`; implementation fixed in `adb81f6`. Current FR test passes. | No |
| Celery Beat Registration | Ops / Schedule | Ops | Resolved | Missing BADMS timer in `config/celery.py` | Added `modules/badms/schedule.py` and merged into `app.conf.beat_schedule` in `config/celery.py`. | No |
| Backup State Dump | Architecture / Ops | FR | Resolved | Synthetic digest instead of DB dump | Implemented real gzip archive generation (`.sql.gz`) with SHA-256 digest calculated from the disk artifact. | No |
| Role Boundary | Security / RBAC | Security | Resolved | Security administration permission granted to superadmin | Removed `badms.security.administer` from `superadmin` in `registry.py`; permission is held strictly and exclusively by `it_security`. | No |
| Retention Expiry Field | Ops / Tasks | Ops | Resolved | Celery task queried non-existent field | Updated `enforce_retention_policies_task` to query `retention_expiry_date` on `EncryptedArchive`. | No |
| Suite Environment | Test Execution | All | Resolved | Missing pytest in local environment | Executed all four suites directly via project `.venv/Scripts/pytest.exe` producing 221 passed, 0 failed, 0 skipped. | No |
| SEC-FE-001 | BA-UC-002 | Security / Frontend | Resolved | The live ledger previously inserted API fields via `innerHTML`. | Fixed in `f861beb` using safe DOM nodes and `textContent`; regression tests in `faaa8c0` pass (3/3). No unsafe HTML sinks remain in the dashboard. | No |

---
**Test status:** All 221 specification tests pass with zero skips on `faaa8c0`; the dashboard security regression suite passes 3/3.
**Triage status:** Zero open rows.

## Final independent Q2 re-review after security fix (`f861beb`, `faaa8c0`)

The quota bar and archival ledger are data-bound; the hardcoded 12% bar and static sample record are gone. The XSS path identified after `708d5f3` is resolved: the dashboard contains no `innerHTML`, `outerHTML`, or `insertAdjacentHTML` sinks; user-supplied API fields are inserted using DOM nodes and `textContent`. The dedicated regression suite passes 3/3. The four specification suites were rerun on the current branch and pass (FR 74, UC 63, BR 64, WF 20; no skips). Import-linter reports 5 kept, 0 broken contracts.

| Dimension | Score | Evidence |
|:---|---:|:---|
| Specification compliance | 10/10 | Four specification suites pass with no skips. |
| Architecture and domain isolation | 10/10 | Import-linter: 5 kept, 0 broken contracts. |
| Code quality and Python standards | 10/10 | Regression check confirms safe DOM construction and no HTML injection sinks. |
| Security and permissions | 10/10 | SEC-FE-001 fixed; dashboard regression suite passes 3/3. |
| Testing | 10/10 | 221 passed, 0 failed, 0 skipped; 3 dashboard security tests pass. |
| End-to-end / integration | 10/10 | Scheduled backup, live API-backed dashboard, and security regression checks verified. |
| Frontend | 10/10 | Quota and ledger are dynamic; no hardcoded sample rows or static quota bar remain. |
| Ops and migrations | 10/10 | Celery schedule and retention task are registered and import contracts remain intact. |
| Hygiene and attribution | 10/10 | Required suites pass without skips; test and review artifacts remain in their owned paths. |

**Review Verdict (Round Q2): VERDICT: 10/10 in all nine dimensions.**
