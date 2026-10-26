# Changes Made by 24BCS260 — ELM Phase 2 Engineering Log

## 1. Student & Environment Configuration
- **Student Roll No**: 24BCS260
- **Repository**: `FusionIIIT/Fusion-Integrated`
- **Fork**: `https://github.com/uttkarshbagad/Fusion-Integrated`
- **Branch**: `elm-phase2`
- **Inherited Baseline**: Phase 1 implementation (`elm-pilot-qwen` / `ELM_MODEL_1`)
- **Machine**: Apple MacBook Air (M3, 16 GB Unified Memory)
- **Local AI Coding Model**: `qwen2.5-coder:7b` (via Ollama)
- **Coding Interface**: Continue VS Code Extension (Chat mode with `@file` context)

---

## 2. Inherited Phase-1 Baseline Audit
Reviewing the inherited Phase-1 code against the **ELM Specification Bundle v1.4** highlighted key areas requiring engineering attention:
1. **Incomplete Models**: `LeaveApplication` lacked a `reason` field, dropping user input. Status choices were limited to basic states (`PENDING`, `APPROVED`, etc.) without the workflow gates (`AWAITING_SUBSTITUTE`, `AWAITING_APPROVAL`) specified in `06_ELM_Workflow_Specifications_v1.6`. `SubstituteNomination` lacked a `status` field to record substitute consent (`BR-EL-015`).
2. **Missing Domain Validation**: No checks for leave balance sufficiency, date overlap (`BR-EL-012`), or self-nomination as substitute (`BR-EL-014`).
3. **Frontend Stubs**: `LeaveBalance.tsx` was empty; `LeaveApplication.tsx` only logged form inputs to `console.log` without calling the API.
4. **Test Coverage**: Zero unit or integration tests existed in `modules/elm/`.

---

## 3. Commit-by-Commit Engineering Log

### Commit 1 (e4afea2) — Models & Workflow Schema Alignment
- **Target File**: `modules/elm/models.py`
- **Objective**: Align data models with workflow state lifecycles and persist leave reasons and substitute response statuses.
- **Prompt to Qwen2.5-Coder:7b**:
```text
@models.py
Review and update modules/elm/models.py to satisfy the ELM specifications:
1. In LeaveApplication:
   - Add a `reason` TextField (blank=True, default="").
   - Update `STATUS_CHOICES` to include:
     ('AWAITING_SUBSTITUTE', 'Awaiting Substitute Consent'),
     ('AWAITING_APPROVAL', 'Awaiting Approval'),
     ('APPROVED', 'Approved'),
     ('REJECTED', 'Rejected'),
     ('WITHDRAWN', 'Withdrawn'),
     ('CANCELLED', 'Cancelled')
   - Default status should be 'AWAITING_APPROVAL'.

2. In SubstituteNomination:
   - Add a `status` CharField with choices:
     ('PENDING', 'Pending Consent'),
     ('ACCEPTED', 'Accepted'),
     ('DECLINED', 'Declined')
     with default='PENDING'.
   - Add a `decline_reason` TextField (blank=True, default="").

Preserve all existing table names (Meta db_table) and integer ID conventions for Fusion compatibility.
```

- **Observations & Code Review**:
  - The model accurately updated `STATUS_CHOICES` and added `reason`, `SubstituteNomination.status`, and `decline_reason`.
  - **Defect Caught During Review**: The model retained `models.CharField(max_length=10)` on `LeaveApplication.status`. Because `"AWAITING_SUBSTITUTE"` is 19 characters, this would have triggered database truncation/`DataError` at runtime.
  - **Action**: Updated `max_length` to `30` on `LeaveApplication.status` and `20` on `SubstituteNomination.status`.

- **Commit**: `e4afea2` — `feat(elm): update models with workflow statuses and reasons`

---

### Commit 2 (9e9507e) — Pure-Python Domain Business Rules & Transitions
- **Target File**: `modules/elm/domain/policy.py`
- **Objective**: Implement pure-Python domain business rules (`BR-EL-012`, `BR-EL-014`, balance validation, and workflow state transitions) with no Django or ORM dependencies.
- **Prompt to Qwen2.5-Coder:7b**:
```text
@policy.py
Update modules/elm/domain/policy.py with pure-Python business rules from the ELM Specification Bundle (no Django or ORM imports):

1. Add `validate_substitute_eligibility(applicant_id: int, substitute_id: int) -> None`:
   - Raise ValueError if applicant_id == substitute_id (BR-EL-014).

2. Add `check_date_overlap(start_a: date, end_a: date, start_b: date, end_b: date) -> bool`:
   - Return True if the two date intervals [start_a, end_a] and [start_b, end_b] overlap (BR-EL-012).

3. Add `validate_balance_sufficiency(current_balance: float | int, requested_days: float | int) -> None`:
   - Raise ValueError("Insufficient leave balance") if requested_days > current_balance.

4. Add `is_valid_transition(current_status: str, target_status: str) -> bool`:
   - Implement the allowed state transitions:
     - AWAITING_SUBSTITUTE -> AWAITING_APPROVAL, WITHDRAWN
     - AWAITING_APPROVAL -> APPROVED, REJECTED, WITHDRAWN
     - APPROVED -> CANCELLED
   - Return False for all other transitions.

Keep all existing LeaveCode, LeaveEntitlement, LEAVE_ENTITLEMENTS, and requested_days functions intact.
```

- **Observations & Code Review**:
  - The model correctly added `validate_substitute_eligibility`, `check_date_overlap`, `validate_balance_sufficiency`, and `is_valid_transition`.
  - Zero Django or ORM dependencies were introduced, fully respecting Fusion ERP's strict architecture rule (`domain/` may not import Django, DRF or Celery).
- **Commit**: `9e9507e` — `feat(elm): add pure-Python domain business rules and transition validators`

---

### Commit 3 (ae43983) — Service Layer Workflow & Business Rule Integration
- **Target File**: `modules/elm/services/applications.py`
- **Objective**: Integrate domain validations into the application service and implement full lifecycle workflows (leave submission with balance/overlap gates, substitute nomination with eligibility gates, substitute consent responses, supervisor reviews with balance deduction, and withdrawals).
- **Prompt to Qwen2.5-Coder:7b**:
```text
Look strictly at `modules/elm/services/applications.py`, `modules/elm/models.py`, and `modules/elm/domain/policy.py`.

Update `modules/elm/services/applications.py` with this exact structure:

from datetime import date
from django.db import transaction
from modules.elm.domain.policy import (
    check_date_overlap,
    is_valid_transition,
    requested_days,
    validate_balance_sufficiency,
    validate_substitute_eligibility,
)
from modules.elm.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveType,
    SubstituteNomination,
)

1. `submit_leave_application`:
   - Arguments: applicant_id: int, leave_type: LeaveType, start_date: date, end_date: date, reason: str = "", station_leave_details: str = ""
   - Calculate days = requested_days(start_date, end_date)
   - Fetch applicant's LeaveBalance for leave_type; call validate_balance_sufficiency(balance_obj.balance, days)
   - Query existing LeaveApplications for applicant with status in ["AWAITING_SUBSTITUTE", "AWAITING_APPROVAL", "APPROVED"]; for each, if check_date_overlap(app.start_date, app.end_date, start_date, end_date) is True, raise ValueError("Overlapping leave application exists.")
   - Create LeaveApplication with status="AWAITING_APPROVAL", reason=reason.

2. `nominate_substitute`:
   - Arguments: leave_application: LeaveApplication, substitute_id: int, start_date: date, end_date: date, reason: str = ""
   - Call validate_substitute_eligibility(leave_application.applicant_id, substitute_id)
   - Create SubstituteNomination with status="PENDING"
   - Update leave_application.status = "AWAITING_SUBSTITUTE", save.

3. `respond_substitute_nomination`:
   - Arguments: nomination: SubstituteNomination, accept: bool, decline_reason: str = ""
   - If accept: nomination.status = "ACCEPTED", nomination.leave_application.status = "AWAITING_APPROVAL", save both.
   - If not accept: nomination.status = "DECLINED", nomination.decline_reason = decline_reason, save.

4. `review_leave_application`:
   - Arguments: application: LeaveApplication, approve: bool
   - If approve:
     - Check is_valid_transition(application.status, "APPROVED")
     - Fetch applicant's LeaveBalance with select_for_update(); deduct requested_days; save balance.
     - application.status = "APPROVED", save.
   - If reject:
     - Check is_valid_transition(application.status, "REJECTED")
     - application.status = "REJECTED", save.

5. `withdraw_application`:
   - Check is_valid_transition(application.status, "WITHDRAWN")
   - application.status = "WITHDRAWN", save.

6. Keep `get_employee_balances(employee_id: int)`.
```

- **Defects Caught During Human-in-the-Loop Review**:
  1. *Explanation vs. Code Discrepancy*: In `nominate_substitute`, Qwen's explanation stated that it updated the leave application status to `AWAITING_SUBSTITUTE`, but it completely omitted those lines (`leave_application.status = "AWAITING_SUBSTITUTE"; leave_application.save()`) in the generated code block.
  2. *Related Object Persistence Bug*: In `respond_substitute_nomination`, Qwen mutated `nomination.leave_application.status = "AWAITING_APPROVAL"` in memory, but only called `nomination.save()`. It forgot to call `save()` on `nomination.leave_application`, meaning the status would never be persisted in the database!
  3. *Missing Null Safety*: In `submit_leave_application`, it accessed `balance_obj.balance` without checking if `balance_obj` is `None`, risking an unhandled `AttributeError`.
- **Engineering Actions Applied**:
  - Added explicit `leave_application.save(update_fields=["status"])` to both `nominate_substitute` and `respond_substitute_nomination`.
  - Added defensive `None` check raising `ValueError` when an applicant lacks a balance record.
  - Enforced atomic transactions and `select_for_update()` during supervisor review balance deductions to prevent race conditions.
- **Commit**: `ae43983` — `feat(elm): integrate domain rules and workflow actions into application service`

---

### Commit 4 (916bed9) — Database Schema Migration
- **Target File**: `modules/elm/migrations/0002_add_workflow_and_reason_fields.py`
- **Objective**: Create the Django schema migration reflecting the new fields (`reason`, `SubstituteNomination.status`, `decline_reason`) and updated `LeaveApplication.status` choices and length.
- **Context Files Provided**: `modules/elm/models.py`, `modules/elm/migrations/0001_initial.py`
- **Prompt to Qwen2.5-Coder:7b**:
```text
Based on `modules/elm/models.py` and `modules/elm/migrations/0001_initial.py`:

Write the Django schema migration `modules/elm/migrations/0002_add_workflow_and_reason_fields.py` to reflect the updated models:
1. Set dependencies = [('elm', '0001_initial')].
2. AddField `reason` (models.TextField, blank=True, default='') to `leaveapplication`.
3. AlterField `status` on `leaveapplication` with max_length=30, default='AWAITING_APPROVAL', and the updated STATUS_CHOICES from models.py.
4. AddField `status` on `substitutenomination` with max_length=20, default='PENDING', and STATUS_CHOICES from models.py.
5. AddField `decline_reason` (models.TextField, blank=True, default='') to `substitutenomination`.
```

- **Engineering Action**: Corrected the operation on `substitutenomination.status` to `migrations.AddField`.
- **Commit**: `916bed9` — `feat(elm): add schema migration for workflow statuses and reasons`

---

### Commit 5 (937b9dc) — Domain Unit Test Suite
- **Target File**: `modules/elm/tests/test_policy.py`
- **Objective**: Establish the first automated unit test suite for ELM to test pure-Python domain business rules (`BR-EL-012`, `BR-EL-014`, balance validation, workflow state transitions, and requested days calculation).
- **Context File Provided**: `modules/elm/domain/policy.py`
- **Prompt to Qwen2.5-Coder:7b**:
```text
Based on `modules/elm/domain/policy.py`:

Write a comprehensive pytest unit test suite in `modules/elm/tests/test_policy.py` to test the pure-Python domain rules:

1. Test `validate_substitute_eligibility`:
   - Passes when applicant_id != substitute_id.
   - Raises ValueError when applicant_id == substitute_id (BR-EL-014).

2. Test `check_date_overlap` (BR-EL-012):
   - Returns True for overlapping intervals (e.g., Oct 1-5 and Oct 4-8, or nested intervals).
   - Returns False for disjoint/adjacent intervals (e.g., Oct 1-5 and Oct 6-10).

3. Test `validate_balance_sufficiency`:
   - Passes when balance >= requested days.
   - Raises ValueError when requested days > balance.

4. Test `is_valid_transition`:
   - Returns True for allowed transitions (AWAITING_SUBSTITUTE -> AWAITING_APPROVAL/WITHDRAWN, AWAITING_APPROVAL -> APPROVED/REJECTED/WITHDRAWN, APPROVED -> CANCELLED).
   - Returns False for illegal transitions (e.g. APPROVED -> REJECTED, REJECTED -> APPROVED, WITHDRAWN -> APPROVED).

5. Test `requested_days`:
   - Correct day count for valid ranges.
   - Raises ValueError if end_date < start_date.

Write clean, idiomatic pytest functions without Django database fixtures (pure Python unit tests).
```

- **Defects Caught During Human-in-the-Loop Review**:
  1. *Missing Import*: The model called `date(2023, 10, 1)` throughout the tests but omitted `from datetime import date`. This would have caused `pytest` to immediately fail with `NameError: name 'date' is not defined`.
  2. *Contradictory Overlap Assertion*: In `test_check_date_overlap`, line 18 asserted that `(Oct 1-5)` and `(Oct 6-10)` **do** overlap (`assert check_date_overlap(...)`), and then three lines later asserted that `(Oct 1-5)` and `(Oct 6-10)` **do not** overlap (`assert not check_date_overlap(...)`). Since the dates are disjoint, line 18 would fail `pytest`.
- **Engineering Actions Applied**:
  - Added `from datetime import date` to imports.
  - Replaced the contradictory line with valid partial and nested/enclosed overlap test cases.
- **Commit**: `937b9dc` — `test(elm): add automated pytest suite for domain policy business rules`

---

### Commit 6 (fa0e6a3) — REST API Layer (Serializers, Views, and URL Routing)
- **Target Files**: `modules/elm/api/serializers.py`, `modules/elm/api/views.py`, `modules/elm/api/urls.py`
- **Objective**: Wire HTTP endpoints and request/response serializers to the application service layer to support the complete leave application lifecycle (submission, substitute responses, supervisor review, and withdrawal).
- **Context Files Provided**: `modules/elm/api/serializers.py`, `modules/elm/api/views.py`, `modules/elm/api/urls.py`, `modules/elm/services/applications.py`
- **Prompts to Qwen2.5-Coder:7b**:
```text
Update modules/elm/api/serializers.py:
1. In LeaveApplicationSerializer: include 'reason' and make 'status' and 'applicant_id' read-only.
2. Add SubstituteNominationSerializer with 'status' read-only.
3. Add SubstituteResponseSerializer with accept and decline_reason.
4. Add ReviewApplicationSerializer with approve.

Update modules/elm/api/views.py and modules/elm/api/urls.py:
1. In LeaveApplicationListCreateView.post: call submit_leave_application, catch ValueError -> HTTP 400.
2. Add SubstituteResponseView: call respond_substitute_nomination.
3. Add LeaveApplicationReviewView: call review_leave_application.
4. Add LeaveApplicationWithdrawView: call withdraw_application.
```

- **Defects Caught During Human-in-the-Loop Review**:
  1. *Omission of Existing Endpoint*: Qwen accidentally omitted `LeaveBalanceListView` from `views.py` while keeping its route in `urls.py`, which would crash routing with an `AttributeError`.
  2. *Missing Imports*: `HasPermission` and `SubstituteNominationSerializer` were referenced in the views without being imported, causing `NameError`.
  3. *URL Signature Mismatch (`TypeError`)*: In `urls.py`, routes were defined with `<int:pk>`, but Qwen defined the view methods as `post(self, request)` without `pk`, which causes DRF to raise `TypeError: post() got an unexpected keyword argument 'pk'`.
  4. *Passing Raw String ID instead of Model Instance*: The service functions expect model instances (`application: LeaveApplication`), but Qwen passed `request.data['id']` directly, causing `AttributeError: 'str' object has no attribute 'status'`.
- **Engineering Actions Applied**:
  - Preserved `LeaveBalanceListView` in `views.py`.
  - Added all required imports (`get_object_or_404`, `HasPermission`, `SubstituteNominationSerializer`).
  - Corrected method signatures to `post(self, request, pk: int)` and fetched model instances via `get_object_or_404`.
  - Added OpenAPI `@extend_schema` annotations for schema compliance.
- **Commit**: `fa0e6a3` — `feat(elm): wire complete REST API views, serializers, and routes`

---

### Commit 7 (4d1a882) — Frontend Client Integration (React Components & API Client)
- **Target Files**: `client/src/modules/elm/api.ts`, `client/src/modules/elm/LeaveBalance.tsx`, `client/src/modules/elm/LeaveApplication.tsx`
- **Objective**: Replace frontend placeholder stubs and mock console logs with live data fetching and form submission handling wired to the REST API.
- **Context Files Provided**: `client/src/modules/elm/api.ts`, `client/src/modules/elm/LeaveBalance.tsx`, `client/src/modules/elm/LeaveApplication.tsx`
- **Prompt to Qwen2.5-Coder:7b**:
```text
Look strictly at `client/src/modules/elm/api.ts`, `client/src/modules/elm/LeaveBalance.tsx`, and `client/src/modules/elm/LeaveApplication.tsx`.

1. In `api.ts`:
   - Add `reason?: string` to `LeaveApplicationPayload`.

2. Update `LeaveBalance.tsx`:
   - Use `useEffect` to fetch balances on mount using `fetchLeaveBalances()`.
   - Render a loading state, error state, and a clean table/card list displaying the leave balances.

3. Update `LeaveApplication.tsx`:
   - Connect the form submission to `submitLeaveApplication(...)`.
   - Show loading state while submitting.
   - Show a success alert upon successful creation and reset the form.
   - Catch errors and display the error message to the user.
```

- **Defects Caught During Human-in-the-Loop Review**:
  1. *Hallucinated Dependency (`react-toastify`)*: Qwen added `import { toast } from "react-toastify"`. The Fusion project does not have `react-toastify` installed (Fusion uses Mantine UI), which would cause `npm run build` and `npm run typecheck` to fail with `Cannot find module 'react-toastify'`.
  2. *Missing TypeScript Type Import*: In `LeaveBalance.tsx`, Qwen annotated state as `useState<LeaveBalanceRow[]>([])` without importing `LeaveBalanceRow`.
  3. *Redundant Relative Path*: Imported from `"../../modules/elm/api"` when `api.ts` is in the same directory (`./api`).
- **Engineering Actions Applied**:
  - Replaced the uninstalled toast dependency with self-contained, clean notification banners.
  - Imported `type LeaveBalanceRow` from `./api`.
  - Added `reason?: string` to `LeaveApplicationPayload` in `api.ts`.
  - Added form validation, loading states, and reset handling.
- **Commit**: `4d1a882` — `feat(elm): wire LeaveBalance and LeaveApplication frontend to REST API`






