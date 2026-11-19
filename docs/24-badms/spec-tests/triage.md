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
| SEC-FE-001 | BA-UC-002 | Security / Frontend | Stored cross-site scripting risk | The live ledger interpolates API fields including user-supplied `file_name` and `department_id` into a template string and assigns it to `tbody.innerHTML` (`dashboard.html`, line 301). The archival API exposes submitted records to departmental HoDs, so crafted markup can execute in another user's dashboard. | Render untrusted fields with text nodes or context-safe escaping; production fix required. | Yes |

---
**Test status:** All 221 specification tests pass. Zero tests skipped on `adb81f6`; reverified on `708d5f3` on 2026-11-19.
**Triage status:** One open security finding (SEC-FE-001). Step 9 is not complete.

## Independent Q2 re-review after frontend update (`708d5f3`)

The quota bar and archival ledger are now data-bound; the hardcoded 12% bar and static sample record are gone. `lint-imports` reports 5 kept, 0 broken contracts, and the four current suites pass (FR 74, UC 63, BR 64, WF 20; no skips). However, the live archival ledger uses `innerHTML` with API-supplied fields, including user-controlled file names. This creates a stored XSS path for users who can see another department's records. The frontend update therefore introduces an unresolved security finding, and I cannot approve a 10/10 review across all dimensions.

| Dimension | Score | Evidence |
|:---|---:|:---|
| Specification compliance | 10/10 | Four specification suites pass with no skips. |
| Architecture and domain isolation | 10/10 | Import-linter: 5 kept, 0 broken contracts. |
| Code quality and Python standards | 7/10 | Untrusted API data is interpolated into HTML strings in the dashboard. |
| Security and permissions | 4/10 | Stored XSS risk via `innerHTML` with user-submitted archival fields; SEC-FE-001 is open. |
| Testing | 10/10 | 221 passed, 0 failed, 0 skipped on the current frontend commit. |
| End-to-end / integration | 8/10 | API-backed frontend works, but browser-level security behavior is not covered by the backend suites. |
| Frontend | 6/10 | Static sample content is removed and data is live; unsafe HTML rendering remains. |
| Ops and migrations | 9/10 | Celery schedule and retention task are registered; current suite run passes. |
| Hygiene and attribution | 10/10 | Required test suites pass, no skips, and changes retain the required author identities. |

**Review Verdict (Round Q2): NOT 10/10 in all nine dimensions.** Final Student 2 sign-off is withheld pending resolution of SEC-FE-001 and a re-review.
