# Phase 2 — Human-AI Interaction & Prompt Log
**Module**: Employee Leave Management (ELM)  
**Base Repository**: Fusion-Integrated  
**Initial Inherited Implementation**: Qwen 2.5 Coder 7B (Branch `elm/llm-qwen2.5-coder`)  
**Target Branch**: `feat/elm-phase2`

---

## Session Overview & Workflow Progression
The improvement of the inherited Phase-1 ELM implementation was conducted across multiple stages:
1. **Understand & Diagnose**: Inspecting code structure, diagnosing architecture violations, identity model mismatches, and build failures.
2. **Data Layer Alignment**: Refactoring data models from illegal multi-database ForeignKeys to `core.db.mixins.UserScopedModel` and regenerating migrations.
3. **Services & Scoping**: Implementing domain services (`apply_leave`, `cancel_leave`, `review_leave`, `respond_to_substitute_request`), queryset scoping, and serializer contracts.
4. **IAM & RBAC Seeding**: Creating `modules/elm/registry.py` and automating permission seeding into `Fusion_System_Administrator`.
5. **Frontend UI Rebuild**: Rebuilding raw HTML tables into modern Mantine UI components with React Query hooks.
6. **Unified Dev Orchestration**: Writing `run.sh` / `make run` to automate local multi-service development and fix port 8001 / 8002 environment collisions.
7. **Testing & Quality Assurance**: Adding unit and integration tests passing `make check` and `make check-client`.

---

## Key Interaction Transcripts

### Interaction 1: Architecture & Model Diagnosis
**Prompt**:
> "Can you inspect the inherited ELM implementation in modules/elm and evaluate whether it adheres to Fusion ERP architecture rules and the assignment specification?"

**Diagnosis / Response**:
The initial Phase-1 implementation contained multiple critical architectural violations:
1. Identity: The models used `models.ForeignKey(Principal)` and `models.ForeignKey(User)`. In Fusion, identity is owned by an external IAM database. Modules must use integer `user_id` via `core.db.mixins.UserScopedModel`.
2. Boundaries: `modules.elm` was not declared in `.importlinter`, and views imported models directly without service/selector separation.
3. Permissions: The module had no `registry.py` with `NAV_ITEMS`, `PERMISSIONS`, and `ROLE_GRANTS`, meaning it could never be granted to institute roles or appear in the server-driven sidebar navigation.
4. Frontend: The client used raw HTML tables (`<table>`, `<tr>`) and non-functional forms instead of Mantine UI components.

---

### Interaction 2: Model & Migration Refactoring
**Prompt**:
> "Align the ELM data models, migrations, and import contracts with Fusion architecture rules using UserScopedModel and integer user_id."

**Changes Applied**:
- Updated `LeaveBalance`, `LeaveApplication`, and `SubstituteRequest` to inherit from `UserScopedModel` and `TimeStampedModel`.
- Configured `.importlinter` contracts for `modules.elm`.
- Created clean migration `modules/elm/migrations/0001_initial.py`.

---

### Interaction 3: Backend Services, Registry, and Tests
**Prompt**:
> "Implement the services layer, selectors, permission-gated DRF views with drf-spectacular annotations, and pytest test suite for ELM."

**Changes Applied**:
- Created `modules/elm/services.py` with transactional balance verification, application submissions, cancellations, and substitute approvals.
- Created `modules/elm/selectors.py` for user-scoped reads.
- Created `modules/elm/registry.py` with permissions and role grants for faculty and staff.
- Added pytest test suite in `modules/elm/tests/test_elm.py` using `stub_iam`.
- Regenerated OpenAPI schema and permission manifest (`registry/permissions.json`).

---

### Interaction 4: Mantine Frontend Rebuild
**Prompt**:
> "Rebuild the ELM frontend components using Mantine UI (@mantine/core, @tabler/icons-react), TanStack Query hooks, and client registry integration."

**Changes Applied**:
- Created typed API hooks in `client/src/modules/elm/api/hooks.ts` with error handling and React Query mutations.
- Created Mantine UI pages: `MyLeavesPage.tsx`, `LeaveBalancesPage.tsx`, `LeaveApprovalsPage.tsx`, and `HolidayCalendarPage.tsx`.
- Registered routes in `client/src/modules/elm/routes.tsx` and mounted in `client/src/app/registry.ts`.
- Added Vitest test in `client/src/modules/elm/api/hooks.test.tsx`.

---

### Interaction 5: Multi-Service Runner & IAM Debugging
**Prompt**:
> "can you make a single command to run this system ?
> Currently I have to do all these things:
> Terminal 1: runserver 127.0.0.1:8001
> Terminal 2: make dev (port 8002)
> Terminal 3: cd client && npm run dev (port 5173)"

**Diagnosis & Fix**:
Running the three services revealed two critical runtime bugs:
1. `ModuleNotFoundError: No module named 'config'`: The `Makefile` exported `DJANGO_SETTINGS_MODULE` which leaked into the IAM backend. Fixed by isolating subshells and explicitly exporting `DJANGO_SETTINGS_MODULE="backend.settings"` for IAM.
2. `Identity service unavailable / Connection refused on port 8001`: An ambient `DEBUG=release` environment variable caused Django to enforce HTTPS redirection. Fixed by setting `DEBUG="True"` and `SECURE_SSL_REDIRECT="False"` for local development and adding a readiness polling loop.

---

### Interaction 6: RBAC Role Grants for Faculty and Staff
**Prompt**:
> "The backend and frontend are running, but the ELM module is still not showing up in the sidebar navigation for logged in faculty or staff accounts. How do we register and seed the IAM permissions?"

**Changes Applied**:
- Added `faculty` and `staff` role grants to `modules/elm/registry.py`.
- Automated IAM permission syncing via `manage.py seed_iam_permissions --manifest ../registry/permissions.json` inside `run.sh` so every startup auto-provisions permissions.

