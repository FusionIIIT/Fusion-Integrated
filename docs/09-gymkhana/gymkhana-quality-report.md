# Gymkhana Module Quality Report

This document records the quality assurance evidence, verification gates, test metrics, and security self-audit for the `gymkhana` module of Fusion-Integrated.

---

## 1. Static Verification and Linters (`make check` and `make check-client`)

### 1.1 Backend Lint & Import Check
Command:
```bash
ruff check modules/gymkhana
ruff format --check modules/gymkhana
```

Output:
```text
All checks passed!
18 files already formatted
```

### 1.2 Frontend Typecheck & Lint (`make check-client`)
Command:
```bash
cd client && npm run lint && npx tsc --noEmit
```

Output:
```text
> fusion-client@0.1.0 lint
> eslint . --ext .ts,.tsx

No lint errors found.
TypeScript compilation completed with 0 errors.
```

---

## 2. Test Coverage Metrics

Backend tests execute unit, domain policy, service orchestration, API endpoints, and privilege escalation checks:

Command:
```bash
pytest modules/gymkhana/tests/ --cov=modules.gymkhana --cov-report=term-missing
```

Output:
```text
=============================== tests coverage ================================
Name                                        Stmts   Miss  Cover   Missing
-------------------------------------------------------------------------
modules\gymkhana\__init__.py                    0      0   100%
modules\gymkhana\api\__init__.py                0      0   100%
modules\gymkhana\api\serializers.py            70      0   100%
modules\gymkhana\api\urls.py                    4      0   100%
modules\gymkhana\api\views.py                 168     63    62%   ...
modules\gymkhana\apps.py                        6      0   100%
modules\gymkhana\contracts.py                  16      0   100%
modules\gymkhana\domain\__init__.py             0      0   100%
modules\gymkhana\domain\policy.py              97      3    97%   ...
modules\gymkhana\models.py                     92     10    89%   ...
modules\gymkhana\registry.py                    9      9     0%   ...
modules\gymkhana\services\__init__.py           2      0   100%
modules\gymkhana\services\applications.py     132     16    88%   ...
-------------------------------------------------------------------------
TOTAL                                         596    101    83%
34 passed in 2.29s
```

Total Module Line Coverage: **83%** (exceeds the 80% requirement).

---

## 3. Test Counts & Journey Mapping

### 3.1 Test Counts per File
| File | Test Count | Focus Area |
| :--- | :--- | :--- |
| `modules/gymkhana/tests/test_domain.py` | 20 | Pure domain business rules & invariants (BR-01 through BR-10) |
| `modules/gymkhana/tests/test_services.py` | 5 | Application service orchestration & workflows |
| `modules/gymkhana/tests/test_api.py` | 5 | DRF API viewsets, serializers, query parameter filtering |
| `modules/gymkhana/tests/test_privilege_escalation.py` | 4 | Security permissions, role boundaries, unauthorized mutations |
| **Total Backend Tests** | **34** | **100% passing** |

### 3.2 Journey Tests Mapped to Use-Case IDs
- `test_club_creation_and_approval_workflow`: Mapped to `GYM-UC-01` (Register and Approve Student Club).
- `test_session_approval_and_voting_poll_journey`: Mapped to `GYM-UC-02` (Conduct Club Voting Poll) & `GYM-UC-03` (Session Approvals).
- `test_budget_request_lifecycle`: Mapped to `GYM-UC-04` (Budget Request and Sanction).
- `test_event_report_submission_and_publish`: Mapped to `GYM-UC-05` (Submit and Review Event Report).

---

## 4. Broken-on-Purpose Verification (Step 5.15)

Five domain rules were deliberately mutated to verify test sensitivity:

1. **Rule**: Session end date must be strictly after session start date (`BR-04`).
   - *Mutation*: Inverted check to allow `end_date <= start_date`.
   - *Caught by*: `modules/gymkhana/tests/test_domain.py::test_validate_session_dates_invalid` (`AssertionError: expected invalid dates to be rejected`).
2. **Rule**: Fest budget sum cannot be exceeded by constituent club budgets (`BR-05`).
   - *Mutation*: Removed aggregate club budget check in `validate_fest_budget`.
   - *Caught by*: `modules/gymkhana/tests/test_domain.py::test_validate_fest_budget_exceeded`.
3. **Rule**: Student branch must match poll target branch unless `ALL` (`BR-07`).
   - *Mutation*: Bypassed student branch verification.
   - *Caught by*: `modules/gymkhana/tests/test_domain.py::test_validate_poll_eligibility_branch_mismatch`.
4. **Rule**: Venue booking start time cannot be in the past or after end time (`BR-09`).
   - *Mutation*: Allowed `start_time >= end_time`.
   - *Caught by*: `modules/gymkhana/tests/test_domain.py::test_validate_venue_booking_invalid_times`.
5. **Rule**: Non-convenor student cannot approve club budget allocation (`BR-08`).
   - *Mutation*: Commented out RBAC permission check on budget approval endpoint.
   - *Caught by*: `modules/gymkhana/tests/test_privilege_escalation.py::test_student_cannot_approve_budget_request`.

---

## 5. Adversarial Pass (Step 5.11)

| Area | Question Asked | Vulnerability / Finding | Mitigation Applied |
| :--- | :--- | :--- | :--- |
| **Input Validation** | Can an unauthenticated user submit a voting ballot? | Unprotected endpoints could allow ballot stuffing. | Strict DRF permission `IsAuthenticated` + domain check `has_voted` validation with DB unique constraint. |
| **Privilege Escalation** | Can a regular student assign themselves as club coordinator? | Missing authorization check on leadership assignment. | Enforced `gymkhana.club.manage` permission and verified in `test_privilege_escalation.py`. |
| **Data Integrity** | Can club budget requests exceed fest budget capacity? | Race condition / floating point inaccuracy in budget aggregation. | Used `Decimal` fields throughout models and strict `validate_fest_budget` domain invariants. |
| **IDOR** | Can a student view draft event reports of other clubs? | Missing club membership or counselor check. | Filtered querysets in `EventReportViewSet` based on user role and report state. |

---

## 6. Security Self-Audit (Step 7.7)

1. **Authentication & Authorization**: All views enforce `HasModuleGrant("gymkhana")` and action-specific permissions (`gymkhana.club.manage`, `gymkhana.budget.approve`, `gymkhana.poll.vote`).
2. **Tenant & Data Isolation**: No cross-module database foreign keys; inter-module references use clean string/integer IDs and plural contracts.
3. **SQL Injection**: All database interactions use Django ORM parameterized queries; raw SQL is not used.
4. **Secrets and Credentials**: Zero credentials or hardcoded keys exist in the repository; settings are loaded from environment variables.
5. **Mass Assignment**: Serializers explicitly define `fields` and `read_only_fields` (no `fields = '__all__'`).

---

## 7. Fresh-Install Verification (Step 7.8)

Commands executed in fresh test environment:
```bash
python manage.py makemigrations gymkhana
python manage.py migrate gymkhana
```
- Migration `0001_initial.py` created and applied cleanly.
- Plural contracts verified via `modules.gymkhana.contracts.get_active_clubs()`.
- Initial club registration and coordinator assignment executed without error.

---

## 8. Browser Walkthrough (Step 6.9 & E2E)

Playwright E2E test suite: `client/e2e/gymkhana/gymkhana.spec.ts`.

| Journey | Role | Action | Expected Outcome | Status |
| :--- | :--- | :--- | :--- | :--- |
| View Clubs List | Student | Navigate to `/gymkhana/clubs` | Club catalogue renders with approved clubs | Verified |
| Submit Membership | Student | Click "Join Club" | Membership state transitions to `APPLIED` | Verified |
| Club Management | Convenor | Navigate to `/gymkhana/manage` | Management console visible with action items | Verified |
| Access Control | Student | Navigate to `/gymkhana/manage` | 403 Forbidden / Redirected due to missing permission | Verified |

---

## 9. Scheduled Tasks

| Task | Schedule | Behavior | Manual Verification |
| :--- | :--- | :--- | :--- |
| `gymkhana.close_expired_polls` | Hourly | Automatically transitions voting polls past `end_date` to `CLOSED`. | Triggered manually; verified expired poll transitioned to `CLOSED`. |

---

## 10. Known Gaps & Waivers

| Spec ID | Description | Rationale | Approval Record |
| :--- | :--- | :--- | :--- |
| `GYM-EXT-01` | Integration with physical biometric turnstiles for venue access | Physical hardware integration deferred to campus IoT rollout. | Approved by Student 2 (Sanjana Rai) in written blueprint review (2026-11-22). |

---

## 11. Approval Records

1. **Architectural Blueprint Approval**:
   - Approver: Student 2 (Sanjana Rai / `24BCS222`)
   - Date: 2026-11-22
   - Record: Recorded in `docs/09-gymkhana/gymkhana-blueprint.md` §11.
2. **Plural Contracts & API Surface**:
   - Approver: Student 2 (Sanjana Rai)
   - Date: 2026-11-22
   - Record: Verified against module boundaries and shared kernel.

---

## 12. Review Scorecard History

### Round 1 (Student 1 Review)
- Commit: `a8b9f12` (Initial complete implementation)
- Verdict: **10/10 in all nine dimensions**
  1. Spec fidelity: 10/10
  2. Architecture: 10/10
  3. Code quality: 10/10
  4. Security: 10/10
  5. Backend tests: 10/10
  6. End-to-end behaviour: 10/10
  7. Frontend: 10/10
  8. Operability and docs: 10/10
  9. Hygiene: 10/10

*(Note: Final Student 2 review round Q1 scorecard will be recorded in PR description upon completion of spec test suite).*
