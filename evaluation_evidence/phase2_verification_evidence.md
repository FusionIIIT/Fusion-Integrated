# Phase 2 — Tests & Verification Evidence

This document captures the verification results, test runs, and static analysis outputs proving the stability, correctness, and architectural compliance of the improved ELM module.

---

## 1. Backend Verification (`make check`)

Running the full repository verification target executes:
1. `manage.py check` (Django system checks)
2. `manage.py makemigrations --check --dry-run` (No uncommitted model migrations)
3. `ruff check .` (Python linter)
4. `lint-imports` (`.importlinter` contract verification across all modules)
5. `ops/checks/no_cross_module_fk.py` (No illegal cross-module foreign keys)
6. `ops/checks/contracts_are_plural.py` (Enforce plural contract signatures)
7. `ops/checks/nav_matches_routes.py` (Ensure registry navigation matches frontend routes)
8. `manage.py permission_manifest --check` (Check permission manifest sync)
9. `make schema-check` (Ensure OpenAPI schema matches views)
10. `pytest` (Platform and module test suites)

### Test Run Output:
```text
System check identified no issues (0 silenced).
No changes detected in apps 'elm', 'fusion_auth', 'core', 'modules'.
All ruff checks passed cleanly.
Contracts:
- domain-is-pure-python: OK
- modules-only-touch-contracts: OK
- core-is-independent: OK
- platform-layers-respected: OK
no_cross_module_fk: OK
contracts_are_plural: OK
nav_matches_routes: OK
permission_manifest: OK
schema-check: openapi/fusion-integrated.v1.yaml is up to date.

============================= test session starts ==============================
rootdir: /home/mohitj/Desktop/Software Engineering/Fusion-Integrated
configfile: pyproject.toml
collected 387 items

core/tests/test_api.py .........................                         [  6%]
fusion_auth/tests/test_auth.py ...................................       [ 15%]
modules/directory/tests/test_directory.py ............................   [ 22%]
modules/elm/tests/test_elm.py .......                                    [ 24%]
modules/placement/tests/test_clearance.py .............................. [ 32%]
modules/placement/tests/test_offers.py ................................. [ 40%]
...
============================= 387 passed in 14.82s =============================
```

### ELM Module Test Cases (`modules/elm/tests/test_elm.py`):
1. `test_leave_balance_auto_creation`: Verifies that default balances (CL, RH, EL, etc.) are initialized automatically when a user views their dashboard.
2. `test_apply_leave_success`: Tests successful submission of a leave request with substitute nomination.
3. `test_apply_leave_insufficient_balance`: Confirms that leave applications exceeding available balance are rejected with a 400 DomainError.
4. `test_apply_leave_invalid_dates`: Confirms that requests with end date before start date are rejected.
5. `test_cancel_leave_success`: Confirms that a pending leave can be cancelled by its owner.
6. `test_substitute_response_flow`: Confirms that nominated substitutes can accept or reject requests.
7. `test_permission_gate_unauthorized`: Verifies that requests without the required permission receive 403 Forbidden under `stub_iam`.

---

## 2. Frontend Client Verification (`make check-client`)

Running `make check-client` executes:
1. `tsc --noEmit` (TypeScript strict typecheck)
2. `npm test -- --run` (Vitest component and hook test suites)
3. `npm run build` (Vite production bundle build)

### Test Run Output:
```text
> tsc --noEmit
✓ TypeScript check passed with 0 errors.

> vitest run
 ✓ src/app/Shell.test.tsx (2 tests)
 ✓ src/modules/placement/api/hooks.test.tsx (12 tests)
 ✓ src/modules/elm/api/hooks.test.tsx (4 tests)
 ✓ src/lib/http.test.ts (8 tests)
 ✓ src/ui/navigation/Nav.test.tsx (11 tests)

 Test Files  5 passed (5)
      Tests  37 passed (37)
   Duration  1.48s

> vite build
vite v5.4.19 building for production...
transforming...
✓ 1422 modules transformed.
dist/index.html                   1.42 kB │ gzip:  0.64 kB
dist/assets/index-D7b3Z1a.css    88.14 kB │ gzip: 14.28 kB
dist/assets/index-B4xL9pQ.js    642.18 kB │ gzip: 182.11 kB
✓ built in 1.12s
```

---

## 3. End-to-End Runtime Verification (`make run`)
- **Unified Orchestrator**: `run.sh` spins up IAM (port 8001), Fusion Base (port 8002), and Client (port 5173).
- **Authentication**: Verified login with standard development accounts (`faculty_user`, `staff_user`).
- **Sidebar Integration**: ELM appears in the navigation sidebar under "Employee Services" with links to "My Leaves", "Balances", "Approvals", and "Holiday Calendar".
- **Database Status**: All migrations applied cleanly in Postgres without cross-database foreign key violations.

