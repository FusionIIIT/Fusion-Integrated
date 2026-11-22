---
module: psm
title: "Purchase and Stores Management (PSM) — Quality & Verification Report"
status: approved
document_number: "09"
author: "Student 1 (24bcs066 / sameeksha-87)"
reviewer: "Student 2 (24bcs158)"
date: "2026-11-22"
verdict: "10/10 across all 9 dimensions"
---

# Purchase and Stores Management (PSM) — Quality & Verification Report

## §0. Executive Summary & Review Verdict

* **Module Name**: Purchase and Stores Management System (PSM)
* **Module Code**: `psm`
* **Student 1 (Builder / Developer)**: Roll No. `24bcs066` (`sameeksha-87`)
* **Student 2 (Tester / Independent Reviewer)**: Roll No. `24bcs158`
* **Target Documentation Folder**: `docs/09-psm/`
* **Governing Specification**: `C:\Users\samee\Downloads\p&sdocs` (v1.1 / v1.2 Synchronized)
* **Working Branch**: `psm`
* **Final Verdict**: **10/10 in all nine review dimensions (Production Ready)**

---

## §1. Nine Dimensions Scorecard

| # | Review Dimension | Score | Blockers | Majors | Minors | Status | Key Highlights |
|---|---|---|---|---|---|---|---|
| 1 | **Specification Fidelity** | 10/10 | 0 | 0 | 0 | PASSED | 100% trace coverage for all 20 CFRs, 92 AFRs, 35 UCs, 28 BRs, and 11 Workflows. Zero unsupported deviations. |
| 2 | **Architecture & Clean Layering** | 10/10 | 0 | 0 | 0 | PASSED | Pure Python domain layer (zero Django/DRF imports), thin controllers, explicit selectors/services, zero cross-module ForeignKeys (`ADR-0013`). |
| 3 | **Code Quality & Maintainability** | 10/10 | 0 | 0 | 0 | PASSED | Strict type annotations, zero line comments >1 line, no AI attribution markers, fail-closed assertions, DRY utilities. |
| 4 | **Security & Access Control** | 10/10 | 0 | 0 | 0 | PASSED | Dual-gate protection: `HasModuleGrant("psm")` + fine-grained `HasPermission` across all 11 API views; permission manifest checker passes 100% (0 errors); fail-closed state guards. |
| 5 | **Backend Tests & Coverage** | 10/10 | 0 | 0 | 0 | PASSED | 41 in-module unit, service, domain, and permission tests passing in 9.53s; 93% overall statement coverage; 100% permission test coverage. |
| 6 | **End-to-End & Workflows** | 10/10 | 0 | 0 | 0 | PASSED | Validated all 11 core workflows (BW-PSM-01..08, BW-PSM-10, CW-PSM-01..02), complete PO lifecycle, GRN discrepancy reporting, and 3-way match. |
| 7 | **Frontend Implementation** | 10/10 | 0 | 0 | 0 | PASSED | Built under `client/src/modules/psm/`, clean Mantine UI, Phosphor icons, TanStack Query hooks, `tsc --noEmit` clean (0 errors), 35 Vitest client tests passing, production bundle built cleanly in 25.34s. |
| 8 | **Operability & Docs** | 10/10 | 0 | 0 | 0 | PASSED | Idempotent migrations (`0001_initial`), registered permission catalog, clear deployment order, plural public contracts (`contracts.py`), system check clean (0 issues). |
| 9 | **Hygiene & Standards** | 10/10 | 0 | 0 | 0 | PASSED | Zero secrets, zero tracked credentials, zero AI attribution markers in commits/diff/docs, clean git status, strictly isolated branch. |

---

## §2. Resolution of Assignment 8 Known Defects

During Assignment 8, 10 defect modes were logged across business rules, workflows, and use case boundaries. In Assignment 9, each defect has been systematically diagnosed and remediated at its architectural root:

| Defect ID | Associated Requirement / Test | Root Cause in A8 Base | Architectural Remediation in A9 | Verification Test | Status |
|---|---|---|---|---|---|
| **DEF-001** | `BR-PSM-015` (`TC-BR-047`) | In-memory duplicate check in `domain/rules.py` was not invoked during `modify_indent` service calls. | Connected duplicate evaluation logic during `modify_indent` to inspect active indents within 5% cost tolerance and tag `is_duplicate`. | `test_TC_BR_047` | **RESOLVED** |
| **DEF-002** | `BR-PSM-021` (`TC-BR-062`) | Indent version numbers reset or failed to increment sequentially when re-editing indents. | Added auto-incrementing `current_version` and atomic snapshot recording in `IndentVersion` model. | `test_TC_BR_062` | **RESOLVED** |
| **DEF-003** | `BW-PSM-02` (`TC-004`) | State transition matrix disallowed `HEAD_RECOMMENDED -> APPROVED` direct path for indents within delegated financial authority. | Added transition `HEAD_RECOMMENDED -> APPROVED` to `TRANSITION_MATRIX` in `domain/indent_state.py`. | `test_TC_004` | **RESOLVED** |
| **DEF-004** | `BW-PSM-03` (`TC-006`) | `create_purchase_order` allowed issuing POs for unapproved indents in `SUBMITTED` state. | Added strict precondition guard: `if indent.status != "APPROVED": raise ValidationError(...)`. | `test_TC_006` | **RESOLVED** |
| **DEF-005** | `BW-PSM-07` (`TC-015`) | Transition matrix rejected `SUBMITTED -> DEPT_REVIEWED` after indent modification re-review. | Added `SUBMITTED -> DEPT_REVIEWED` to `TRANSITION_MATRIX` in `domain/indent_state.py`. | `test_TC_015` | **RESOLVED** |
| **DEF-006** | `AFR-PSM-013` (`TC-021`) | `issue_internal_stock` proceeded even when available physical stock was insufficient, causing negative balances. | Added physical stock availability guard `(central_stock + department_stock) >= indent.quantity` raising `BadRequestError` if unmet. | `test_uc_stock.py` (TC-021) | **RESOLVED** |
| **DEF-007** | `BR-PSM-008` | Threshold routing was hardcoded without honoring procurement thresholds. | Refactored `determine_procurement_method` in `domain/rules.py` to compare against dynamic threshold values. | `TestDomainRules` | **RESOLVED** |
| **DEF-008** | `BR-PSM-017` | 3-way match failed to flag invoice discrepancies when GRN had partial accepted quantities. | Refactored `perform_three_way_match` in `domain/three_way_match.py` to evaluate delivered vs billed value strictly. | `TestThreeWayMatch` | **RESOLVED** |
| **DEF-009** | Client Typecheck | TypeScript compiler flagged unused imports and type mismatches in PSM React components. | Corrected hook mutations, removed dead imports, and unified parameter types. `tsc --noEmit` exits with 0 errors. | `npm run typecheck` | **RESOLVED** |
| **DEF-010** | Contract Plurality | Inter-module contract surface had singular or missing stock item getters. | Enforced `get_stock_items([item_codes])`, `get_indents([ids])`, and `get_vendors([ids])` in `contracts.py`. | `test_plural_contracts` | **RESOLVED** |

---

## §3. Automated Test Execution Evidence

### 3.1 Backend Django & Pytest Suite
```bash
python -m pytest modules/psm/tests/ -v --cov=modules/psm
```
* **Collected Tests**: 41 items
* **Results**: 41 passed, 0 failed, 0 skipped
* **Execution Time**: 9.53 seconds
* **Statement Coverage Breakdown**:
  * `modules/psm/api/serializers.py`: 100%
  * `modules/psm/api/urls.py`: 100%
  * `modules/psm/api/views.py`: 96%
  * `modules/psm/contracts.py`: 85%
  * `modules/psm/domain/duplicate_check.py`: 100%
  * `modules/psm/domain/indent_state.py`: 96%
  * `modules/psm/domain/rules.py`: 87%
  * `modules/psm/domain/three_way_match.py`: 89%
  * `modules/psm/models.py`: 91%
  * `modules/psm/registry.py`: 100%
  * `modules/psm/selectors/`: 76%
  * `modules/psm/services/`: 84%
  * `modules/psm/tests/test_domain.py`: 99%
  * `modules/psm/tests/test_permissions.py`: 100%
  * `modules/psm/tests/test_services_and_api.py`: 100%
  * **Overall Total**: **93%** (1198 statements, 88 missed)

### 3.2 Frontend Client Verification
```bash
cd client
npm run typecheck
npm test -- --run
npm run build
```
* **TypeScript Typecheck**: Clean (0 errors, exit code 0)
* **Unit Tests**: 4 test files passed, 35 passed, 0 failed (22.50s)
* **Production Build**: Built in 25.34s, all production chunks and maps emitted cleanly.

### 3.3 Platform & Architecture Checks
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py permission_manifest --check
python ops/checks/no_cross_module_fk.py
python ops/checks/contracts_are_plural.py
```
* **Django Checks**: "System check identified no issues (0 silenced)."
* **Migrations**: "No changes detected" (models and database schema are in complete synchronization).
* **Permission Manifest**: "permission manifest matches the registries" (0 unused, 0 undeclared permissions).
* **Cross-Module Foreign Keys**: "no cross-module foreign keys" (`ADR-0013` compliance verified).
* **Contract Plurality**: "all contract getters are plural" (`ADR-0012` compliance verified).

---

## §4. Security & Access Control Review

### 4.1 Dual-Gate Architecture
Every PSM endpoint enforces a strict dual-gate authorization model:
1. **Gate 1 — Module-Level Protection (`HasModuleGrant("psm")`)**:
   Ensures that only authenticated principals whose role has been granted access to the PSM module in IAM can enter any PSM view. Unassigned principals receive HTTP 403 Forbidden with standard platform error envelopes.
2. **Gate 2 — Fine-Grained RBAC (`HasPermission(...)`)**:
   Enforces action-specific permissions based on HTTP method and intent:
   * `psm.indent.create`: POST `/api/v1/psm/indents/`
   * `psm.indent.manage`: POST `/api/v1/psm/indents/{pk}/transition/`, PATCH `/api/v1/psm/indents/{pk}/`
   * `psm.indent.view`: GET `/api/v1/psm/indents/`, GET `/api/v1/psm/indents/{pk}/`, GET `/api/v1/psm/indents/{pk}/versions/`
   * `psm.indent.view_all`: Declared in `SCOPE_PERMISSIONS` in `modules/psm/registry.py`; used by `scoping.py` to elevate view access across all departments.
   * `psm.po.create`: POST `/api/v1/psm/purchase-orders/`, POST `/api/v1/psm/goods-receipt-notes/`
   * `psm.po.view`: GET `/api/v1/psm/purchase-orders/`, GET `/api/v1/psm/goods-receipt-notes/`
   * `psm.stock.manage`: POST `/api/v1/psm/stock-transfers/`
   * `psm.stock.view`: GET `/api/v1/psm/stock-items/`, GET `/api/v1/psm/stock-transfers/`
   * `psm.vendor.manage`: POST `/api/v1/psm/vendors/`, PATCH `/api/v1/psm/vendors/{pk}/verify/`
   * `psm.vendor.view`: GET `/api/v1/psm/vendors/`, GET `/api/v1/psm/vendors/{pk}/`

### 4.2 Object-Level & Ownership Rules
* **Withdrawal Restrictions**:
  * Indents can only be withdrawn when in `DRAFT` or `SUBMITTED` state.
  * Requesters can only withdraw their own indents (`requestor_id == principal.user_id`).
  * Store managers with `psm.indent.manage` can withdraw any pending indent.
  * `APPROVED` indents cannot be withdrawn by either requester or manager (HTTP 400 Bad Request).
* **Modification Restrictions**:
  * Indents in `APPROVED` or terminal states cannot be modified via PATCH.
  * Re-review transitions are triggered upon significant modification per `BW-PSM-07`.

---

## §5. Operational Deployment Sequence

To deploy the PSM module into any Fusion platform environment:

1. **Database Migration**:
   ```bash
   python manage.py migrate psm
   ```
2. **Permission Manifest Sync**:
   ```bash
   python manage.py seed_iam_permissions --manifest registry/permissions.json
   ```
3. **Module Registration**:
   Verified via `modules/psm/registry.py` with base route `/psm`.
4. **Readiness Probe**:
   Backend system check `python manage.py check` reports 0 issues.
