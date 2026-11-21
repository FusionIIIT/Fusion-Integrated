# Architecture Blueprint: Mess Management System (`mms`)

**Document Phase**: Phase 1 — Architecture Blueprint  
**Module Name**: Mess Management System  
**Module Code**: `mms`  
**Specification Reference**: `docs/09-mms/README.md`  
**Target Environment**: `module-only`  

---

## 1. Domain Models (`modules/mms/models.py`)

All models inherit from `core.db.mixins.TimeStampedModel`. No cross-module ForeignKeys are used; user IDs and employee IDs are stored as indexed integers.

1. **`MessRoleAssignment` (`mms_role_assignments`)**:
   - `employee_id`: `IntegerField(db_index=True)`
   - `role`: `CharField(max_length=20, choices=['caretaker', 'warden'])`
   - `start_date`: `DateField()`
   - `end_date`: `DateField(null=True, blank=True)`
   - `is_active`: `BooleanField(default=True, db_index=True)`
   - `assigned_by_id`: `IntegerField()`
   - `remarks`: `TextField(blank=True)`

2. **`RegistrationWindow` (`mms_registration_windows`)**:
   - `name`: `CharField(max_length=100)`
   - `mess_name`: `CharField(max_length=50, default="Central Mess")`
   - `start_date`: `DateField()`
   - `end_date`: `DateField()`
   - `is_open`: `BooleanField(default=True, db_index=True)`
   - `opened_by_id`: `IntegerField()`

3. **`MessRegistration` (`mms_registrations`)**:
   - `student_id`: `IntegerField(db_index=True)`
   - `window_id`: `IntegerField(null=True, blank=True, db_index=True)`
   - `mess_name`: `CharField(max_length=50, default="Central Mess")`
   - `start_date`: `DateField()`
   - `end_date`: `DateField(null=True, blank=True)`
   - `status`: `CharField(max_length=20, choices=['PENDING', 'REGISTERED', 'REJECTED', 'DEREGISTER_REQUESTED', 'DEREGISTERED'])`
   - `remarks`: `TextField(blank=True)`
   - `reviewed_by_id`: `IntegerField(null=True, blank=True)`
   - `deregistration_date`: `DateField(null=True, blank=True)`
   - `deregistration_reason`: `TextField(blank=True)`

4. **`DailyMenuItem` (`mms_daily_menu_items`)**:
   - `mess_name`: `CharField(max_length=50, default="Central Mess")`
   - `day_of_week`: `CharField(max_length=15, choices=['MONDAY'..'SUNDAY'])`
   - `meal_time`: `CharField(max_length=15, choices=['BREAKFAST', 'LUNCH', 'SNACKS', 'DINNER'])`
   - `items`: `TextField()`
   - `is_active`: `BooleanField(default=True)`
   - `updated_by_id`: `IntegerField(null=True, blank=True)`
   - Unique together: `('mess_name', 'day_of_week', 'meal_time')`

5. **`RebateRequest` (`mms_rebate_requests`)**:
   - `student_id`: `IntegerField(db_index=True)`
   - `mess_name`: `CharField(max_length=50, default="Central Mess")`
   - `start_date`: `DateField(db_index=True)`
   - `end_date`: `DateField(db_index=True)`
   - `duration_days`: `PositiveIntegerField()`
   - `reason`: `TextField()`
   - `status`: `CharField(max_length=20, choices=['PENDING', 'APPROVED', 'REJECTED'])`
   - `approved_start_date`: `DateField(null=True, blank=True)`
   - `approved_end_date`: `DateField(null=True, blank=True)`
   - `reviewed_by_id`: `IntegerField(null=True, blank=True)`
   - `decision_remarks`: `TextField(blank=True)`

6. **`MessFeedback` (`mms_feedbacks`)**:
   - `student_id`: `IntegerField(db_index=True)`
   - `mess_name`: `CharField(max_length=50, default="Central Mess")`
   - `rating`: `PositiveSmallIntegerField()` (1 to 5)
   - `category`: `CharField(max_length=30, choices=['FOOD_QUALITY', 'HYGIENE', 'STAFF_BEHAVIOR', 'TIMINGS', 'GENERAL'])`
   - `comments`: `TextField()`
   - `is_resolved`: `BooleanField(default=False)`
   - `resolution_notes`: `TextField(blank=True)`

7. **`MessActionLog` (`mms_action_logs`)**:
   - `entity_type`: `CharField(max_length=40)`
   - `entity_id`: `IntegerField()`
   - `actor_id`: `IntegerField()`
   - `action`: `CharField(max_length=50)`
   - `remarks`: `TextField(blank=True)`

---

## 2. API Endpoints & Permission Matrix (`modules/mms/api/urls.py`)

| Method | Endpoint | Description | Permission Code | Allowed Roles |
|---|---|---|---|---|
| `GET` | `/api/v1/mms/menu/` | View current weekly menu | `mess_module.menu.view` | Student, Caretaker, Warden |
| `POST` | `/api/v1/mms/menu/manage/` | Create or update menu item | `mess_module.menu.manage` | Caretaker |
| `POST` | `/api/v1/mms/registration/window/` | Open/manage registration window | `mess_module.registration.review` | Caretaker |
| `POST` | `/api/v1/mms/registration/apply/` | Student register/deregister | `mess_module.registration.submit` | Student |
| `POST` | `/api/v1/mms/registration/review/` | Caretaker review registration | `mess_module.registration.review` | Caretaker |
| `POST` | `/api/v1/mms/rebate/apply/` | Student apply for rebate | `mess_module.rebate.apply` | Student |
| `POST` | `/api/v1/mms/rebate/review/` | Caretaker review rebate | `mess_module.rebate.review` | Caretaker |
| `POST` | `/api/v1/mms/feedback/submit/` | Submit feedback/rating | `mess_module.feedback.submit` | Student |
| `GET` | `/api/v1/mms/oversight/logs/` | View audit logs & metrics | `mess_module.oversight.view` | Warden, Admin |
| `POST` | `/api/v1/mms/roles/assign/` | Assign Caretaker/Warden role | `mess_module.role.manage` | Admin, Warden |

---

## 3. Frontend Architecture (`client/src/modules/mms/`)

- **Root Routing (`routes.tsx`)**:
  - `/mms` -> `DashboardPage.tsx` (Summary of status, active mess, quick links)
  - `/mms/menu` -> `MenuPage.tsx` (Interactive weekly meal schedule)
  - `/mms/registration` -> `RegistrationPage.tsx` (Student registration & deregistration)
  - `/mms/rebates` -> `RebatesPage.tsx` (Rebate application & status table)
  - `/mms/caretaker` -> `CaretakerPage.tsx` (Review queues for caretaker)
  - `/mms/admin` -> `AdminPage.tsx` (Role assignments & audit log overview)

---

## 4. Formal Approval Gate
This architecture blueprint is frozen for student review. Student 2 must verify coverage against the module specifications and confirm approval before test automation proceeds.
