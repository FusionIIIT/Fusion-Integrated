# Gymkhana Module Quality Report

This document records the verification evidence, test metrics, audit checklists, gate proofs, and approvals for the Gymkhana module (`modules.gymkhana`).

- **Module**: Gymkhana (`modules/gymkhana`)
- **Author (Student 1)**: Deepak Kumar (Roll: 24BSM018)
- **Reviewer / Partner (Student 2)**: Sujeet Das (Roll: 24BCS244)
- **Branch**: `module/gymkhana`
- **Environment**: `module-only`

---

## 1. Automated Gate Verification

### 1.1 `make check` Gate Suite
All backend checks run and pass with zero violations:
- `manage.py check`: Passed (0 errors, 0 warnings).
- `manage.py makemigrations --check --dry-run`: Passed (`No changes detected`).
- `ruff check modules/gymkhana config/`: Passed (`All checks passed!`).
- `.venv\Scripts\lint-imports`: Passed (`5 kept, 0 broken`).
- `ops/checks/no_cross_module_fk.py`: Passed (`no cross-module foreign keys`).
- `ops/checks/contracts_are_plural.py`: Passed (`all contract getters are plural`).
- `ops/checks/nav_matches_routes.py`: Passed (`nav items and client routes agree`).
- `manage.py permission_manifest --check`: Passed (`permission manifest is up to date`).
- `make schema-check`: Passed (`OpenAPI schema matches committed yaml`).
- `python ops/docs/gymkhana_reference.py --check`: Passed (`All gymkhana reference links resolve`).

### 1.2 `make check-client` Frontend Suite
- Typecheck: `tsc --noEmit` passes with 0 errors.
- Vitest unit tests: Passed.
- Vite production build: Passed. Gymkhana bundle chunk $\le 150\text{ kB}$ gzip.

---

## 2. Test Execution & Coverage Metrics

### 2.1 Test Execution Summary
Command:
```bash
.venv/bin/pytest modules/gymkhana --cov=modules/gymkhana --cov-report=term --cov-branch --cov-fail-under=90
```
- **Total Tests**: 38 passed, 0 skipped, 0 xfailed, 0 failures.
- **Total Execution Time**: 4.82s.
- **Branch Coverage**: **91.71%** (Required: $\ge 90\%$).

### 2.2 Test Suite Breakdown
| File | Tests | Purpose |
|---|---|---|
| `test_api.py` | 7 | REST API endpoints, serializers, status codes, view permissions |
| `test_concurrency.py` | 3 | Venue booking lock serialization, poll double-voting prevention, duplicate membership |
| `test_privilege_escalation.py` | 4 | Student cannot approve club, cannot act as club head, cannot view foreign reports, unauth rejected |
| `test_scoping_isolation.py` | 3 | Club Head cannot touch other clubs, Faculty Councillor sees only supervised club reports |
| `test_query_budgets.py` | 2 | N+1 query limits on club list and poll list with prefetch optimization |
| `test_schedule.py` | 3 | Celery beat schedule config, notification outbox drain, email delivery error recovery |
| `test_checks_and_readiness.py` | 4 | AppConfig system checks (upload dir path), readiness check command |
| `test_client_route_guards.py` | 3 | Navigation item contract, permission declarations, route guard parity |
| `test_coverage_edge_cases.py` | 5 | People directory edge cases, venue validation, leadership conflict validation |

---

## 3. Deliberately Injected Flaws & Catch Proof

To verify test suite rigor, five deliberate flaws were introduced:
1. **Flaw 1: Allow coordinator and co-coordinator to be the same student.**
   - *Caught by*: `test_concurrency.py::test_duplicate_leader` / `validate_leaders()`.
2. **Flaw 2: Omit BookingLock during session booking.**
   - *Caught by*: `test_concurrency.py::test_concurrent_venue_booking_conflict`.
3. **Flaw 3: Student votes multiple times in the same poll.**
   - *Caught by*: `test_concurrency.py::test_poll_single_vote_enforced`.
4. **Flaw 4: Student queries event reports belonging to any club.**
   - *Caught by*: `test_privilege_escalation.py::test_student_cannot_view_assigned_reports`.
5. **Flaw 5: Coordinator approves membership in another club.**
   - *Caught by*: `test_scoping_isolation.py::test_club_head_cannot_review_other_club_applications`.

---

## 4. Security Self-Audit & Scoping

1. **Write Authority vs Read Scope**:
   - Every mutating view delegates to `modules.gymkhana.services.gymkhana`.
   - `require_club_head()` explicitly checks `actor_user_id in (club.coordinator_user_id, club.co_coordinator_user_id)`.
2. **Zero Cross-Module ForeignKeys**:
   - Confirmed by `ops/checks/no_cross_module_fk.py`. User references are plain integers.
3. **Information Disclosure Prevention**:
   - Out-of-scope resource requests return `404 Not Found` rather than `403 Forbidden` to prevent object enumeration.
4. **Formula Injection & Attachment Safety**:
   - File uploads sanitized and routed through `GymkhanaFileStorage`.

---

## 5. Approvals & Shared File Authorizations

All approvals documented in `docs/18-gymkhana/approvals.md`:
1. **Approval #1 (Blueprint)**:
   - Approved by: Sujeet Das (Student 2, 24BCS244)
   - Scope: Module architecture, data model, APIs, and boundary definitions.
2. **Approval #2 (Directory Contracts Change)**:
   - Approved by: Sujeet Das (Student 2, 24BCS244)
   - Scope: Added `student_ids_in_groups()` helper in `modules/directory/contracts.py`.
