# Mess Management System (MMS) - Architecture Blueprint

**Module Code**: `mms`  
**Docs Directory**: `docs/09-mms`  
**Specification Reference**: MMS v1.4 FINAL (Problem Statement v1.0, CFR/AFR Registry v1.4, Use Case Specifications v1.4, Business Rules v1.4, Workflow Specifications v1.4)  
**Status**: APPROVED by Student 2 for Phase 2 Proceeding  

---

## 1. Module Identity & Boundary

The Mess Management System (MMS) operates as an independent domain module within `Fusion-Integrated`.
- **Primary Domain**: Mess registration, caretaker/warden operational role assignments, weekly menu publishing, rebate lifecycle tracking, and student feedback.
- **Explicit Scope Boundaries**:
  - Excludes external payment collection, accounting settlement, payroll processing, procurement, stock, and inventory management (enforced by `BR-MMS-001`, `CFR-MMS-001`, `AFR-MMS-100`).
  - Uses employee and student identity identifiers from institutional master data, without owning master identity schemas.
  - Mess Admin is restricted strictly to operational role management and cannot access operational mess data (`BR-MMS-005`).

---

## 2. Domain Entities & Database Schema

All domain models extend `TimeStampedModel` from `core.db.mixins`:

1. **`MessRoleAssignment`**:
   - `mess_name` (CharField, max 64)
   - `role` (CharField, choices: `MessRole.CARETAKER = "caretaker"`, `MessRole.WARDEN = "warden"`)
   - `employee_id` (IntegerField, db_index=True)
   - `is_active` (BooleanField, default=True)
   - `assigned_date` (DateField, auto_now_add=True)
   - *Invariants*: Exactly one active Caretaker (`BR-MMS-003`) and one active Warden (`BR-MMS-004`) per mess.

2. **`RegistrationWindow`**:
   - `semester` (CharField, max 32)
   - `start_date` (DateField)
   - `end_date` (DateField)
   - `is_open` (BooleanField, default=True)
   - `created_by_id` (IntegerField)
   - *Invariants*: `start_date <= end_date`. Enforced by `BR-MMS-008`.

3. **`MessRegistration`**:
   - `student_id` (IntegerField, db_index=True)
   - `mess_name` (CharField, max 64)
   - `window` (ForeignKey -> RegistrationWindow, CASCADE, related_name="registrations")
   - `status` (CharField, choices: `PENDING`, `REGISTERED`, `REJECTED`, `DEREGISTERED`)
   - `registered_date` (DateField, auto_now_add=True)
   - `deregistration_date` (DateField, null=True, blank=True)
   - `reviewer_id` (IntegerField, null=True, blank=True)
   - `rejection_reason` (TextField, blank=True)
   - *Invariants*: Single active registration per student per window (`BR-MMS-010`).

4. **`DailyMenuItem`**:
   - `mess_name` (CharField, max 64)
   - `day_of_week` (CharField, choices: `DayOfWeek`)
   - `meal_time` (CharField, choices: `MealTime`)
   - `menu_description` (TextField)
   - `last_updated_by_id` (IntegerField, null=True, blank=True)
   - *Invariants*: Unique per `(mess_name, day_of_week, meal_time)` (`BR-MMS-014`).

5. **`RebateRequest`**:
   - `student_id` (IntegerField, db_index=True)
   - `mess_name` (CharField, max 64)
   - `start_date` (DateField)
   - `end_date` (DateField)
   - `duration_days` (PositiveIntegerField)
   - `reason` (TextField, blank=True)
   - `status` (CharField, choices: `PENDING`, `APPROVED`, `REJECTED`)
   - `reviewer_id` (IntegerField, null=True, blank=True)
   - `review_notes` (TextField, blank=True)
   - *Invariants*:
     - Minimum 3 consecutive days duration (`BR-MMS-021`).
     - Minimum 1 calendar day lead-time before start date (`BR-MMS-022`).
     - No overlapping active/approved rebate requests for the same student (`BR-MMS-023`).

6. **`MessFeedback`**:
   - `student_id` (IntegerField, db_index=True)
   - `mess_name` (CharField, max 64)
   - `category` (CharField, choices: `FOOD_QUALITY`, `CLEANLINESS`, `TIMELINESS`, `GENERAL`)
   - `comment` (TextField)
   - `is_addressed` (BooleanField, default=False)
   - `resolution_notes` (TextField, blank=True)

7. **`MessActionLog`**:
   - `action_by_id` (IntegerField)
   - `action_type` (CharField, max 64)
   - `target_id` (IntegerField, null=True, blank=True)
   - `details` (TextField, blank=True)

---

## 3. Pure Domain Rules (`modules.mms.domain.rules`)

Zero-framework dependency pure functions:
- `validate_role_assignment(role: str, employee_id: int) -> None`: Enforces valid roles (`caretaker`, `warden`) and valid positive `employee_id`.
- `validate_registration_window(window_start: date, window_end: date, request_date: date, is_open: bool) -> None`: Validates window open status and date containment.
- `validate_rebate_request(start_date: date, end_date: date, submission_date: date) -> int`: Validates lead-time (>= 1 calendar day), non-inverted dates, and duration (>= 3 days). Returns computed duration.
- `check_rebate_overlap(existing_rebates: list[dict], new_start: date, new_end: date) -> None`: Prevents overlapping date ranges for active/approved rebates.

---

## 4. Service Layer (`modules.mms.services`)

Encapsulates all atomic transactional operations (`@transaction.atomic`):
- `assign_mess_role(mess_name, role, employee_id, assigned_by_id) -> MessRoleAssignment`
- `open_registration_window(semester, start_date, end_date, created_by_id) -> RegistrationWindow`
- `submit_registration(student_id, mess_name, window_id) -> MessRegistration`
- `review_registration(registration_id, reviewer_id, approve, rejection_reason) -> MessRegistration`
- `update_menu_item(mess_name, day_of_week, meal_time, menu_description, updated_by_id) -> DailyMenuItem`
- `submit_rebate_request(student_id, mess_name, start_date, end_date, reason) -> RebateRequest`
- `review_rebate_request(rebate_id, reviewer_id, approve, review_notes) -> RebateRequest`
- `submit_feedback(student_id, mess_name, category, comment) -> MessFeedback`

---

## 5. Selectors & Public Inter-Module Contracts

1. **Selectors (`modules.mms.selectors`)**:
   - `get_active_mess_roles(mess_name: str)`
   - `get_open_registration_windows()`
   - `get_student_registrations(student_id: int)`
   - `get_student_rebates(student_id: int)`
   - `get_mess_rebates(mess_name: str)`
   - `get_weekly_menu(mess_name: str)`
   - `get_feedbacks(mess_name: Optional[str] = None)`

2. **Public Contracts (`modules.mms.contracts`)**:
   - `is_student_registered(student_id: int) -> bool`
   - `get_student_active_mess(student_id: int) -> Optional[dict]`
   - `has_active_rebate(student_id: int, on_date: date) -> bool`

---

## 6. API Layer & Permissions

Registered URL patterns under `/api/v1/mms/`:
- `GET /api/v1/mms/menu/` -> `MenuView` (`mess_module.menu.view`)
- `POST /api/v1/mms/menu/manage/` -> `ManageMenuView` (`mess_module.menu.manage`)
- `GET /api/v1/mms/windows/` -> `RegistrationWindowView` (`mess_module.registration.review`)
- `POST /api/v1/mms/windows/` -> `RegistrationWindowView` (`mess_module.registration.review`)
- `GET /api/v1/mms/registrations/` -> `RegistrationView` (`mess_module.registration.submit`)
- `POST /api/v1/mms/registrations/` -> `RegistrationView` (`mess_module.registration.submit`)
- `POST /api/v1/mms/registrations/<pk>/review/` -> `ReviewRegistrationView` (`mess_module.registration.review`)
- `GET /api/v1/mms/rebates/` -> `RebateView` (`mess_module.rebate.submit`)
- `POST /api/v1/mms/rebates/` -> `RebateView` (`mess_module.rebate.submit`)
- `GET /api/v1/mms/rebates/review/` -> `ReviewRebateView` (`mess_module.rebate.review`)
- `POST /api/v1/mms/rebates/<pk>/review/` -> `ReviewRebateView` (`mess_module.rebate.review`)
- `GET /api/v1/mms/feedback/` -> `FeedbackView` (`mess_module.feedback.submit`)
- `POST /api/v1/mms/feedback/` -> `FeedbackView` (`mess_module.feedback.submit`)
- `POST /api/v1/mms/roles/` -> `AssignRoleView` (`mess_module.role.assign`)

All endpoints enforce `IsAuthenticated` and `HasModuleGrant("mess_module")`.

---

## 7. Approval Record

- **Reviewer**: Student 2 (Gajji Sai Pavan Kumar, 24BCS080)
- **Status**: Formally Approved
- **Statement**: "I have reviewed the architecture blueprint and approve proceeding to Phase 2."
