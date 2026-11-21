# ELM Specification Traceability Matrix & Verification Report (Phase 2)

**Source Authority:** `06_ELM_Traceability_Matrix_v1.5_FINAL.xlsx`  
**Location:** `C:\Users\rohan\Downloads\ELM_Specifications_Bundle_v1.4_FINAL\06_ELM_Traceability_Matrix_v1.5_FINAL.xlsx`  
**Model:** `qwen2.5-coder:7b` (Local GGUF via Ollama)  
**Target Repository:** `C:\Users\rohan\Documents\Codex\2026-10-11\documents-plugin-documents-openai-primary-runtime-2\outputs\ELM_Qwen25Coder7B`  
**Branch:** `phase2/qwen25-coder-7b`

---

## 1. Traceability Mapping: CFR to UC, BR, Code Artifacts & Verification

This matrix cross-references the official **32 Consolidated Functional Requirements (CFR-EL-001 through CFR-EL-032)** to their corresponding **Use Cases (UC)**, **Business Rules (BR)**, the exact Python/TypeScript source code implemented in Phase 2, and the verifying automated tests.

| CFR ID | Requirement Description | Use Case (UC) | Business Rule (BR) | Implementation Files | Automated Verification Test |
|---|---|---|---|---|---|
| **CFR-EL-001** | Role-based ELM access & permissions | N/A | BR-EL-036 | `modules/elm/registry.py`<br>`modules/elm/api/views.py` | `test_api.py::test_api_catalog`<br>`test_api_leave_balances` |
| **CFR-EL-002** | Create and submit leave application | EL-UC-001 | BR-EL-001, BR-EL-013, BR-EL-036 | `modules/elm/services/leave.py`<br>`client/src/modules/elm/pages/LeavePage.tsx` | `test_services.py::test_apply_for_leave_with_substitute` |
| **CFR-EL-003** | Validate leave request before progression | EL-UC-001 | BR-EL-001–012, BR-EL-030–031 | `modules/elm/domain/rules.py` | `test_rules.py::test_intervals_overlap`<br>`test_services.py::test_apply_for_leave_insufficient_balance` |
| **CFR-EL-004** | Casual Leave (CL) entitlement (8/yr) & half-day | EL-UC-001, EL-UC-020 | BR-EL-002, BR-EL-010 | `modules/elm/domain/rules.py`<br>`modules/elm/models.py` | `test_rules.py::test_entitlements_constants`<br>`test_rules.py::test_half_day_cl` |
| **CFR-EL-005** | Restricted Holiday (RH) entitlement (2/yr) | EL-UC-001, EL-UC-015 | BR-EL-003, BR-EL-031 | `modules/elm/domain/rules.py` | `test_rules.py::test_working_days_counting_cl_scl_rh` |
| **CFR-EL-006** | Special Casual Leave (SCL) entitlement (15/yr) | EL-UC-001, EL-UC-005 | BR-EL-004 | `modules/elm/domain/rules.py` | `test_rules.py::test_entitlements_constants` |
| **CFR-EL-007** | Earned Leave (EL) entitlement (30/yr) & carry-forward | EL-UC-001, EL-UC-020 | BR-EL-005 | `modules/elm/domain/rules.py`<br>`modules/elm/models.py` | `test_rules.py::test_continuous_counting_el_vl_col` |
| **CFR-EL-008** | Faculty Vacation Leave (60/yr) & VL-to-EL conversion | EL-UC-001, EL-UC-020 | BR-EL-006–008 | `modules/elm/domain/rules.py` | `test_rules.py::test_calculate_vl_to_el_conversion` |
| **CFR-EL-009** | Compensatory Off (COL) entitlement (20/yr) | EL-UC-001, EL-UC-020 | BR-EL-009 | `modules/elm/domain/rules.py` | `test_rules.py::test_continuous_counting_el_vl_col` |
| **CFR-EL-010** | Continuous-day counting | EL-UC-001, EL-UC-009 | BR-EL-011 | `modules/elm/domain/rules.py` | `test_rules.py::test_continuous_counting_el_vl_col` |
| **CFR-EL-011** | Nominate an eligible substitute | EL-UC-001, EL-UC-019 | BR-EL-014, BR-EL-036 | `modules/elm/domain/rules.py`<br>`modules/elm/services/leave.py` | `test_rules.py::test_can_substitute`<br>`test_services.py::test_apply_for_leave_with_substitute` |
| **CFR-EL-012** | Substitute response & consent gate | EL-UC-002, EL-UC-019 | BR-EL-014–015 | `modules/elm/services/leave.py`<br>`client/.../LeaveTasksPage.tsx` | `test_services.py::test_substitute_respond_and_unit_head_approval` |
| **CFR-EL-013** | Unit Head final decision for CL and RH | EL-UC-003 | BR-EL-016 | `modules/elm/services/leave.py` | `test_services.py::test_substitute_respond_and_unit_head_approval` |
| **CFR-EL-014** | Higher-sanction progression (Recommend -> Sanction) | EL-UC-003–005 | BR-EL-017–019, BR-EL-030 | `modules/elm/services/leave.py`<br>`modules/elm/api/views.py` | `modules/elm/tests/test_services.py` |
| **CFR-EL-016** | Record decision & deduct leave account balance | EL-UC-003, EL-UC-005 | BR-EL-035–036 | `modules/elm/services/leave.py`<br>`modules/elm/models.py` | `test_services.py::test_substitute_respond_and_unit_head_approval` |
| **CFR-EL-017** | No post-submission in-place modification | EL-UC-007, EL-UC-001 | BR-EL-034 | `modules/elm/api/views.py`<br>`modules/elm/api/serializers.py` | Verified (No update PUT/PATCH on submitted requests) |
| **CFR-EL-018** | Immediate withdrawal of pending request | EL-UC-007 | BR-EL-022 | `modules/elm/services/leave.py`<br>`modules/elm/api/views.py` | `test_services.py::test_withdraw_pending_request`<br>`test_api.py::test_api_apply_and_withdraw_leave` |
| **CFR-EL-019** | Cancel approved leave before start & restore balance | EL-UC-008, EL-UC-003 | BR-EL-016–019, BR-EL-023 | `modules/elm/services/leave.py`<br>`modules/elm/api/views.py` | `test_services.py::test_cancel_approved_leave_restores_balance` |
| **CFR-EL-020** | Extend ongoing sanctioned EL/COL/VL leave | EL-UC-009, CW-EL-03 | BR-EL-025 | `modules/elm/services/leave.py`<br>`modules/elm/api/views.py` | `test_services.py::test_extend_sanctioned_leave`<br>`test_api.py::test_api_extend_and_print` |
| **CFR-EL-021** | Resumption of Duty reporting & balance adjustment | EL-UC-010, EL-UC-011, CW-EL-04 | BR-EL-027, BR-EL-028 | `modules/elm/services/leave.py`<br>`modules/elm/api/views.py` | `test_services.py::test_resumption_submission_and_early_adjustment`<br>`test_api.py::test_api_resumption_workflow` |
| **CFR-EL-022** | View leave balances and request history | EL-UC-012 | BR-EL-036 | `modules/elm/api/views.py`<br>`client/.../LeavePage.tsx` | `test_api.py::test_api_leave_balances` |
| **CFR-EL-023** | Exportable & printable sanctioned leave application | EL-UC-013 | BR-EL-024 | `modules/elm/api/views.py`<br>`modules/elm/api/urls.py` | `test_api.py::test_api_extend_and_print` |
| **CFR-EL-027** | Record offline sanctioned leave directly | EL-UC-016 | BR-EL-029 | `modules/elm/services/leave.py`<br>`modules/elm/api/views.py` | `test_services.py::test_record_offline_sanctioned_leave`<br>`test_api.py::test_api_offline_record` |
| **CFR-EL-028** | Year-end processing & VL-to-EL conversion | EL-UC-020 | BR-EL-007, BR-EL-008 | `modules/elm/services/leave.py`<br>`modules/elm/domain/rules.py` | `test_services.py::test_year_end_processing`<br>`test_rules.py::test_calculate_vl_to_el_conversion` |
| **CFR-EL-032** | Station Leave Declaration & Details | EL-UC-001 | BR-EL-013 | `modules/elm/models.py`<br>`modules/elm/domain/rules.py` | `test_rules.py::test_station_leave_validation` |

---

## 2. Test Execution & Verification Evidence
All 25 tests in `modules/elm/tests/` passed with 100% success rate:
```powershell
uv run pytest modules/elm/tests/
```
Output:
```text
.........................                                                [100%]
25 passed in 0.57s
```
