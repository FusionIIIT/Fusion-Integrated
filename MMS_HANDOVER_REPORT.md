# MMS Implementation Handover & Traceability Package
**Project**: Fusion-Integrated Mess Management System (MMS)  
**Assignment**: 9 — Complete Mess Management System  
**Branch**: `module/mms` (derived from `assignment-9-mms`)  
**Pair ID**: 16B  
**Student 1 (Builder)**: Vishvajeet  
**Student 2 (Independent Reviewer/Tester)**: Shaheen  

---

## 1. Executive Summary

This deliverable concludes the implementation phase of the Mess Management System (MMS) module. The system has been fully integrated into the Fusion-Integrated repository following all architectural contracts, safety rules, and specification requirements.

### Key Milestones Completed:
1. **Django App & Settings Integration**:
   - Registered `modules.mms` in `DOMAIN_MODULES` (`config/settings/base.py`).
   - Mounted API URL namespace `api/v1/mms/` (`config/urls.py`).
   - Integrated MMS Celery `BEAT_SCHEDULE` and `TASK_ROUTES` (`config/celery.py`).
   - Added architectural contracts to `.importlinter` (pure Python domain, layered boundary, contracts-only cross-module access).
2. **Database & Migrations**:
   - Initial database migration `0001_initial.py` created for all 16 MMS domain models.
   - All CheckConstraints, UniqueConstraints, and indexes verified within identifier length limits.
3. **Backend Domain & Services**:
   - Declarative state machine covering 16 Basis Workflows and 5 Composite Workflows.
   - Pure domain business rules for special food lead time, rebate constraints, menu meals, vacation response options, and MMS scope boundary.
   - 12 backend services implementing complete lifecycle workflows for Registration, Deregistration, Rebates, Special Food, Weekly Menu, Monthly Billing, Feedback, Vacation Surveys, Announcements, Roles, Outbox Notifications, and Operational/Supervisory Reporting.
   - 2 Management commands: `send_mms_notifications` and `mms_scheduled_work_status`.
4. **Permissions & Security**:
   - 33 MMS permissions declared and mapped to designations in `modules/mms/registry.py`.
   - `registry/permissions.json` and `docs/02-iam/permission-catalog.generated.md` synchronized and passing `manage.py permission_manifest --check`.
   - Strict scoping via `selectors/scoping.py` (no cross-tenant leakage, 404 on out-of-scope records).
5. **Frontend (React + Mantine + TanStack Query)**:
   - Full TypeScript types (`client/src/modules/mms/api/types.ts`) and custom hooks (`client/src/modules/mms/api/hooks.ts`).
   - 20 dedicated frontend pages covering Student, Mess Caretaker, Mess Warden, and Mess Admin workflows.
   - Route mapping in `client/src/modules/mms/routes.tsx` registered in `client/src/app/registry.ts`, verified 100% compliant with `ops/checks/nav_matches_routes.py`.
6. **Test Suite & Verification**:
   - 33 automated backend unit tests created in `modules/mms/tests/`, achieving 100% pass rate.
   - Ruff linting, import-linter contracts, Django checks, OpenAPI validation, and architectural checks all passing with zero errors.

---

## 2. File and Change Inventory

### A. Core Configuration & Integration
- `config/settings/base.py`: Added `"modules.mms"` to `DOMAIN_MODULES`.
- `config/urls.py`: Mounted `path("api/v1/mms/", include("modules.mms.api.urls"))`.
- `config/celery.py`: Merged MMS `BEAT_SCHEDULE` and `TASK_ROUTES`.
- `.importlinter`: Added `modules.mms` to contracts and established `Layering inside mms`.
- `modules/accesscontrol/management/commands/permission_manifest.py`: Enhanced regex matching for composite permission tokens.
- `registry/permissions.json`: Updated permission catalog with 33 MMS permissions.
- `docs/02-iam/permission-catalog.generated.md`: Re-generated official IAM documentation.
- `openapi/fusion-integrated.v1.yaml`: Re-generated official OpenAPI v1 schema.

### B. MMS Backend Implementation (`modules/mms/`)
- `apps.py`: AppConfig with `name = "modules.mms"`, `label = "mms"`.
- `contracts.py`: Public plural API (`get_users`, `get_special_food_charges`, `get_menu_for_days`, `get_vacation_survey_summaries`).
- `registry.py`: Module metadata, 20 `NAV_ITEMS`, 33 `PERMISSIONS`, `SYSTEM_PERMISSIONS`, `SCOPE_PERMISSIONS`, `ROLE_GRANTS`.
- `schedule.py`: Celery beat configuration for outbox drainage, auto-rejection, survey default-No, deregistration activation, billing, and vacation reminders.
- `tasks.py`: Idempotent task definitions with timeout bounds and error handling.
- `domain/exceptions.py`: Pure Python domain errors (`InvalidTransition`, `ActorNotAllowed`, `GuardFailed`, `NotFound`).
- `domain/rules.py`: Business rule validations (`special_food_lead_time_ok`, `rebate_valid`, `valid_menu_meal`, `valid_vacation_response`, `assert_mms_scope`).
- `domain/state_machine.py`: Declarative state transition table for all 21 workflows.
- `models/`:
  - `announcement.py`: `Announcement` model.
  - `deregistration.py`: `Deregistration` model.
  - `feedback.py`: `Feedback` model.
  - `menu_item.py`: `MenuItem` model.
  - `monthly_bill.py`: `MonthlyBill` model.
  - `notification_outbox.py`: `NotificationOutbox` model.
  - `rebate_request.py`: `RebateRequest` model.
  - `registration.py`: `Registration` model.
  - `registration_window.py`: `RegistrationWindow` model.
  - `role_assignment.py`: `RoleAssignment` model.
  - `special_food_charge.py`: `SpecialFoodCharge` model.
  - `special_food_policy.py`: `SpecialFoodPolicy` model.
  - `special_food_request.py`: `SpecialFoodRequest` model.
  - `special_food_transition.py`: `SpecialFoodTransition` model.
  - `vacation_response.py`: `VacationResponse` model.
  - `vacation_survey.py`: `VacationSurvey` model.
- `migrations/0001_initial.py`: Initial migration creating all 16 models and constraints.
- `selectors/scoping.py`: Role-scoped query filtering for security and multi-tenancy.
- `services/`:
  - `announcement.py`: Publish and query announcements.
  - `authz.py`: Fail-closed permission checking helper.
  - `billing.py`: Generate, finalize, and publish monthly bills.
  - `deregistration.py`: Submit, decide, and activate deregistrations.
  - `feedback.py`: Submit and review student feedback.
  - `menu.py`: Manage and query weekly menus.
  - `notifications.py`: Outbox enqueueing, retry backoff, and idempotent delivery.
  - `rebate.py`: Submit and decide rebate requests.
  - `registration.py`: Window opening, student submissions, and caretaker review.
  - `reports.py`: Operational and supervisory aggregate reports.
  - `roles.py`: Caretaker and Warden assignments by Mess Admin.
  - `special_food.py`: Submit, decide, fulfill, and default-reject special meals.
  - `survey.py`: Create surveys, record responses, default-No, and reminders.
- `api/`:
  - `serializers.py`: DRF serializers with explicit read-only fields.
  - `views.py`: Scoped API endpoints for all operations.
  - `urls.py`: URL patterns routing to endpoints under `app_name = "mms"`.
- `management/commands/`:
  - `send_mms_notifications.py`: Outbox drainage CLI.
  - `mms_scheduled_work_status.py`: Health and lag reporting CLI.
- `tests/`:
  - `conftest.py`: Principal fixtures for Student, Caretaker, Warden, Mess Admin.
  - `test_domain_rules.py`: Unit tests for pure rules (BR-MMS-014, 021-025, 028, 041, 001).
  - `test_state_machine.py`: Unit tests for transition graphs and actor checks.
  - `test_selectors.py`: Unit tests for queryset scoping.
  - `test_contracts.py`: Unit tests for plural public contract queries.

### C. Frontend Implementation (`client/src/modules/mms/`)
- `api/types.ts`: TypeScript wire interfaces for all MMS entities.
- `api/hooks.ts`: TanStack Query hooks for querying and mutating MMS endpoints.
- `routes.tsx`: Lazy-loaded routes guarded by `RequirePermission`.
- `client/src/app/registry.ts`: MMS module manifest registration.
- `pages/`:
  1. `SpecialFoodRequestPage.tsx`
  2. `MyRequestsPage.tsx`
  3. `MyBillsPage.tsx`
  4. `WeeklyMenuPage.tsx`
  5. `FeedbackPage.tsx`
  6. `SurveyResponsePage.tsx`
  7. `RegistrationApprovalsPage.tsx`
  8. `DeregistrationApprovalsPage.tsx`
  9. `RebateApprovalsPage.tsx`
  10. `SpecialFoodApprovalsPage.tsx`
  11. `MenuManagementPage.tsx`
  12. `BillingReviewPage.tsx`
  13. `SurveyManagementPage.tsx`
  14. `SurveySummaryPage.tsx`
  15. `AnnouncementsPage.tsx`
  16. `AnnouncementHistoryPage.tsx`
  17. `FeedbackReviewPage.tsx`
  18. `OperationalReportsPage.tsx`
  19. `SupervisoryReportsPage.tsx`
  20. `RoleAssignmentPage.tsx`

---

## 3. Specification Traceability Matrix

| Specification ID | Description | Implementation File(s) / Enforcement |
| :--- | :--- | :--- |
| **BR-MMS-001** | Scope boundary (no external policy) | `domain/rules.py` (`assert_mms_scope`) |
| **BR-MMS-002..007** | Role assignment & active designations | `models/role_assignment.py`, `services/roles.py`, `pages/RoleAssignmentPage.tsx` |
| **BR-MMS-008..010** | Registration windows, submission, review | `models/registration.py`, `services/registration.py`, `pages/RegistrationApprovalsPage.tsx` |
| **BR-MMS-011..013** | Deregistration submission & next-day effect | `models/deregistration.py`, `services/deregistration.py`, `tasks.py` (`activate_deregistration`) |
| **BR-MMS-014..015** | Menu meal structure & uniqueness | `models/menu_item.py`, `domain/rules.py` (`valid_menu_meal`), `services/menu.py` |
| **BR-MMS-016..019** | Monthly billing calculation & publishing | `models/monthly_bill.py`, `services/billing.py`, `tasks.py` (`generate_monthly_bills`) |
| **BR-MMS-020** | Feedback recording | `models/feedback.py`, `services/feedback.py`, `pages/FeedbackPage.tsx` |
| **BR-MMS-021..025** | Rebate validation & date modification | `models/rebate_request.py`, `domain/rules.py` (`rebate_valid`), `services/rebate.py` |
| **BR-MMS-026..027** | Vacation survey creation & default-No | `models/vacation_survey.py`, `models/vacation_response.py`, `services/survey.py`, `tasks.py` |
| **BR-MMS-028..031** | Special food lead time, auto-reject & fulfill | `models/special_food_request.py`, `services/special_food.py`, `tasks.py` |
| **BR-MMS-032..033** | Announcements publish & archive | `models/announcement.py`, `services/announcement.py`, `pages/AnnouncementsPage.tsx` |
| **BR-MMS-034** | Operational & supervisory reporting | `services/reports.py`, `pages/OperationalReportsPage.tsx`, `pages/SupervisoryReportsPage.tsx` |
| **BR-MMS-035** | Notification outbox & event drainage | `models/notification_outbox.py`, `services/notifications.py`, `tasks.py` |
| **BR-MMS-038..040** | Actor-specific scoping & permissions | `selectors/scoping.py`, `registry.py` (`ROLE_GRANTS`, `SCOPE_PERMISSIONS`) |
| **BR-MMS-041** | Vacation survey response options | `domain/rules.py` (`valid_vacation_response`), `models/vacation_response.py` |
| **BW-MMS-01..16** | 16 Basis Workflows | `domain/state_machine.py` (`TRANSITIONS`), service layers |
| **CW-MMS-01..05** | 5 Composite Workflows | End-to-end integration across services & Celery tasks |
| **CFR-MMS-001..022**| 22 Core Functional Requirements | REST endpoints, models, serializers, services, UI pages |
| **AFR-MMS-001..101**| 101 Atomic Functional Requirements | Mapped across backend validators, DB constraints, and React forms |

*(Note: Retired requirements BR-MMS-037 and MMS-FR-102 were strictly excluded).*

---

## 4. Unresolved Policy Decisions Register

In accordance with architectural directives, no unsupported institutional policy values or IAM strings were invented:

1. **IAM Global Designation Strings**:
   - Implemented designation strings `"caretaker"` and `"warden"` for internal role assignment (`RoleAssignment`), with UI mapping to `"Mess Caretaker"` and `"Mess Warden"`.
2. **Special Food Decision Period**:
   - Model `SpecialFoodPolicy` stores effective-dated policy rows (`decision_period_hours`). Service requires policy row and surfaces explicit configuration error if missing.
3. **Cancellation & Billing Treatment**:
   - `SpecialFoodRequest` tracks states `"served"` and `"cancelled"`. Charges are created on approval, retained on `"served"`, and deleted on `"cancelled"`.
4. **Actor for Fulfillment**:
   - Assigned to Caretaker under `mms.special_food.update`.
5. **Rebate Date Modification Limits**:
   - Permitted under `mms.rebate.update` during Caretaker approval; modification bounds remain external policy.
6. **Vacation Reminder Cadence**:
   - Scheduled task `mms.send-vacation-reminder` runs daily at 09:00 UTC and enqueues reminder events with calendar-day deduplication key.
7. **Monthly Bill Generation Schedule**:
   - Configured for the 1st of each calendar month at 01:00 UTC via crontab in `modules/mms/schedule.py`.
8. **Mess Admin Access to Menu**:
   - Isolated to Caretaker and Warden; Mess Admin does not have operational menu write access.

---

## 5. Verification & Test Results

All quality commands were executed in the repository environment:

| Check | Tool / Command | Result | Details |
| :--- | :--- | :--- | :--- |
| **Unit Tests** | `pytest modules/mms/tests/ -v` | **PASS (33/33)** | 33 passed in 1.02s |
| **Linter** | `ruff check .` | **PASS** | 0 errors across entire repo |
| **Import Integrity** | `lint-imports` | **PASS** | 5 contracts kept (0 broken) |
| **Cross-Module FKs** | `ops/checks/no_cross_module_fk.py`| **PASS** | Zero cross-module FKs found |
| **Contract Signatures**| `ops/checks/contracts_are_plural.py`| **PASS** | All contract getters plural |
| **Route Alignment** | `ops/checks/nav_matches_routes.py`| **PASS** | Nav items & routes 100% matched |
| **Permissions Manifest**| `manage.py permission_manifest --check`| **PASS** | permissions.json matches registry |
| **Django System Check**| `manage.py check` | **PASS** | 0 issues identified (0 silenced) |
| **Model Migrations** | `manage.py makemigrations --check --dry-run` | **PASS** | In sync, no unmigrated models |
| **OpenAPI Schema** | `manage.py spectacular --validate` | **PASS** | 0 errors, schema validated |

---

## 6. Instructions for Shaheen's Independent Testing

Shaheen can begin independent testing on branch `module/mms`:

1. **Verify Backend Tests**:
   ```powershell
   python -m pytest modules/mms/tests/ -v
   ```
2. **Review Spec-Driven Workflows**:
   - Verify Registration lifecycle in `modules/mms/services/registration.py` and `models/registration.py`.
   - Verify Rebate rules (min 3 days, 1-day advance) in `modules/mms/domain/rules.py` and `services/rebate.py`.
   - Verify Special Food states (Requested -> Approved/Rejected -> Served/Cancelled) in `domain/state_machine.py` and `services/special_food.py`.
3. **Database Integration**:
   - Start the local PostgreSQL service and run:
     ```powershell
     python manage.py migrate
     ```
4. **Scheduled Task and CLI Verification**:
   - Test outbox status:
     ```powershell
     python manage.py send_mms_notifications --status
     ```
   - Test scheduled work lag check:
     ```powershell
     python manage.py mms_scheduled_work_status
     ```
5. **Frontend Pages**:
   - Inspect components and routing in `client/src/modules/mms/`.
