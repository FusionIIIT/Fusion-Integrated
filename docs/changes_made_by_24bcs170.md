# Changes Made by 24BCS170 - ELM Phase 2 Engineering Log

## 1. Student & Environment Configuration
- **Student Roll No**: 24BCS170
- **Partner Roll No**: 24BCS182
- **Repository**: `FusionIIIT/Fusion-Integrated`
- **Fork**: `https://github.com/nikhiljain10905/Fusion-Integrated`
- **Branch**: `elm-nikhiljain10905`
- **Inherited Baseline**: Phase 1 implementation (`pilot/ELM_MODEL_1`)
- **Local AI Coding Model**: `Qwen2.5-Coder:7b` (via Ollama / Continue IDE extension)
- **Testing & Verification**: `pytest`, `ruff`, `import-linter`, `ops/checks/no_cross_module_fk.py`, `ops/checks/contracts_are_plural.py`, `ops/checks/nav_matches_routes.py`, `manage.py permission_manifest --check`

---

## 2. Inherited Phase-1 Baseline Audit
Reviewing the Phase-1 code against the **ELM Specification Bundle v1.4** identified several key deficiencies:
1. **Incomplete Models**: `LeaveApplication` lacked the `reason` field, losing critical application context. Status choices were limited to basic states (`PENDING`, `APPROVED`, etc.) without multi-step workflow states (`AWAITING_SUBSTITUTE`, `AWAITING_APPROVAL`) specified in the Workflow specifications. `SubstituteNomination` lacked `status` (`PENDING`, `ACCEPTED`, `DECLINED`) and `decline_reason` for recording substitute consent (`BR-EL-015`).
2. **Missing Pure-Python Domain Validation**: No checks for leave balance sufficiency, date overlap (`BR-EL-012`), self-substitute nomination (`BR-EL-014`), or state machine transitions.
3. **Frontend Stubs**: Placeholder components lacked live API interaction, input validation, and proper error handling.
4. **Test Coverage**: No automated unit tests for domain business logic or API endpoints.

---

## 3. Engineering Improvements Made in Phase 2

### 1. Models & Workflow Schema Alignment (`modules/elm/models.py`)
- Added `reason` field (`models.TextField`) to `LeaveApplication`.
- Updated `STATUS_CHOICES` on `LeaveApplication` to support the full state lifecycle:
  - `AWAITING_SUBSTITUTE`, `AWAITING_APPROVAL`, `APPROVED`, `REJECTED`, `WITHDRAWN`, `CANCELLED`.
- Added `status` (`PENDING`, `ACCEPTED`, `DECLINED`) and `decline_reason` to `SubstituteNomination`.
- Ensured strict compliance with Fusion ADR-0013: no cross-module foreign keys (`applicant_id`, `employee_id`, and `substitute_id` are integer IDs).

### 2. Pure-Python Domain Rules (`modules/elm/domain/policy.py`)
- Implemented pure-Python domain rules without Django, DRF, or Celery imports (satisfying `import-linter`):
  - Defined `LeaveCode`, `LeaveEntitlement`, and `LEAVE_ENTITLEMENTS` for all 6 leave types (CL, RH, SCL, EL, VL, COL).
  - Implemented `requested_days` calculation with date order validation.
  - Implemented `validate_substitute_eligibility` preventing self-nomination (`BR-EL-014`).
  - Implemented `check_date_overlap` preventing overlapping leave periods (`BR-EL-012`).
  - Implemented `validate_balance_sufficiency` preventing overdrafts.
  - Implemented `is_valid_transition` enforcing valid workflow transitions.

### 3. Service Layer (`modules/elm/services/applications.py`)
- Implemented transactional services (`@transaction.atomic`):
  - `submit_leave_application`: validates balance sufficiency and overlap checks prior to creation.
  - `nominate_substitute`: creates nomination and transitions status to `AWAITING_SUBSTITUTE`.
  - `respond_substitute_nomination`: handles accept/decline consent flow (`BR-EL-015`).
  - `review_leave_application`: atomic approval with `select_for_update()` balance deduction; handles rejection.
  - `withdraw_application`: validates transition and moves application to `WITHDRAWN` (`BR-EL-022`).
  - `get_employee_balances`: queries employee balances.

### 4. Cross-Module Contract (`modules/elm/contracts.py`)
- Implemented `get_active_leaves_for_employees(employee_ids: Sequence[int])` taking a sequence of IDs to enforce plural contracts and eliminate N+1 queries per repo architectural rules.

### 5. REST API Layer (`modules/elm/api/`)
- Created serializers for applications, balances, nominations, reviews, and responses.
- Implemented DRF API views with `@extend_schema` OpenAPI metadata and RBAC permission guards (`HasModuleGrant("elm")`, `HasPermission(...)`).
- Wired URL patterns in `modules/elm/api/urls.py` and connected them to the root URLconf in `config/urls.py`.

### 6. Module Registration & RBAC (`modules/elm/registry.py`)
- Registered module manifest (`MODULE`), navigation items (`NAV_ITEMS`), permissions (`PERMISSIONS`), and role grants (`ROLE_GRANTS` for faculty and staff).
- Synchronized with `registry/permissions.json` and `docs/02-iam/permission-catalog.generated.md`.

### 7. Frontend Client (`client/src/modules/elm/`)
- Implemented `routes.tsx` with lazy loading for `balance`, `application`, and `history` routes.
- Registered the module in `client/src/app/registry.ts`.
- Built `LeaveBalance.tsx`, `LeaveApplication.tsx`, and `LeaveHistory.tsx` using Fusion's shared HTTP client and proper state management.
- Implemented cancellation/withdrawal UI in `LeaveHistory.tsx` for pending applications.

### 8. Automated Tests (`modules/elm/tests/`)
- Created pytest suite `test_policy.py` verifying:
  - Substitute eligibility (self-nomination rejection)
  - Date overlap detection (nested, partial, adjacent, disjoint intervals)
  - Balance sufficiency validation
  - State machine transition rules
  - Day count calculations and date order checks
- Created `test_api.py` testing unauthorized withdrawal, self-withdrawal, and 404 handling.

---

## 4. Verification Results
- `ops/checks/no_cross_module_fk.py`: PASSED (0 cross-module FKs).
- `ops/checks/contracts_are_plural.py`: PASSED (all contract getters are plural).
- `ops/checks/nav_matches_routes.py`: PASSED (sidebar nav items and client routes agree).
- `python manage.py permission_manifest --check`: PASSED (manifest matches registries).
- `lint-imports`: PASSED (all 4 contracts kept).
- `ruff check config core modules ops fusion_auth`: PASSED (all checks passed).
- `pytest modules/elm/tests/test_policy.py`: PASSED (100% tests passing).
