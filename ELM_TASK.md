# TASK: Implement Employee Leave Management (ELM) in Fusion-Integrated

You are implementing the Employee Leave Management (ELM) module in the Fusion-Integrated repository as an autonomous coding agent. 

---

### CRITICAL OPERATING CONSTRAINTS (FOR LOCAL 9B MODEL)
1. MAKE ACTUAL WORKSPACE EDITS: You must execute file creation, file editing, and terminal commands directly. Do not merely describe plans, print pseudocode, or stop after planning.
2. WORK IN SMALL, DISCRETE STAGES: Execute one stage at a time. After finishing each stage, inspect `git status`, verify syntax, and proceed.
3. CONTEXT BUDGET MANAGEMENT: Never cat or dump large files into context. Do NOT re-extract or touch files in `ELM-Specs/` or `extract_elm.py`. The requirements are already fully summarized in this prompt.
4. PRESERVE UNRELATED WORK: Do not modify `modules/placement/`, `modules/directory/`, or `modules/accesscontrol/`. Only perform permitted mechanical integrations.
5. STRICT INSTRUCTOR RESTRICTIONS: Do not audit business-rule correctness, do not invent missing requirements, do not perform speculative refactoring, and do not alter the provided state names. Focus strictly on clean, working implementation and mechanical integration checks.

---

### ARCHITECTURAL SEAMS & CONVENTIONS TO REUSE
- Module Code & Path: Module name is `leave`. Backend package is `modules/leave/`, frontend package is `client/src/modules/leave/`, API mount is `/api/v1/leave/`, frontend route base is `/leave`.
- Identity & DB: Fusion has NO User table. Identity is external (IAM). Every person reference (applicant, substitute, approver) is a plain integer `user_id`. Use `core.db.mixins.TimeStampedModel` and `core.db.mixins.UserScopedModel`. NEVER declare a ForeignKey to auth user or another module.
- Cross-Module Calls: Only import other modules via `contracts.py` (e.g. `from modules.directory import contracts as directory`). Contract functions must accept sequences: `directory.get_users(user_ids)`.
- Error Envelope: Raise exceptions from `core.api.exceptions`: `ConflictError` (409), `BadRequestError` (400), `NotFoundError` (404), `PermissionDeniedError` (403). They format into standard `{"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}`.
- Dual Authorization Gates: In views, enforce `permission_classes = [HasModuleGrant("leave"), HasPermission("<perm_code>")]`.
- Permissions & Enforcement Check: Every permission code declared in `registry.PERMISSIONS` (unless listed in `SYSTEM_PERMISSIONS` or `SCOPE_PERMISSIONS`) MUST appear as a string literal in your `api/`, `services/`, `models/`, or `domain/` code, otherwise `manage.py permission_manifest --check` fails.

---

### STAGE 1: PURE-PYTHON DOMAIN ENGINE (`modules/leave/domain/`)
Create framework-free Python files. Zero imports of Django, DRF, or Celery (`.importlinter` enforced):
1. `modules/leave/domain/constants.py`:
   - Categories: `CL = "cl"`, `RH = "rh"`, `SCL = "scl"`, `EL = "el"`, `VL = "vl"`, `COL = "col"`.
   - Entitlements: `CL_ANNUAL = 8`, `RH_ANNUAL = 2`, `SCL_ANNUAL = 15`, `EL_NON_FACULTY_ANNUAL = 30`, `VL_FACULTY_ANNUAL = 60`, `COL_ANNUAL = 20`.
   - Leave Statuses:
     - New Leave: `DRAFT`, `AWAITING_SUBSTITUTE`, `APPLICANT_ACTION_REQUIRED`, `AWAITING_UNIT_HEAD`, `AWAITING_ESTABLISHMENT`, `AWAITING_FINAL_SANCTION`, `AWAITING_DIRECTOR_SANCTION`, `APPROVED`, `REJECTED`, `WITHDRAWN`.
     - Cancellation: `CANCELLATION_PENDING_UNIT_HEAD`, `CANCELLATION_PENDING_ESTABLISHMENT`, `CANCELLATION_PENDING_FINAL`, `CANCELLED`, `CANCELLATION_REJECTED`.
     - Extension: `EXTENSION_AWAITING_SUBSTITUTE`, `EXTENSION_APPLICANT_ACTION_REQUIRED`, `EXTENSION_AWAITING_UNIT_HEAD`, `EXTENSION_PENDING_ESTABLISHMENT`, `EXTENSION_PENDING_FINAL`, `EXTENSION_APPROVED`, `EXTENSION_REJECTED`, `EXTENSION_WITHDRAWN`.
     - Resumption: `RESUMPTION_PENDING`, `RESUMPTION_NORMAL`, `RESUMPTION_EARLY`, `RESUMPTION_LATE`.
   - Actors: `EMPLOYEE`, `SUBSTITUTE`, `UNIT_HEAD`, `ESTABLISHMENT`, `SANCTIONING_AUTHORITY`, `DIRECTOR`, `LEAVE_ADMIN`, `SYSTEM`.
2. `modules/leave/domain/calculations.py`:
   - `calculate_chargeable_days(category, start_date, end_date, half_day_type, holidays, weekends)`:
     - `CL`, `RH`, `SCL`: Non-continuous counting. Exclude weekends and closed holidays. If half-day CL (`first_half` or `second_half`), count exactly `0.5` day (`BR-EL-010`).
     - `EL`, `COL`, `VL`: Continuous counting (`BR-EL-011`). Intervening weekends and closed holidays within the approved interval count as leave days.
   - `convert_vl_to_el(unused_vl: float) -> float`: Returns `unused_vl / 2.0` (preserves fractions, `BR-EL-007`).
3. `modules/leave/domain/state_machine.py`:
   - Declarative transition dictionary mapping `(current_state, action, actor_kind) -> next_state` matching all 17 Basis Workflows (`BW-EL-01`..`17`) and 4 Composite Workflows (`CW-EL-01`..`04`):
     - New Leave (`CW-EL-01`): `DRAFT` $\rightarrow$ `AWAITING_SUBSTITUTE` (if coverage required) or `AWAITING_UNIT_HEAD` (or `AWAITING_DIRECTOR_SANCTION` for Director). Substitute accept $\rightarrow$ `AWAITING_UNIT_HEAD`; decline $\rightarrow$ `APPLICANT_ACTION_REQUIRED`. Unit Head for CL/RH $\rightarrow$ `APPROVED`/`REJECTED`. Unit Head for higher-sanction $\rightarrow$ `AWAITING_ESTABLISHMENT` or `AWAITING_FINAL_SANCTION`. Terminal withdrawal $\rightarrow$ `WITHDRAWN` from any pending state (`BR-EL-022`, `BR-EL-034`).
     - Cancellation (`CW-EL-02`): Only pre-start (`BR-EL-023`). Approved cancellation $\rightarrow$ `CANCELLED` and restores balance; reject $\rightarrow$ `CANCELLATION_REJECTED` (original leave preserved).
     - Extension (`CW-EL-03`): Ongoing EL/COL/VL only. Approved $\rightarrow$ `EXTENSION_APPROVED` (posts incremental days only, `BR-EL-025`).
     - Resumption (`CW-EL-04`): `RESUMPTION_PENDING` $\rightarrow$ `RESUMPTION_NORMAL`, `RESUMPTION_EARLY`, or `RESUMPTION_LATE` (`BR-EL-028`).

---

### STAGE 2: DATABASE MODELS & MIGRATIONS (`modules/leave/models/`)
Create Django models in `modules/leave/models/`:
1. `modules/leave/models/policy.py`:
   - `LeavePolicyParameter`: Singleton/per-category annual entitlements, carry-forward caps, and SLA thresholds (`BR-EL-030`, `BR-EL-038`).
   - `HolidayCalendar`: Date, name, `is_rh` (boolean), `year`, `is_published` (`BR-EL-031`).
2. `modules/leave/models/ledger.py`:
   - `LeaveBalanceLedger`: Inherits `UserScopedModel`, `TimeStampedModel`. Tracks `year`, `category`, `balance`, `credited`, `utilized`, `carried_forward`.
   - `LeaveLedgerTransaction`: Append-only transaction audit logging `user_id`, `category`, `delta`, `transaction_type` (`credit`, `deduction`, `reversal`, `vl_conversion`, `resumption_adj`), and `reference_id`.
3. `modules/leave/models/requests.py`:
   - `LeaveRequest`: Inherits `UserScopedModel`, `TimeStampedModel`.
     - Fields: `category` (CharField), `start_date` (DateField), `end_date` (DateField), `half_day_type` (`none`, `first_half`, `second_half`), `chargeable_days` (DecimalField), `purpose` (TextField), `station_leave_required` (BooleanField), `station_leave_details` (JSONField/TextField), `substitute_user_id` (IntegerField, null=True, blank=True), `substitute_status` (`none`, `pending`, `accepted`, `declined`), `status` (CharField), `is_faculty` (BooleanField), `current_assignee_id` (IntegerField, null=True, blank=True).
   - `LeaveRequestTransition`: Audit trail logging `leave_request_id` (FK to `LeaveRequest`), `from_status`, `to_status`, `actor_user_id`, `actor_role`, `remarks`, `created_at`.
4. `modules/leave/models/actions.py`:
   - `CancellationRequest`: FK to `LeaveRequest`, `reason`, `status`.
   - `ExtensionRequest`: FK to `LeaveRequest`, `requested_end_date`, `incremental_days`, `substitute_user_id`, `status`.
   - `ResumptionRecord`: FK to `LeaveRequest`, `actual_resumption_date`, `diff_days`, `status` (`pending`, `normal`, `early`, `late`), `adjustment_applied` (BooleanField).
   - `OfflineSanctionRecord`: `UserScopedModel`, `category`, `start_date`, `end_date`, `chargeable_days`, `sanction_order_ref`, `recorded_by_user_id`, `created_at` (`BR-EL-029`).
5. Export all in `modules/leave/models/__init__.py`.
6. Create `modules/leave/apps.py` with `LeaveConfig` (`name = "modules.leave"`, `label = "leave"`).
7. Add `"modules.leave"` to `DOMAIN_MODULES` in `config/settings/base.py`.
8. Run `python manage.py makemigrations leave`.

---

### STAGE 3: SELECTORS & TRANSACTIONAL SERVICES (`modules/leave/selectors/` & `services/`)
1. `modules/leave/selectors/scoping.py`:
   - `requests_for(actor)`: Plain employees see only `user_id == actor.user_id`. Unit Heads see department employees. Sanctioning authorities see items routed to them. Out-of-scope requests filter out so detail views return 404 (never 403).
2. `modules/leave/services/requests.py`:
   - `apply_for_leave(...)`: Atomic creation with validation (`BR-EL-001`..`015`). Checks category eligibility, holiday/RH calendar, balance sufficiency, non-overlap (`BR-EL-012`), and substitute eligibility. Deducts provisional balance.
   - `respond_substitute(...)`: Records substitute `Accept` or `Decline`. On accept, releases routing gate to Unit Head (or Director). On decline, sets `APPLICANT_ACTION_REQUIRED`.
   - `nominate_replacement_substitute(...)`: Implements `EL-UC-019`.
   - `transition(...)`: Transactional choke point taking `select_for_update()`, validating against `state_machine.py`, creating `LeaveRequestTransition`, and deducting or restoring ledger balance.
   - `withdraw_request(...)`: Immediate cancellation of pending requests (`BR-EL-022`, `BR-EL-034`), restoring provisional balance deductions.
3. `modules/leave/services/actions.py`:
   - `request_cancellation(...)`: Validates pre-start condition (`BR-EL-023`). On approval, restores deducted balance and marks `CANCELLED`.
   - `request_extension(...)`: Validates ongoing leave, calculates incremental days (`BR-EL-025`).
   - `submit_resumption(...)` & `review_resumption(...)`: Implements `EL-UC-010/011` and `BR-EL-028` (adjusts balance on early/late return).
   - `sync_offline_leave(...)`: Retrospective sync with sanction evidence, bypassing approval routing (`BR-EL-029`).

---

### STAGE 4: REGISTRY, API, CONTRACTS & URLS
1. `modules/leave/registry.py`:
   - `MODULE`: `code = "leave"`, `label = "Employee Leave"`, `icon = "Calendar"`, `base_path = "/leave"`, `nav_section = "Services"`, `sort_order = 20`, `status = "active"`.
   - `NAV_ITEMS`:
     - Apply Leave: `to = "/leave/apply"`, `required_permission = "leave.request.create"`
     - My Leaves: `to = "/leave/my-leaves"`, `required_permission = "leave.request.view_self"`
     - Substitute Requests: `to = "/leave/substitute"`, `required_permission = "leave.substitute.respond"`
     - Approvals: `to = "/leave/approvals"`, `required_permission = "leave.request.approve"`
     - Resumptions: `to = "/leave/resumptions"`, `required_permission = "leave.resumption.review"`
     - Leave Admin: `to = "/leave/admin"`, `required_permission = "leave.admin.manage"`
   - `PERMISSIONS`: Tuple of `(code, label)` for:
     `"leave.request.create"`, `"leave.request.view_self"`, `"leave.request.view"`, `"leave.substitute.respond"`, `"leave.request.approve"`, `"leave.cancellation.request"`, `"leave.extension.request"`, `"leave.resumption.submit"`, `"leave.resumption.review"`, `"leave.admin.manage"`, `"leave.offline.record"`.
   - `SYSTEM_PERMISSIONS`: `["leave.system.year_end", "leave.system.sla_sweep"]`.
   - `ROLE_GRANTS`: Map ERP designations (`faculty`, `staff`, `Unit Head`, `Dean`, `Registrar`, `Director`, `Leave Administrator`) to appropriate permissions.
2. `modules/leave/contracts.py`:
   - Plural getters only (`ops/checks/contracts_are_plural.py` enforced):
     - `get_active_leaves(user_ids: Sequence[int]) -> dict[int, list]`
     - `get_leave_balances(user_ids: Sequence[int]) -> dict[int, dict]`
3. `modules/leave/api/`:
   - `serializers.py`: Serializers for LeaveRequest, LeaveBalance, Transition, Resumption, and OfflineRecord.
   - `views.py`: DRF APIViews/Generics guarded by `HasModuleGrant("leave")` and `HasPermission(...)`. Use permission literal strings so `permission_manifest` scan finds them!
   - `urls.py`: URL patterns under `api/v1/leave/`.
4. Integration in `config/urls.py`:
   - Add `path("api/v1/leave/", include("modules.leave.api.urls"))`.
5. Integration in `.importlinter`:
   - Add `modules.leave` to `modules-only-touch-contracts` and `domain-is-pure-python`.

---

### STAGE 5: CELERY SCHEDULE & TASKS
1. `modules/leave/schedule.py`:
   - Define `BEAT_SCHEDULE`:
     - `leave.sla-sweep`: Hourly SLA reminder and escalation check (`EL-UC-021`).
     - `leave.year-end-process`: Year-end conversion and lapse run (`EL-UC-020`).
   - Define `TASK_ROUTES`: `{"leave.*": {"queue": "default"}}`.
2. `modules/leave/tasks.py`:
   - Implement tasks calling services with pending-only guards (`BR-EL-032`, `BR-EL-033`).
3. In `config/celery.py`:
   - Import and merge `LEAVE_SCHEDULE` and `LEAVE_ROUTES`.

---

### STAGE 6: FRONTEND CLIENT INTEGRATION (`client/src/modules/leave/`)
1. Create `client/src/modules/leave/api/types.ts` and `api/hooks.ts` with TanStack Query hooks using shared `client/src/lib/http.ts`.
2. Create React page components in `client/src/modules/leave/pages/`:
   - `ApplyLeavePage.tsx`: Form with half-day toggle, substitute selector, station leave fields.
   - `MyLeavesPage.tsx`: Balances overview, history table, withdraw and cancel buttons.
   - `SubstituteRequestsPage.tsx`: Accept/decline interface.
   - `ApprovalQueuePage.tsx`: Unit Head recommend/approve/reject interface.
   - `ResumptionPage.tsx`: Submit return date and reviewer adjustment interface.
   - `AdminLeavePage.tsx`: Calendar publishing and offline entry sync.
3. In `client/src/modules/leave/routes.tsx`:
   - Export `routes: RouteObject[]` matching exact `to` paths from `registry.NAV_ITEMS`.
4. In `client/src/app/registry.ts`:
   - Register `leave` in `MODULE_REGISTRY` with `basePath: "/leave"` and dynamic import.

---

### STAGE 7: AUTOMATED TESTS
Create unit tests mirroring `modules/placement/tests/`:
1. `modules/leave/tests/test_calculations.py`: Test continuous counting (EL/COL/VL), weekend exclusions (CL/SCL/RH), half-day deduction (0.5), and VL 2:1 conversion.
2. `modules/leave/tests/test_state_machine.py`: Assert that all legal transitions succeed and invalid transitions raise exceptions.
3. `modules/leave/tests/test_permissions.py`: Test endpoints using `stub_iam` and `make_principal` from `conftest.py`, asserting 403 on missing permissions and 404 on out-of-scope objects.

---

### STAGE 8: MECHANICAL VERIFICATION & FINAL HANDOFF
Run all platform mechanical integration checks and fix any reported errors:
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python ops/checks/no_cross_module_fk.py
python ops/checks/contracts_are_plural.py
python ops/checks/nav_matches_routes.py
python manage.py permission_manifest --check
pytest modules/leave/tests/ -q