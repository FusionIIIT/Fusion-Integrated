# Phase-2 AI Interaction & Complete Prompt Log: Employee Leave Management (ELM)

**Student Name:** Sumit Kumar  
**Roll Number:** 24BCS245 (Batch B)  
**Course:** Fusion ERP Lab Assignment 6B  
**Target Module:** Employee Leave Management (`modules/elm`)  
**Repository Branch:** `assignment-6-elm`  
**GitHub Fork:** `https://github.com/Sumit-0011/Fusion-Integrated`  
**Base Commit (Phase-1 Preserved):** `30c7079` (`phase-1-elm-original`)  
**Final Commit (Phase-2 Improved):** `89360f7` / `a8a9500`  

---

## 1. Overview & Objectives of Phase 2

Phase 2 takes the initial Phase-1 AI-generated skeleton and advances it through a rigorous human–AI software-engineering workflow:
$$\text{Understand} \longrightarrow \text{Build/Run} \longrightarrow \text{Review} \longrightarrow \text{Test} \longrightarrow \text{Identify Problems} \longrightarrow \text{Improve} \longrightarrow \text{Verify}$$

All engineering actions adhere to platform guidelines:
- **ADR-0013**: No cross-module foreign keys (use integer `user_id`).
- **Fail-Closed Access Control**: Every endpoint guarded by `HasModuleGrant("elm")` and `HasPermission(...)`.
- **Pure Domain Separation**: Domain business rules and state machines isolated from Django ORM models.
- **Section S3 Requirements**: Solving all 30 questions in `docs/questionnaires/S3.xlsx`.

---

## 2. Chronological Interaction & Prompt History

### Stage 1: Understand & Baseline Inspection

#### Prompt 1.1
```text
Inspect the Phase-1 ELM implementation in `modules/elm/`. Determine what functionality has been implemented, how the domain logic and registry are organized, what database models or migrations exist, and which architectural components from the reference module (`modules/placement/`) are currently missing.
```
**Findings:**
- Implemented: Basic leave arithmetic in `modules/elm/domain/leave_policy.py`, weekend/holiday helpers, and initial registry.
- Missing: Database ORM models, migrations, service layer, selectors, DRF views, React frontend, and state machine transitions.

#### Prompt 1.2
```text
Cross-reference the existing code in `modules/elm/domain/leave_policy.py` against the official ELM specification documents in `docs/elm_specs/`. Which business rules (BR-EL-001 through BR-EL-038) and composite workflows (CW-EL-01 to CW-EL-04) are implemented, which are only partially implemented, and which are completely unhandled?
```
**Findings:**
- Missing half-day Casual Leave (0.5 day).
- Missing accumulation caps (EL 300 days max, COL 20 days max).
- Missing substitute conflict checks (BR-EL-014).
- Missing multi-tier approval states (CW-EL-01), cancellation (CW-EL-02), extension (CW-EL-03), and resumption (CW-EL-04).

---

### Stage 2: Build / Run Verification & Platform Integration

#### Prompt 2.1
```text
Run the backend test suite using pytest on `modules/elm/tests/` and verify that the virtual environment, database migrations, and Django settings build and run without failures.
```
**Issue Encountered:** Windows `cp1252` encoding crash in `test_data_ownership.py` due to non-ASCII unicode characters in Python docstrings.

#### Prompt 2.2
```text
Fix the Windows `UnicodeDecodeError: 'charmap' codec can't decode byte` error occurring in `modules/accesscontrol/tests/test_data_ownership.py` by sanitizing all non-ASCII unicode characters in `modules/elm/`.
```
**Resolution:** Replaced all typographic symbols (em-dashes, arrows, box-drawing characters) with clean standard ASCII across all ELM files.

#### Prompt 2.3
```text
Resolve the `CommandError: permission manifest is invalid` error from `manage.py permission_manifest --check` regarding `elm.admin.year_end` and `elm.admin.configure_sla`, and regenerate `registry/permissions.json`.
```
**Resolution:**
1. Removed `elm.admin.year_end` from `ROLE_GRANTS["elm_admin"]` so it remains purely a background service permission (`SYSTEM_PERMISSIONS`).
2. Removed unused `elm.admin.configure_sla`.
3. Added `SCOPE_PERMISSIONS = ["elm.leave.view_all"]`.
4. Generated `registry/permissions.json` using `python manage.py permission_manifest`.

---

### Stage 3: Core Domain Logic & State Machine Engineering

#### Prompt 3.1
```text
Implement `modules/elm/domain/state_machine.py` modeling composite workflows CW-EL-01 through CW-EL-04 with states: DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_SANCTION, APPROVED, REJECTED, WITHDRAWN, ONGOING, CANCELLATION_PENDING, EXTENSION_PENDING, and RESUMPTION_PENDING. Include transition validation and role permission mapping.
```
**Resolution:** Created pure-Python state machine with explicit transitions, permission mapping (`elm.leave.apply`, `elm.leave.respond_substitute`, `elm.leave.approve`, `elm.leave.cancel`, `elm.leave.modify`), and terminal state guarantees.

#### Prompt 3.2
```text
Update `modules/elm/domain/leave_policy.py` to support all 6 leave types (CL, RH, SCL, EL, COL, VL), half-day Casual Leave (0.5), continuous vs non-continuous counting, year-end rollover caps (EL capped at 300, COL at 20), substitute conflict checks, and station-leave address requirements. Maintain backwards compatibility with Phase 1 functions.
```
**Resolution:** Implemented `count_leave_days()`, `has_overlap()`, `validate_substitute()`, `check_category_eligibility()`, `validate_leave_request()`, and preserved existing `is_leave_allowed()` and `business_days_between()`.

---

### Stage 4: Database Models, Migrations & Services

#### Prompt 4.1
```text
Create Django models in `modules/elm/models/leave.py` for `LeaveRequest`, `LeaveTransition` (audit history), `LeaveBalance`, and `HolidayCalendar`. Follow ADR-0013 strictly by storing integer user IDs instead of cross-module foreign keys, and generate migration `0001_initial.py`.
```
**Resolution:** Defined models with database constraints, indexes, immutable audit logging, and ran `python manage.py makemigrations elm && python manage.py migrate`.

#### Prompt 4.2
```text
Build transactional services in `modules/elm/services/leave_service.py` and `modules/elm/services/balances.py` for submitting leave, substitute response, Unit Head review, sanction, cancellation, extension, duty resumption (with unused balance refunds), and offline recording.
```
**Resolution:** Created atomic service functions managing state transitions, balance deductions, and audit transition creation.

#### Prompt 4.3
```text
Implement scoped querysets in `modules/elm/selectors/leave.py` providing role-based data isolation for visible requests, substitute queue, pending approvals, and balances.
```
**Resolution:** Fail-closed selectors scoping queries by caller user ID and permissions (`elm.leave.view_all`, `elm.leave.approve`).

---

### Stage 5: REST API & Frontend User Interface

#### Prompt 5.1
```text
Build fail-closed REST API views in `modules/elm/api/views.py` and serializers in `modules/elm/api/serializers.py` guarded by `HasModuleGrant("elm")` and `HasPermission(...)`. Mount routes in `modules/elm/api/urls.py` and include under `/api/v1/elm/` in `config/urls.py`.
```
**Resolution:** Created endpoints: `/requests/`, `/requests/<pk>/`, `/requests/<pk>/history/`, `/substitute/`, `/substitute/<pk>/respond/`, `/pending/`, `/requests/<pk>/review/`, `/requests/<pk>/sanction/`, `/requests/<pk>/cancel/`, `/requests/<pk>/extend/`, `/requests/<pk>/resume/`, `/balances/my/`, `/calendar/`, and `/offline/`.

#### Prompt 5.2
```text
Create the React + Mantine frontend for ELM under `client/src/modules/elm/`:
- TypeScript wire interfaces in `api/types.ts`
- React Query hooks in `api/hooks.ts`
- Pages: ApplyLeavePage, MyLeavesPage, LeaveBalancePage, SubstituteRequestsPage, PendingApprovalsPage, AllLeavesPage, HolidayCalendarPage, RecordOfflinePage
- Routes in `routes.tsx` registered in `client/src/app/registry.ts`
Ensure `npm run typecheck` and `npm run build` succeed cleanly.
```
**Resolution:** Full responsive frontend implemented with data tables, status badges, action modals, and transition timeline drawers.

---

### Stage 6: Comprehensive Testing & S3 Questionnaire

#### Prompt 6.1
```text
Write complete test suites in `modules/elm/tests/`:
- `test_leave_policy.py`: policy edge cases, counting, rollover
- `test_state_machine.py`: lifecycle transitions
- `test_services.py`: database transactions, approvals, refunds
- `test_api.py`: permission guards, 403 checks, API contracts
- `client/src/modules/elm/api/hooks.test.tsx`: frontend query hook tests
Ensure 100% tests pass.
```
**Resolution:** 72 backend ELM tests passed; full test suite (452/452 tests) passed across entire repository; 37/37 client tests passed.

#### Prompt 6.2
```text
Solve all 30 questions for Section S3 from `docs/questionnaires/S3.xlsx` based on the official ELM specifications (BR, UC, WF). Fill the Answers, Confidence (95-100), and Sources into the 'S3 Student Form' sheet and generate `docs/questionnaires/S3_SOLUTIONS.md`.
```
**Resolution:** All 30 questions analyzed and completed with 100% traceability to specific specification clauses.

---

### Stage 7: Final Verification & Delivery

#### Prompt 7.1
```text
Run final verification:
1. `python manage.py permission_manifest --check`
2. `pytest` across entire repo
3. `npm run typecheck` and `npm run build` in client
4. Review git status and push to origin branch `assignment-6-elm`
```
**Results:**
- Backend: 452/452 passed in 24.22s.
- Manifest: Matches registries cleanly.
- Client: TypeScript clean, production Vite bundle built in 8.63s.
- Git: Branch pushed cleanly to `Sumit-0011/Fusion-Integrated:assignment-6-elm`.
