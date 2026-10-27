# Fusion ERP ELM Phase 2 Engineering Review (Assignment 6B)

## 1. Executive Summary & Git State
- **Branch**: `assignment6-elm-phase2` based cleanly on the original `assignment6-elm` commit (`0ed6ef3`, PR #77).
- **Preservation Policy**: All Phase 1 contributions remain intact on the base commit without overwriting or destructive rebasing. No unauthorized resets, cleans, or commits were executed.
- **Specification Baseline**: Synchronized against `ELM_Specifications_Bundle_v1.4_FINAL` (problem statement, functional requirements, use case specifications, business rules, traceability matrix, and workflow specifications v1.6).
- **Local Model Usage**: `deepseek-coder:6.7b` queried via local Ollama instance (`http://127.0.0.1:11434`) for defect diagnosis, verification, and code review.

---

## 2. Implemented Engineering Work & Fixes

### A. Domain State Machine & Lifecycle Workflows (`CW-EL-01`, `CW-EL-02`, `BR-EL-014`–`023`)
- **Resolved Defect**: Removed illegal direct transition `APPROVED -> CANCELLED`.
- **Expanded States**: Integrated substitute consent gate (`AWAITING_SUBSTITUTE_RESPONSE`, `APPLICANT_ACTION_REQUIRED`), Director self-sanction route (`AWAITING_DIRECTOR_SELF_SANCTION`), and multi-stage cancellation approval hierarchy (`CANCELLATION_PENDING_UNIT_HEAD`, `CANCELLATION_PENDING_ESTABLISHMENT`, `CANCELLATION_PENDING_FINAL_DECISION`).
- **Immediate Withdrawal**: Enforced `BR-EL-022` enabling withdrawal from all 6 pre-final pending states.
- **Pre-Start Cancellation Constraint**: Enforced `BR-EL-023` ensuring approved leave can only be cancelled prior to its start date.

### B. Persistence Layer & Migration Integrity
- **Models**:
  - `LeaveRequest`: added `half_day_type` (`FULL`, `FIRST_HALF`, `SECOND_HALF`) and station-leave coupling fields (`is_station_leave`, `station_leave_address`, `station_leave_contact`).
  - `LeaveBalance`: created with `DecimalField` for fractional day precision, positive balance check constraints, and unique compound index `(employee_user_id, leave_type, year)`.
  - `SubstituteResponse`: created to capture substitute consent responses with uniqueness per request and substitute.
  - `LeaveRequestTransition`: immutable audit history logging.
- **ADR-0013 Compliance**: Preserved zero cross-module foreign keys (`user_id` stored as plain integer references).
- **Migrations**: Generated `modules/elm/migrations/0001_initial.py`. Verified with `manage.py makemigrations --check --dry-run` ("No changes detected").

### C. Leave-Balance Service & Idempotent Year-End Conversion
- Implemented `modules/elm/services/balances.py`:
  - `credit_annual_leaves`: sets base entitlements (CL, RH, SCL, VL, EL, COL) per role.
  - `process_year_end`: executes year-end rollover and VL-to-EL conversion at 2 VL : 1 EL (`BR-EL-007`, `BR-EL-008`), preserves unused EL/COL carry-forward (`BR-EL-005`, `BR-EL-009`), and resets lapsed CL (`BR-EL-002`). Idempotent calculation prevents repeated accrual on reruns.
  - `calculate_leave_days`: calculates leave interval accounting for half-day CL requests (0.5 day) (`BR-EL-010`, `BR-EL-011`).
  - `debit_leave_balance`: debits leave balance upon final sanction approval (`BR-EL-010`, `BR-EL-023`).
  - `restore_leave_balance`: restores debited balance upon approved cancellation (`BR-EL-023`).

### D. Fusion Authentication, RBAC, & API Security
- **Endpoints**: `types`, `requests`, `requests/<pk>/transition`, `balances`, `substitute-responses`, `substitute-responses/<pk>/respond`.
- **Permissions**: Enforces `IsAuthenticatedPrincipal` and `HasModuleGrant("leave_elm")`.
- **Ownership Verification**: Enforced that only the applicant employee may withdraw or request cancellation of their leave request.
- **Substitute Consent Gate (`BR-EL-014`, `BR-EL-015`)**: Substitute acceptance routes application forward to Unit Head review; substitute decline transitions to `APPLICANT_ACTION_REQUIRED`. Enforced that substitute cannot be the applicant.
- **Applicant Non-Overlap Constraint (`BR-EL-012`)**: Rejects applications overlapping existing active requests with exception for non-overlapping first/second half-day CL.
- **Audit Logging**: State transitions create an atomic `LeaveRequestTransition` record recording actor and reason.

### E. Frontend UI Pages & Routing
- Replaced placeholder views in `client/src/modules/elm/pages/`:
  - `ApplyLeavePage.tsx`: application form with category selection, date ranges, half-day choices, and station-leave details.
  - `MyRequestsPage.tsx`: request list with status badges, action modals for withdrawal and cancellation request.
  - `LeaveBalancePage.tsx`: tabular view of credited, used, and remaining balances per category.
  - `SubstituteRequestsPage.tsx`: response dashboard for nominated substitutes to accept or decline coverage requests.
  - `UnitHeadReviewPage.tsx`: department review dashboard for Unit Heads to approve/reject CL/RH, recommend higher-sanction leaves, and sanction cancellation requests.
- Updated `client/src/modules/elm/routes.tsx` and registered lazy loader in `client/src/app/registry.ts`.

---

## 3. Actual Test & Check Results

| Check / Test Suite | Command Run | Result | Evidence |
| :--- | :--- | :--- | :--- |
| **All ELM Tests** | `python -m unittest discover -s modules/elm/tests -v` | **PASSED (22/22)** | Ran 22 tests in 0.050s (OK): API authentication, module grants, invalid status rejection, transition state updates, annual entitlements, 2:1 conversion ratio, substitute consent accept/decline gates, Director route, cancellation pipeline, immediate withdrawal, terminal locks, station leave capture, substitute self-nomination guard, non-overlap validation, leave start date cancellation lock, approval balance debiting, and cancellation balance restoration. |
| **Django System Check** | `python manage.py check` | **PASSED** | "System check identified no issues (0 silenced)." |
| **Migration Consistency** | `python manage.py makemigrations --check --dry-run` | **PASSED** | "No changes detected". |
| **Cross-Module FKs** | `python ops/checks/no_cross_module_fk.py` | **PASSED** | "no cross-module foreign keys" |
| **Contract Plurality** | `python ops/checks/contracts_are_plural.py` | **PASSED** | "all contract getters are plural" |
| **Nav Routes Parity** | `python ops/checks/nav_matches_routes.py` | **PASSED** | "nav items and client routes agree" |

---

## 4. Environment Blockers & Remaining Limitations
- **Container Environment (Docker)**: The local Windows Docker Desktop engine pipe (`npipe:////./pipe/dockerDesktopLinuxEngine`) was stopped/unreachable on the host. PostgreSQL migrations could not be applied against a live container database instance; verified via Django migration dry-run and ORM schema compilation instead.
- **Client Node Modules**: Host `client/node_modules` was missing, preventing `npm run build`; verified via static TypeScript definitions and `nav_matches_routes.py` route parity check.
