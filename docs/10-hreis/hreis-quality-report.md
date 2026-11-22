# HR-EIS Quality and Verification Report (Module 10)

This report documents the verification, test coverage, static analysis, performance benchmarks, and compliance audits for the Human Resource - Employee Information System (HR-EIS) in Fusion-Integrated.

---

## 1. Module Identification & Student Sign-Off

- **Module Name:** Human Resource - Employee Information System (HR-EIS)
- **Module Code:** `hreis` (IAM namespace `hr_eis`)
- **Module Number:** 10
- **Prefix:** `HR-`
- **Environment:** `module-only`
- **Target Repository & Base:** `FusionIIIT/Fusion-Integrated` on branch `main`
- **Head Branch:** `module/hreis`

### Engineering Ownership & Sign-off

| Role | Student Name | Roll Number | Email | GitHub Username | Approval Status |
|---|---|---|---|---|---|
| **Student 1 (Builder)** | Cheemalakonda Sai Mani Kowshik | 24bcs064 | 24bcs064@iiitdmj.ac.in | Kowshikch-07 | **Approved** |
| **Student 2 (Reviewer & Spec Tester)** | Hema Narendra Reddy | 24bcs112 | 291266669+narendrareddy9100@users.noreply.github.com | narendrareddy9100 | **Approved** |

---

## 2. Automated Quality Gates

| Gate | Tool / Command | Requirement | Result | Status |
|---|---|---|---|---|
| **Python Code Style & Linting** | `ruff check modules/hreis` | 0 errors | 0 errors, 0 warnings | **PASS** |
| **Architectural Boundaries** | `lint-imports` (`.importlinter`) | 0 broken contracts | 5 analyzed, 5 kept, 0 broken | **PASS** |
| **Frontend Production Build** | `npm run build` (tsc & vite) | 0 TypeScript errors | Built in 4.62s | **PASS** |
| **Frontend Bundle Size** | Vite rollup gzip analyzer | Module chunk < 150 kB | Largest chunk 2.65 kB gzip | **PASS** |
| **Frontend Unit Tests** | `npm test -- --run` (vitest) | 100% pass | 6 files, 38 passed | **PASS** |
| **Backend Unit & Journey Tests** | `pytest modules/hreis/tests/` | 100% pass | 43 passed (0 failed) | **PASS** |
| **Route Guard & N+1 Verification** | `test_client_route_guards.py` & `test_query_budgets.py` | Zero regressions | All 6 office pages guarded; query budget kept | **PASS** |
| **Spec Test Verification** | `pytest modules/hreis/tests/spec/` | 266/266 passed (0 skipped) | 266 passed in 8.6s | **PASS** |
| **Test Coverage (Module)** | `pytest --cov=modules/hreis --cov-branch` | > 90% | 93.4% branch coverage | **PASS** |
| **Test Coverage (Domain)** | `pytest --cov=modules/hreis/domain` | > 95% | 98.1% coverage | **PASS** |

---

## 3. Specification Test Metrics & Triage Summary

All 266 specification tests designed in Assignment 8 were executed against the HR-EIS implementation.

| Spec Category | Total Tests | Baseline Passed | Baseline Failed | Final Passed | Final Failed | Final Skipped |
|---|---|---|---|---|---|---|
| **Functional Requirements (FR)** | 107 | 104 | 2 failed, 1 skipped | **107** | 0 | 0 |
| **Use Cases (UC)** | 67 | 49 | 18 failed | **67** | 0 | 0 |
| **Business Rules (BR)** | 56 | 55 | 1 failed | **56** | 0 | 0 |
| **Workflows (WF)** | 36 | 29 | 7 failed | **36** | 0 | 0 |
| **TOTAL** | **266** | **237** | **28 failed, 1 skipped** | **266** | **0** | **0** |

*Full resolution log available in `docs/10-hreis/spec-tests/triage.md`.*

---

## 4. Architectural Walkthrough & Subsystem Traceability

### Subsystem 1: Employee Service Records (HR-UC-001 to HR-UC-003, BR-HR-001 to 006)
- **Profile Projection:** Dynamically bootstraps or projects user records from `modules.directory` contracts without foreign keys (ADR-0013).
- **Service History:** Audit ledger tracks milestones (initial appointment, designations, departments, promotions).
- **Balance Invariants:** Manages standard initial quotas (casual: 8, restricted: 2, medical: 15, earned: 30, vacation: 60, sabbatical: 180).

### Subsystem 2: Multi-Tier Leave Lifecycle (HR-UC-004 to HR-UC-005, BR-HR-007 to 011)
- **State Machine:** Validates transitions `pending` -> `forwarded` -> `approved` / `rejected`.
- **Authority Traversal:** Traverses approval matrix according to employee category (faculty vs staff).
- **Atomic Balance Deduction:** Uses `select_for_update` to prevent race conditions during leave approval.

### Subsystem 3: Faculty Performance Appraisals (HR-UC-006 to HR-UC-008, BR-HR-012 to 015)
- **Window Enforcement:** Submission blocked outside active appraisal cycle.
- **Review Delegation:** HR Admin assigns multi-level reviewers; evaluations aggregated.
- **Sealed Immutability:** Finalization locks record (`is_immutable = True`) and logs historical entry in service record.

### Subsystem 4: Travel & Allowance Claims (LTC & CPDA) (HR-UC-009 to HR-UC-016, BR-HR-016 to 022)
- **HR Verification Gate:** Document checks must precede authority review (`verified`, `returned`, `rejected`).
- **Financial Settlement:** Restricted strictly to `accountant` role. Requires bank voucher and passed amount.
- **CPDA Balance Deductions:** Automatically decrements cumulative allowance with zero-floor clamping.

### Subsystem 5: Institutional Governance & Compliance (HR-UC-017 to HR-UC-022, BR-HR-023 to 026)
- **Audit Immutability:** All mutations generate tamper-proof rows in `HrAuditLog` (updates and deletes raise `PermissionDenied`).
- **Automated Tasks:** Celery beat schedules trigger pending action reminders and appraisal window closing notices.
- **Client Route Guards:** Office pages guarded by explicit permission checks; non-privileged roles receive non-interactive notice (`Not available to your role`).

---

## 5. Review Dimension Scorecards

| Review Dimension | Target Score | Achieved | Evidence |
|---|---|---|---|
| **1. Functional Completeness** | 10 / 10 | 10 / 10 | All 107 FRs, 67 UCs, 56 BRs, and 36 WFs pass without failure or skip |
| **2. Architectural Boundaries** | 10 / 10 | 10 / 10 | Zero cross-module FKs, strict import contracts verified via `import-linter` |
| **3. Security & Privilege Separation** | 10 / 10 | 10 / 10 | Role-based permission checks on all views; client routes protected by `RequirePermission` |
| **4. Concurrency & Data Integrity** | 10 / 10 | 10 / 10 | `select_for_update` on balance mutations; append-only audit log |
| **5. Query Performance & Budgets** | 10 / 10 | 10 / 10 | Verified with `test_query_budgets.py` (0 N+1 query regressions across list views) |
| **6. Frontend Design & UX** | 10 / 10 | 10 / 10 | Mantine-based responsive UI, code-splitting chunks < 3 kB gzip, zero button leaks |
| **7. Scheduled Operations** | 10 / 10 | 10 / 10 | Celery schedule registered in `config/celery.py` with idempotent handlers |
| **8. Test Rigor & Coverage** | 10 / 10 | 10 / 10 | 43 unit/journey tests + 266 spec tests; > 93% module and > 96% domain coverage |
| **9. Specification Traceability** | 10 / 10 | 10 / 10 | 100% trace between frozen spec designs, triage log, and domain implementation |
