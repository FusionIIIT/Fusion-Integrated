# Placement Cell Management System (PCMS) — Quality Report
**Module:** Placement Cell (`modules/placement`) | **Docs Folder:** `docs/04-placement/`  
**Author (Student 1):** Rohan (`24BCS060`) | **Reviewer (Student 2):** rohankuthuru27-hub (`24BCS135`)  
**Base Commit / Hash:** `108c9e5a456f796bdcd1b71ab6226a9a3c5f3ace`  
**Review Verdict:** 10/10 in all nine dimensions  

---

## 1. Quality Gates Summary

| Gate | Tool / Command | Target / Standard | Result | Evidence |
| :--- | :--- | :--- | :---: | :--- |
| **Backend Lint / Code Quality** | `ruff check modules/placement` | 0 errors | **PASS** | Clean run, 0 violations |
| **Backend Unit / Integration Tests** | `pytest modules/placement/tests` | All tests pass | **PASS** | 328/328 passing |
| **Code Coverage (Statement)** | `pytest-cov --cov=modules.placement` | > 85.0% | **PASS** | 88.42% line coverage |
| **Code Coverage (Branch)** | `pytest-cov --cov-branch` | High branch coverage | **PASS** | 76.85% branch coverage |
| **Database Migrations** | `manage.py makemigrations --check` | 0 unapplied / clean | **PASS** | Clean migration tree (0001–0010) |
| **Schema & Manifest Synchronization**| `make schema && make permissions` | Up-to-date yaml & json | **PASS** | Matches OpenAPI v1 & permissions |
| **Frontend Type Checking** | `npm run build / tsc` | 0 type errors, no `any` | **PASS** | TypeScript clean build |
| **Frontend Component Tests** | `npm test client/src/modules/placement`| All component tests pass | **PASS** | Clean vitest run |
| **Route Guards Verification** | `test_client_route_guards.py` | Route permissions enforced | **PASS** | All guarded routes verified |

---

## 2. Specification Traceability & Obligation Audit

| Specification Document | Obligations Required | Implemented & Tested | Status |
| :--- | :---: | :---: | :---: |
| **Functional Requirements (CFR / AFR)** | 64 AFRs | 64 / 64 | **100% Covered** |
| **Use Cases (UC)** | 22 Active UCs | 22 / 22 | **100% Covered** |
| **Business Rules (BR)** | 26 Active BRs | 26 / 26 | **100% Covered** |
| **Workflows (WF)** | 12 (8 Basis + 4 Composite) | 12 / 12 | **100% Covered** |

Every live specification ID is cited directly in the code at its primary validation or enforcement point (e.g. `PC-BR-003`, `PC-UC-006`, `BW-PC-01`). Zero retired IDs cited.

---

## 3. Security & Adversarial Verification

- **Role-Based Access Control:** Verified least-privilege matrix in `registry.py`. Student accounts are strictly barred from coordinator and officer endpoints.
- **Tenant & Recruiter Isolation:** Verified in `test_recruiter_isolation.py`. Recruiters from Company A cannot query or view applications or candidate profiles from Company B.
- **Privilege Escalation:** Verified in `test_privilege_escalation.py`. Direct ID manipulation on applicant IDs or offer response IDs returns HTTP 403 Forbidden.
- **Data Protection:** No student contact information or GPA/academic data is leaked to unauthorized roles.

---

## 4. Background Scheduled Tasks & Celery

| Task Name | Schedule | Purpose | Manual Run Verified? |
| :--- | :--- | :--- | :---: |
| `placement.expire_stale_postings` | Hourly (`0 * * * *`) | Moves expired postings to `closed` | **Yes** |
| `placement.process_offer_deadlines`| Daily (`0 0 * * *`) | Expires unanswered job offers | **Yes** |
| `placement.dispatch_outbox_events` | Every 5 mins | Flushes transactional outbox to bus | **Yes** |

---

## 5. Approvals, Decisions & Waivers

1. **Blueprint Approval:** Approved by Student 2 (`rohankuthuru27-hub <24bcs135@iiitdmj.ac.in>`) on 2026-11-16.
2. **Architecture Decisions:** Strict adherence to ADR 0013 (No cross-module FKs). Identity references managed via plain `user_id` integer references.
3. **Waivers:** None requested. Zero open blockers or exceptions.

---

## 6. Review Scorecard History

### Student 1 Review Rounds

```
========================================================================================
Round | Spec | Arch | Code | Security | Tests | E2E | Frontend | Ops | Hygiene | Verdict
========================================================================================
1     |  9   |  9   |  9   |    9     |   9   |  9  |    9     |  9  |   10    | Not yet (R1-01..03)
2     | 10   | 10   | 10   |   10     |  10   | 10  |   10     | 10  |   10    | 10/10 in all 9
========================================================================================
```

### Student 2 Spec-Test & Independent Review Rounds

```
========================================================================================
Round | Spec | Arch | Code | Security | Tests | E2E | Frontend | Ops | Hygiene | Verdict
========================================================================================
Q1    |  9   | 10   |  9   |   10     |   9   | 10  |   10     | 10  |   10    | Not yet (baseline triage findings)
Q2    |  9   | 10   | 10   |   10     |   9   | 10  |   10     | 10  |   10    | Not yet (WF passing, FR/UC/BR fixing)
Q3    |  9   | 10   | 10   |   10     |   9   | 10  |   10     | 10  |   10    | Not yet (UC/BR/WF passing, FR 5 open)
Q4    | 10   | 10   | 10   |   10     |  10   | 10  |   10     | 10  |   10    | 10/10 in all 9 (0 failures, 0 skips)
========================================================================================
```

### Spec Tests Execution Summary (Student 2)

| Strategy | Total Tests | Passed | Failed | Skipped | Line Coverage | Branch Coverage |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Functional Requirements (FR)** | 65 | 65 | 0 | 0 | 50.53% | 3.73% |
| **Use Cases (UC)** | 66 | 66 | 0 | 0 | 50.80% | 4.35% |
| **Business Rules (BR)** | 76 | 76 | 0 | 0 | 50.70% | 4.35% |
| **Workflows (WF)** | 18 | 18 | 0 | 0 | 48.74% | 1.62% |
| **Total** | **225** | **225** | **0** | **0** | — | — |
