# PROMPT: ELM Phase 2 — Review, Test and Improve the Leave Module (Fusion-Integrated)


---

You are working inside a Django 4 + DRF + React monorepo called **Fusion-Integrated** (a college
ERP). Your job is Assignment 6B Phase 2: take the existing AI-generated ELM (Employee Leave
Management) module, review it against the official specification, test it, fix what is wrong, and
make it runnable inside the Fusion base code.

## Repository layout (absolute paths)

- Repo root: `/home/atharva/Documents/Fusion/Fusion-Integrated` — all work happens HERE, nowhere else.
- The ELM module: `/home/atharva/Documents/Fusion/Fusion-Integrated/modules/leave/`
  - `domain/` — pure rule logic, no Django: `categories.py`, `eligibility.py`, `state_machine.py`, `guards.py`, `routing.py`
  - `services/` — transactions/orchestration: `applications.py`, `decisions.py`, `year_end.py`, `sla.py`, `calendar.py`, `workflow.py`, `accounts.py`, `notifications.py`, `offline.py`
  - `selectors/` — query/scoping: `leave.py`, `balances.py`
  - `api/` — `views.py`, `serializers.py` (**no `urls.py` yet**)
  - `models.py`, `registry.py`, `contracts.py`, `apps.py`
- A reference module that is fully wired and correct: `/home/atharva/Documents/Fusion/Fusion-Integrated/modules/placement/` (copy its patterns, especially `api/urls.py`, `migrations/`, `tests/`).
- Django wiring files:
  - `/home/atharva/Documents/Fusion/Fusion-Integrated/config/settings/base.py` (`DOMAIN_MODULES` list, line ~91)
  - `/home/atharva/Documents/Fusion/Fusion-Integrated/config/urls.py`
- Module authoring rules: `/home/atharva/Documents/Fusion/Fusion-Integrated/docs/03-platform/module-authoring-guide.md` and `platform-structure.md`
- ELM specification (plain-text extracts, read these):
  - `01_ELM_Problem_Statement_v1.4_FINAL.txt` — overview
  - `02_ELM_Functional_Requirement_Specification_v1.5_FINAL.txt` — FRs
  - `03_ELM_Use_Case_Specifications_v1.4_FINAL.txt` — use cases (EL-UC-xxx)
  - `04_ELM_Business_Rule_Specifications_v1.4_FINAL.txt` — business rules (BR-EL-xxx)
  - `06_ELM_Workflow_Specifications_v1.6_FINAL.txt` — workflows (CW-EL-xx)
  - `06_ELM_Traceability_Matrix_v1.5_FINAL.txt` — which BR/UC belongs to which FR

## Current state (verified)

The module code EXISTS and imports cleanly, but it is **not connected to the Django app**:

1. `modules.leave` is NOT in `INSTALLED_APPS` — `config/settings/base.py` `DOMAIN_MODULES` contains only `modules.placement`.
2. There is NO `modules/leave/api/urls.py`, and `config/urls.py` does NOT mount any `/api/v1/leave/` route.
3. There is NO `modules/leave/migrations/` directory, so none of the leave tables can be created.
4. There are NO tests: no `modules/leave/tests/`.
5. `modules/leave/registry.py` still has `"status": "planned"` and the module is ungranted, so no nav item is reachable.
6. There is no frontend under `client/src/modules/` for leave (only `placement` exists).

The HTTP layer already has views for every workflow — `ExtensionView` (CW-EL-03, ongoing-leave
extension) and `ResumptionView` / `ResumptionReviewView` (CW-EL-04) already exist in
`modules/leave/api/views.py`, backed by `services/applications.py::request_extension`,
`submit_resumption` and `services/decisions.py::review_resumption`. Do NOT rewrite them; wire and
verify them.

## Your task, in order

### Step 1 — Register the module
- Add `"modules.leave"` to `DOMAIN_MODULES` in `config/settings/base.py`.
- Mount it in `config/urls.py`: `path("api/v1/leave/", include("modules.leave.api.urls"))`,
  exactly like the placement/directory lines already there.
- Create `modules/leave/api/urls.py` following `modules/placement/api/urls.py` style, routing the
  views that already exist in `modules/leave/api/views.py`.
- Set `MODULE["status"]` in `modules/leave/registry.py` from `"planned"` to `"active"` only after
  everything below passes; read the registry docstring and `make permissions` first.

### Step 2 — Database
- Create `modules/leave/migrations/` (`__init__.py`) and run
  `python manage.py makemigrations leave`, then `make migrate`.
- Do NOT hand-write schema edits in `models.py` unless makemigrations demands it.

### Step 3 — Spec review (the core of the assignment)
Read `04_ELM_Business_Rule_Specifications_v1.4_FINAL.txt` and audit the domain layer against it.
Write failing tests FIRST in `modules/leave/tests/test_domain_rules.py`, then fix the code.
Rules that the traceability matrix ties to `modules/leave/domain/categories.py` and that MUST have
passing tests:
- **BR-EL-007** — unused VL converts to EL at **2 VL : 1 EL** (division, not multiplication), fractional days included. Function: `year_end_action()`.
- **BR-EL-011** — CL/SCL/RH count **duty days only**: both Saturday AND Sunday drop out of the count. Function: `weekend_dates()`.
- **BR-EL-012** — two CL halves on the same date do NOT overlap when they occupy different halves; two requests in the SAME half DO overlap. Function: `Interval.overlaps()`.
Also audit `domain/eligibility.py` against BR-EL-010 (message references) and the state machine in
`domain/state_machine.py` against `06_ELM_Workflow_Specifications_v1.6_FINAL.txt` (EL-UC-001..011,
CW-EL-02/03/04 transitions). Every fix must cite the BR/UC number in the commit message or test
docstring.

### Step 4 — Service/API tests
- Add `modules/leave/tests/test_api.py` covering: apply → review → route → approve happy path,
  an unauthorized user getting 404 (selector scoping, never 403), extension of an ongoing leave
  (CW-EL-03), and resumption submit + review (CW-EL-04).
- Follow `modules/placement/tests/test_api.py` for fixtures/primitives.

### Step 5 — Verify everything CI runs
Run and make ALL of these pass, in this order:
```
make check          # manage.py check, makemigrations --check, ruff, lint-imports,
                    # no_cross_module_fk, contracts_are_plural, nav_matches_routes,
                    # permission_manifest --check, openapi schema-check, pytest
make check-client   # only if you touched client/
```
If `permission_manifest --check` or `nav_matches_routes` fail, fix `modules/leave/registry.py`
(nav items must correspond to real routes; permissions must be granted to some designation).

## Constraints (do not violate)

- Django + DRF only. Do NOT create any FastAPI/SQLAlchemy code, do NOT create
  `backend/leave_management/`, do NOT add `fastapi` or `sqlalchemy` to `requirements.txt`.
- No hardcoded credentials (`admin123` or similar), no in-memory mock databases, no
  `password == ...` checks — auth comes from the existing `fusion_auth` principal, and views use
  `HasModuleGrant("leave")` / `HasPermission(...)` as `modules/leave/api/views.py` already does.
- Keep the existing layering: views parse/scope/delegate → services own transactions → selectors
  scope querysets → domain is pure functions with no Django imports.
- No cross-module foreign keys (ADR-0013); cross-module reads go through `contracts.py`.
- Do NOT replace or delete the existing module; improve it in place.
- Do NOT touch anything outside `modules/leave/`, `config/settings/base.py`, `config/urls.py`,
  and (if needed) `client/src/modules/leave/`.

## Deliverables when you are done

1. The list of spec violations found, each citing its BR/UC number, the file:line, and the fix.
2. `make check` output ending in success.
3. A short summary of what a reviewer should manually test in the running app
   (`make up && make migrate && make seed && make dev`, then sign in and open Leave from the sidebar).
