# Employee Leave Management (ELM) Module — Phase 2 Implementation

This branch (`elmByMe-phase2`) improves the initial Phase-1 skeleton into a deployment-ready, robust ELM module integrated with the Fusion ERP architecture.

## Improvements Completed in Phase 2

1. **Leave Balances & Ledger (`models.py`, `services/leaves.py`)**:
   - Added `LeaveBalance` model tracking annual entitlement per user and category (`allocated`, `used`, `pending`, `available`).
   - Added `uniq_usr_yr_cat` unique constraint and performance indexes.
   - Synchronized leave requests with balance quotas: reserving pending balance on submission, debiting on approval, restoring on rejection, withdrawal, or cancellation.

2. **Domain Business Rules (`domain/entitlement.py`, `domain/state_machine.py`)**:
   - Implemented continuous vs non-continuous day counting (BR-EL-011): intervening weekends/holidays counted for EL, COL, VL; excluded for CL, RH, SCL.
   - Added half-day Casual Leave handling (0.5 day debit) with Forenoon (FN) / Afternoon (AN) session tagging (BR-EL-010).
   - Enforced strict applicant non-overlap validation (BR-EL-012) with the specific half-day CL exemption.
   - Implemented mandatory station details when requesting station leave (BR-EL-013).
   - Structured complete state machine lifecycle: DRAFT → AWAITING_SUBSTITUTE → UNIT_HEAD_QUEUE → ESTABLISHMENT → FINAL_DECISION → APPROVED / REJECTED / WITHDRAWN / CANCELLED.
   - Added substitute consent gate (BR-EL-014, BR-EL-015) allowing nominated substitutes to accept or decline before unit head review.
   - Enforced mandatory justification reasons on rejection (BR-EL-016..019).
   - Added pre-commencement approved leave cancellation with balance restoration (BR-EL-023).

3. **Public Contract Surface (`contracts.py`)**:
   - Implemented `get_leave_balances(user_ids)` querying live `LeaveBalance` tables and returning structured DTOs (adhering to plural contract conventions).

4. **API & Permission Scoping (`api/views.py`, `api/serializers.py`, `selectors/leaves.py`)**:
   - Added endpoints:
     - `GET /api/v1/leave/requests/`: Scoped request list (applicant, substitute, or reviewing authority)
     - `GET /api/v1/leave/requests/<pk>/`: Detailed view with transition audit history
     - `POST /api/v1/leave/requests/apply/`: Leave application endpoint with comprehensive input validation
     - `POST /api/v1/leave/requests/<pk>/substitute-action/`: Substitute consent acceptance/declination
     - `POST /api/v1/leave/requests/<pk>/transition/`: Reviewer recommendations, decisions, withdrawals, cancellations
     - `GET /api/v1/leave/balances/`: Personal quota summary cards
   - Configured OpenAPI schema generation with clean enum naming.

5. **Frontend UI Integration (`client/src/modules/leave/`)**:
   - Built complete React/TSX client module adhering to Fusion UX and Mantine design system:
     - `routes.tsx`: Lazy-loaded module routes mapped to `/leave/*`.
     - `pages/LeaveOverviewPage.tsx`: Executive summary dashboard with quick stats and recent requests.
     - `pages/ApplyLeavePage.tsx`: Interactive application form with dynamic quota checks, date pickers, station leave fields, and substitute selector.
     - `pages/MyLeavesPage.tsx`: User application tracking table with status badges and withdraw/cancel dialogs.
     - `pages/ApprovalsPage.tsx`: Administrative and substitute review queue with recommendation, approval, and rejection reason capture.
     - `pages/BalancesPage.tsx`: Visual progress cards of all leave categories (CL, RH, SCL, EL, COL, VL).
   - Registered module in `client/src/app/registry.ts`.
   - Wired server navigation items in `modules/leave/registry.py` matching routes 1-to-1 (verified via `ops/checks/nav_matches_routes.py`).

6. **Architecture & CI Verification**:
   - `python ops/checks/no_cross_module_fk.py`: PASSED (no cross-module FKs).
   - `python ops/checks/contracts_are_plural.py`: PASSED (all contract getters plural).
   - `python ops/checks/nav_matches_routes.py`: PASSED (sidebar and client routes agree).
   - `python manage.py makemigrations --check --dry-run`: PASSED (schema and migrations synchronized).
   - `python manage.py check`: PASSED (0 issues identified).
   - `python manage.py permission_manifest --check`: PASSED (permission manifest current).
   - `python manage.py spectacular --fail-on-warn`: PASSED (valid OpenAPI 3.0 schema).
   - `pytest modules/leave/tests/test_domain.py`: PASSED (domain logic verified).
