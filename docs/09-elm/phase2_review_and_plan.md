# Fusion ERP Lab Assignment 6B — Phase 2: ELM Module Engineering Review & Improvement Plan

## 1. Executive Summary & Repository Verification

- **Phase 1 PR Source of Truth**: [PR #50: `FusionIIIT/Fusion-Integrated/pull/50`](https://github.com/FusionIIIT/Fusion-Integrated/pull/50)
- **Immutable Phase 1 Reference Branch**: `elm-local-ai` (Commit [`7263068`](file:///home/abhi/Documents/Fusion/Fusion-Integrated))
- **Phase 2 Working Branch**: `assignment6b/elm-review` (Branched directly from `elm-local-ai`)
- **Preservation of Existing Work**: All existing uncommitted WIP on `assignment6/elm` safely preserved in branch `backup/assignment6-leave-wip` and git stash. `elm-local-ai` is preserved without any alteration.
- **Specification Package Verification**: All six canonical specification documents located and verified in `/home/abhi/Documents/Fusion/ELM_Specifications`:
  1. `01_ELM_Problem_Statement_v1.4_FINAL.docx`
  2. `02_ELM_Functional_Requirement_Specification_v1.5_FINAL.xlsx` (32 CFRs, 128 AFRs, 107 historical SRS-EL crosswalk)
  3. `03_ELM_Use_Case_Specifications_v1.4_FINAL.docx` (21 Use Cases: 18 active actor-triggered, 2 active event-triggered, 1 retired)
  4. `04_ELM_Business_Rule_Specifications_v1.4_FINAL.docx` (36 active BRs, 2 retired)
  5. `06_ELM_Workflow_Specifications_v1.6_FINAL.docx` (17 Basis Workflows BW-EL-01..17, 4 Composite Workflows CW-EL-01..04, 1 Transition Pattern XTP-EL-01)
  6. `06_ELM_Traceability_Matrix_v1.5_FINAL.xlsx`

---

## 2. Local AI Model Connectivity & Diagnostic Report

| Component | Status | Diagnostic Finding & Action Taken |
|---|---|---|
| **Model Verification** | Verified | Ollama model `qwen2.5:7b` (Q4_K_M, 4.68 GB, digest `845dbda0ea48`) is present in `~/.ollama/models`. Confirmed that `qwen2.5-coder:7b` is NOT present locally; previous PR description mentioned it, but local evidence confirms `qwen2.5:7b`. |
| **Windows Ollama Service** | Resolved | Ollama was installed on Windows (`C:\Users\aabhi\AppData\Local\Programs\Ollama\ollama.exe`) but not running. Started `ollama serve` listening on `0.0.0.0:11434`. Confirmed responsive via `http://localhost:11434/api/tags`. |
| **WSL-to-Windows Connectivity** | Diagnosed & Resolved | WSL2 guest has its own network (`172.29.119.49`) and connects to Windows host via the default route gateway (`172.29.112.1`). Direct `curl localhost:11434` inside WSL failed because Windows Ollama was not in the WSL network namespace. Tested `curl http://172.29.112.1:11434/api/tags`, which successfully returned `qwen2.5:7b`. Created `ops/llm_query.py` with automatic host resolution. |
| **Model-Assisted Inference** | Operational | Queried `qwen2.5:7b` from WSL. Successfully diagnosed the `//` floor division defect in `convert_vl_to_el` and confirmed model-assisted review workflow. |

---

## 3. Phase 1 Implementation Review & Critical Defect Inventory

A thorough audit of `modules/elm/` and `client/src/modules/elm/` identified the following significant gaps and defects against the ELM specifications:

### Defect 1: Fractional VL-to-EL Conversion Truncated (BR-EL-007, AFR-EL-008.5)
- **Problem**: `convert_vl_to_el` in `policy.py` used integer floor division (`unavailed_vl // Decimal("2")`).
- **Impact**: Odd/fractional unavailed VL balances lost 0.5 days upon conversion (e.g., 15 VL became 7 EL instead of 7.5 EL), violating BR-EL-007.

### Defect 2: Approved Leave Cancellation Workflow Bypassed (BR-EL-023, CW-EL-02, BW-EL-10, BW-EL-11, EL-UC-008, AFR-EL-019.1..7)
- **Problem**: `cancel_approved` immediately marked the application as `CANCELLED` and restored the balance upon an employee's click, without any review or sanction.
- **Specification**: Pre-start cancellation must not edit the approved leave in place. It must create/route a cancellation request through the same hierarchy as the original leave:
  - CL/RH: Unit Head final decision (BW-EL-10).
  - SCL/EL/COL/VL: Unit Head review/recommendation followed by Sanctioning Authority final decision (BW-EL-11).
  - Approval marks leave `CANCELLED` and restores balance; rejection preserves `APPROVED` status with balance unchanged.

### Defect 3: Substitute Nomination, Consent Gate & Decline Recovery Gaps (BR-EL-014, BR-EL-015, EL-UC-002, EL-UC-019, CW-EL-01, BW-EL-02, BW-EL-03)
- **Problem**:
  1. Substitute validation only checked self-nomination, omitting employee existence and overlapping leave checks.
  2. Substitute decline left the request stranded in `AWAITING_SUB` instead of transitioning to `APPLICANT_ACTION_REQUIRED`.
  3. No service or endpoint existed to nominate a replacement substitute (EL-UC-019).
  4. Applicant withdrawal was not permitted from `APPLICANT_ACTION_REQUIRED`.

### Defect 4: Director Self-Sanction Prohibited (BR-EL-020, EL-UC-005, BW-EL-07..09, AFR-EL-015.1)
- **Problem**:
  1. `submit()` raised `ValidationError("Leave Unit Head is not configured")` for Director applicants who have no Unit Head.
  2. `decide()` raised `PermissionDenied("The applicant cannot decide their own leave")`, prohibiting the Director from self-sanctioning.
- **Specification**: Director applicants bypass Unit Head review and proceed directly to Director Self-Sanction (following substitute consent if applicable). The Director self-approves or self-rejects.

### Defect 5: Extension of Ongoing Leave Missing (BR-EL-025, CFR-EL-020, AFR-EL-020.1..7, EL-UC-009, CW-EL-03, BW-EL-12..14)
- **Problem**: Zero implementation of leave extensions.
- **Specification**: Employees on ongoing EL, COL, or VL may submit an extension request. Validated for additional days, balance, calendar rules, substitute consent gate, Unit Head review, and Sanction Authority approval. Approval posts only the incremental period; rejection preserves the base approved leave. Withdrawal permitted while pending.

### Defect 6: Resumption of Duty & Leave Adjustment Missing (BR-EL-027, BR-EL-028, CFR-EL-021, AFR-EL-021.1..10, EL-UC-010, EL-UC-011, CW-EL-04, BW-EL-15..17)
- **Problem**: Zero implementation of duty resumption submission and review.
- **Specification**: After returning from EL/COL/VL, employee submits actual resumption date. Sanction Authority reviews:
  - Normal return (`actual == end`): verified with no balance adjustment.
  - Early return (`actual < end`): actual leave period recorded, unused days restored to balance.
  - Late return (`actual > end`): actual leave period recorded, extra days deducted from balance.
  - No generic Closed state imposed.

### Defect 7: Retrospective Offline-Sanctioned Leave Entry Missing (BR-EL-029, CFR-EL-027, AFR-EL-027.1..5, EL-UC-016)
- **Problem**: No service or endpoint for Leave Administrators to record offline-sanctioned leave with sanction/reference evidence.
- **Specification**: Leave Administrator synchronizes valid offline-sanctioned leave, validates date/balance consistency, records the entry as approved, without creating a second approval workflow.

### Defect 8: Automated Year-End Processing Missing (BR-EL-002..009, CFR-EL-028, AFR-EL-028.1..5, EL-UC-020)
- **Problem**: No automated service or management command for year-end processing.
- **Specification**: Lapses unused CL, RH, and SCL; converts unused faculty VL to EL (2:1, fractional); carries forward EL and COL; creates account transaction records and exception reporting.

### Defect 9: Printable / Exportable Application Representation Missing (CFR-EL-023, AFR-EL-023.1, EL-UC-013)
- **Problem**: No endpoint to produce a structured printable/exportable representation of a leave application.

### Defect 10: SLA Notification & Escalation Infrastructure (CFR-EL-029, CFR-EL-030, CFR-EL-031, CFR-EL-032, BR-EL-032, BR-EL-033, BR-EL-035, BR-EL-038, EL-UC-018, EL-UC-021)
- **Problem**: Missing configurable reminder/escalation thresholds, pending-only guards, and task assignment notifications.

---

## 4. Phase 2 Engineering Action Plan

1. **Domain Layer (`modules/elm/domain/policy.py`)**:
   - Fix `convert_vl_to_el` to support exact half-day/fractional conversions.
   - Add helper logic for extension validation, resumption adjustments (early/late delta), and substitute eligibility.

2. **Data Layer (`modules/elm/models.py` & Migrations)**:
   - Enhance `LeaveApplication` status choices with workflow states (`ACTION_REQUIRED`, `CANCELLATION_PENDING`, `CANCELLATION_SANCTION`, `EXTENSION_*`, `RESUMPTION_PENDING`).
   - Add fields for extension tracking (`extended_from`, `actual_resumption_date`, `resumption_remarks`, `medical_evidence`).
   - Add `SlaConfig`, `LeaveNotification`, and `LeaveAccountTransaction` models.
   - Generate and apply Django migration `0002_elm_phase2_improvements.py`.

3. **Service Layer (`modules/elm/services/leave.py` & `services/admin.py`)**:
   - Update `submit()` with full substitute validation (no overlapping leave) and Director self-sanction route.
   - Implement `nominate_replacement_substitute()` (EL-UC-019).
   - Implement multi-stage cancellation workflow (`request_cancellation()`, cancel decision handling in `decide()`).
   - Implement extension workflow (`submit_extension()`).
   - Implement resumption workflow (`submit_resumption()`, `review_resumption()`).
   - Implement offline leave recording (`record_offline_leave()`).
   - Implement year-end processing service & management command (`elm_year_end`).
   - Implement notification generation on assignment, decision, and SLA threshold events.

4. **API Layer (`modules/elm/api/`)**:
   - Expose endpoints for:
     - `/applications/{id}/replace-substitute`
     - `/applications/{id}/request-cancellation`
     - `/applications/{id}/extend`
     - `/applications/{id}/resume`
     - `/applications/{id}/printable`
     - `/admin/offline-leave`
     - `/admin/year-end`
     - `/admin/sla-config`
     - `/notifications`

5. **Frontend Enhancements (`client/src/modules/elm/ElmPage.tsx`)**:
   - Add UI for substitute decline recovery (nominate replacement).
   - Add UI for requesting cancellation with status indicator.
   - Add UI for submitting resumption and extension.
   - Add UI for Leave Admin offline leave entry and year-end trigger.
   - Add printable representation modal/view.

6. **Rigorous Verification & Quality Checks**:
   - Expand `test_policy.py` and `test_leave_service.py` to cover all new workflows and edge cases.
   - Run `check` (ruff, lint-imports, no_cross_module_fk, contracts_are_plural, nav_matches_routes, permission_manifest, schema-check, pytest).
   - Run `check-client` (tsc, vitest, vite build).
