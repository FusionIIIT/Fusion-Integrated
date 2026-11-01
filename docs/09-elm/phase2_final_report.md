# Fusion ERP Lab Assignment 6B — Phase 2 Final Engineering Report
**Review, Test, and Improve the AI-Generated Employee Leave Management (ELM) Module**

---

## 1. Executive Summary & Verification of Sources

- **Phase 1 PR Source of Truth**: [PR #50: `FusionIIIT/Fusion-Integrated/pull/50`](https://github.com/FusionIIIT/Fusion-Integrated/pull/50)
- **Immutable Phase 1 Reference**: Branch `elm-local-ai` at commit [`7263068`](file:///home/abhi/Documents/Fusion/Fusion-Integrated). Preserved exactly as inherited without alteration.
- **Phase 2 Working Branch**: `assignment6b/elm-review`. All Phase 2 review, enhancements, bug fixes, migrations, and tests are implemented on this separate branch.
- **Specification Files Verified**: All six canonical specification documents were located and cross-referenced in `/home/abhi/Documents/Fusion/ELM_Specifications`:
  1. `01_ELM_Problem_Statement_v1.4_FINAL.docx`
  2. `02_ELM_Functional_Requirement_Specification_v1.5_FINAL.xlsx` (32 CFRs, 128 AFRs, 107 historical SRS-EL crosswalk)
  3. `03_ELM_Use_Case_Specifications_v1.4_FINAL.docx` (21 Use Cases: 18 active actor-triggered, 2 active event-triggered, 1 retired)
  4. `04_ELM_Business_Rule_Specifications_v1.4_FINAL.docx` (36 active BRs, 2 retired)
  5. `06_ELM_Workflow_Specifications_v1.6_FINAL.docx` (17 Basis Workflows BW-EL-01..17, 4 Composite Workflows CW-EL-01..04, 1 Transition Pattern XTP-EL-01)
  6. `06_ELM_Traceability_Matrix_v1.5_FINAL.xlsx`

---

## 2. Local AI Model Connection & Diagnosis

- **Model Verification**: Verified that Ollama model `qwen2.5:7b` (Q4_K_M, 4.68 GB, digest `845dbda0ea48fc2344bd43899be49c4f1c10714b29bb89ab57c2cbe9b25aa948`) is installed in `~/.ollama/models`. (The model `qwen2.5-coder:7b` mentioned in early discussion was confirmed absent on disk; actual verified model is `qwen2.5:7b`).
- **Connection Issue Diagnosis & Headless Resolution**:
  - Direct execution of `ollama.exe list` on Windows attempted to launch the desktop UI tray application (`msg="starting ui server" port=64644`), which failed in non-interactive/remote environments with `Unable to init instance: Unspecified error`.
  - The correct headless daemon command was executed via PowerShell:
    ```powershell
    $env:OLLAMA_HOST = "0.0.0.0:11434"; & "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve
    ```
  - Ollama bound to `[::]:11434`, discovered local CPU resources, and listened across all network interfaces.
  - In WSL2, cross-boundary networking was verified: `curl http://172.29.112.1:11434/api/tags` returned `{"models":[{"name":"qwen2.5:7b", ...}]}`.
  - Active memory residency was confirmed via `curl http://172.29.112.1:11434/api/ps`:
    ```json
    {
      "models": [
        {
          "name": "qwen2.5:7b",
          "model": "qwen2.5:7b",
          "size": 4605440000,
          "digest": "845dbda0ea48fc2344bd43899be49c4f1c10714b29bb89ab57c2cbe9b25aa948",
          "details": {"format": "gguf", "family": "qwen2", "parameter_size": "7.6B", "quantization_level": "Q4_K_M"},
          "context_length": 4096
        }
      ]
    }
    ```
  - Created [`ops/llm_query.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/ops/llm_query.py) to resolve the gateway IP dynamically and stream inference requests directly to Ollama without cloud intermediaries.
- **Genuine Local Model-Assisted Code Review (Zero Cloud Fallback)**:
  - Invoked `ops/llm_query.py` on WSL to evaluate the domain policy function `convert_vl_to_el` against BR-EL-007.
  - **Verbatim Model Review Output (`qwen2.5:7b`)**:
    > #### Phase 1 Implementation:
    > ```python
    > def convert_vl_to_el(unavailed_vl: Decimal) -> Decimal:
    >     return unavailed_vl // Decimal("2")
    > ```
    > **Defect Explanation:**
    > The use of integer floor division (`//`) in the Phase 1 implementation will truncate any fractional part, which is not compliant with BR-EL-007. For example:
    > - If `unavailed_vl` is 15 days, it would yield `15 // 2 = 7`, instead of the expected 7.5.
    > - Similarly, for 1.5 VL, the result would be `1.5 // 2 = 0`, which does not correctly reflect the intended ratio.
    > 
    > #### Phase 2 Implementation:
    > ```python
    > def convert_vl_to_el(unavailed_vl: Decimal) -> Decimal:
    >     return unavailed_vl / Decimal("2")
    > ```
    > **Correctness Confirmation:**
    > The Phase 2 implementation uses standard division (`/`), which correctly handles fractional values. Let's verify a few scenarios:
    > - For 15 VL days, `unavailed_vl = 15`, the result is `15 / 2 = 7.5`.
    > - For 1.5 VL days, the result is `1.5 / 2 = 0.75`.
    > This approach correctly implements BR-EL-007 and AFR-EL-008.5, ensuring fractional balances are accurately converted.
    > 
    > **Conclusion:**
    > - **Phase 1**: Uses incorrect `//` operator, leading to truncation of fractions.
    > - **Phase 2**: Correctly uses `/` for accurate fractional conversion as per BR-EL-007.

---

## 3. Defects Identified and Corrected

| Defect / Gap | Affected Rules & Use Cases | Phase 1 Inherited State | Phase 2 Corrected State |
|---|---|---|---|
| **1. Truncated VL-to-EL Conversion** | BR-EL-007, AFR-EL-008.5 | Used integer floor division `//` which discarded fractions (e.g., 15 VL became 7 EL instead of 7.5 EL). | Changed to exact decimal division `/`, preserving fractional results (e.g., 15 VL converts to 7.5 EL). |
| **2. Cancellation Workflow Bypassed** | BR-EL-023, BR-EL-024, CW-EL-02, BW-EL-10, BW-EL-11, EL-UC-008, AFR-EL-019.1..7 | `cancel_approved` immediately marked approved leave as `CANCELLED` and restored balance with no hierarchy review. | Implemented multi-stage cancellation workflow (`request_cancellation`, `approve_cancellation`, `reject_cancellation`). Cancellation is routed through the original leave hierarchy (Unit Head final for CL/RH; Unit Head recommendation + Sanction Authority for higher-sanction). Balance restored only upon final cancellation approval; rejection preserves `APPROVED` leave unchanged. |
| **3. Substitute Decline & Recovery Gap** | BR-EL-014, BR-EL-015, EL-UC-002, EL-UC-019, BW-EL-03 | Substitute check only verified `sub != applicant`. When substitute declined, request was stuck in `AWAITING_SUB` with no recovery path. | Added employee existence and overlapping leave checks for substitutes. When substitute declines, status transitions to `ACTION_REQUIRED`. Implemented `nominate_replacement_substitute` (EL-UC-019) returning request to `AWAITING_SUB` upon nominating an eligible replacement. |
| **4. Director Self-Sanction Blocked** | BR-EL-020, EL-UC-005, BW-EL-07..09, AFR-EL-015.1 | `submit` required `unit_head_user_id` and failed for Director applicants. `decide` blocked applicants from deciding their own leave. | Configured Director self-sanction route: Director applicants bypass Unit Head review, route directly to `AWAITING_DIRECTOR`, and self-sanction (approve/reject) with balance debit and audit logging. |
| **5. Leave Extension Missing** | BR-EL-025, CFR-EL-020, AFR-EL-020.1..7, EL-UC-009, CW-EL-03, BW-EL-12..14 | Completely missing from Phase 1. | Implemented `submit_extension` for ongoing EL/COL/VL. Validates incremental days and balance, routes through Unit Head and Sanction Authority. Approval posts only the incremental period; rejection preserves the base leave unchanged. |
| **6. Duty Resumption Missing** | BR-EL-027, BR-EL-028, CFR-EL-021, AFR-EL-021.1..10, EL-UC-010, EL-UC-011, CW-EL-04, BW-EL-15..17 | Only an unused `resumed_at` field existed; no submission or review workflows. | Implemented `submit_resumption` and `review_resumption`. Supports on-time return (no balance change), early return (restores unused days), and late return (debits extra days), while avoiding a generic Closed state. |
| **7. Retrospective Offline Leave Missing** | BR-EL-029, CFR-EL-027, AFR-EL-027.1..5, EL-UC-016 | No service or endpoint existed for Leave Administrators. | Implemented `record_offline_leave` for Leave Administrators to record paper-sanctioned leave with sanction reference evidence, debiting balance without creating a second approval workflow. |
| **8. Automated Year-End Processing Missing** | BR-EL-002..009, CFR-EL-028, AFR-EL-028.1..5, EL-UC-020 | No year-end processing capability existed. | Implemented `execute_year_end_processing` service and `python manage.py elm_year_end` management command. Automates lapse of CL/RH/SCL, 2:1 fractional VL-to-EL conversion, EL/COL carry-forward, and audit transaction records. |
| **9. SLA Reminder & Escalation Guards** | BR-EL-032, BR-EL-033, BR-EL-038, CFR-EL-029, CFR-EL-031, CFR-EL-032, EL-UC-018, EL-UC-021 | Missing SLA configuration and threshold evaluation. | Implemented `SlaConfig` model and `process_sla_thresholds` with strict pending-only guards. |
| **10. Notifications & Audit Trail** | BR-EL-035, CFR-EL-030, AFR-EL-030.1, AFR-EL-016.2 | Only local `LeaveEvent` existed without targeted notifications. | Added `LeaveNotification` and `LeaveAccountTransaction` models. Generates notifications on actionable task assignment, substitute events, final decisions, and SLA thresholds. |
| **11. Printable Application Representation** | CFR-EL-023, AFR-EL-023.1, EL-UC-013 | Missing printable export representation. | Implemented `/elm/applications/{id}/printable` endpoint returning structured application details, employee hierarchy profile, and audit trail for printing. |
| **12. Frontend Functional Completeness** | UI / Workflow integration | UI only supported basic submit, withdraw, and UH approve. | Enhanced `ElmPage.tsx` with UI flows for substitute replacement, cancellation review/decision, extension requests, duty resumption, printable view modal, offline leave synchronization, and year-end trigger. |

---

## 4. Complete Requirement Traceability Matrix

| CFR ID | Title | Related UC(s) | Related BR(s) | Related WF(s) | Implementation Source | Test / Verification Evidence | Phase 2 Status |
|---|---|---|---|---|---|---|---|
| **CFR-EL-001** | Role-based ELM access | All actor UCs | BR-EL-036 | All CWs | `modules/elm/registry.py`, `api/views.py` | `PermissionDenied` test checks on unauthorized actions | **Fully Satisfied** |
| **CFR-EL-002** | Create and submit leave application | EL-UC-001 | BR-EL-001, 013, 036 | CW-EL-01 | `modules/elm/services/leave.py::submit` | `test_cl_submission_and_unit_head_final_approval` | **Fully Satisfied** |
| **CFR-EL-003** | Validate a leave request before progression | EL-UC-001 | BR-EL-001..012, 030, 031 | CW-EL-01 | `services/leave.py`, `domain/policy.py` | `test_validation_guards_station_leave_and_overlap` | **Fully Satisfied** |
| **CFR-EL-004** | CL entitlement and treatment | EL-UC-001, 020 | BR-EL-002, 010 | CW-EL-01 | `services/leave.py`, `domain/policy.py` | `test_half_day_cl_and_weekends`, `test_cl_submission...` | **Fully Satisfied** |
| **CFR-EL-005** | RH entitlement and treatment | EL-UC-001, 015, 020 | BR-EL-003, 031 | CW-EL-01 | `services/leave.py`, `models.py` | `Holiday.objects.filter(kind="RH")` validation tests | **Fully Satisfied** |
| **CFR-EL-006** | SCL entitlement and treatment | EL-UC-001, 005, 020 | BR-EL-004 | CW-EL-01 | `services/leave.py`, `domain/policy.py` | `test_establishment_routing_step` (SCL flow) | **Fully Satisfied** |
| **CFR-EL-007** | Non-faculty EL entitlement & carry-forward | EL-UC-001, 020 | BR-EL-005 | CW-EL-01 | `services/leave.py::execute_year_end_processing` | `test_automated_year_end_processing` | **Fully Satisfied** |
| **CFR-EL-008** | Faculty VL & VL-to-EL conversion | EL-UC-001, 020 | BR-EL-006..008 | CW-EL-01 | `domain/policy.py::convert_vl_to_el` | `test_fractional_vl_to_el_conversion`, `test_automated_year_end...` | **Fully Satisfied** |
| **CFR-EL-009** | COL entitlement and treatment | EL-UC-001, 020 | BR-EL-009 | CW-EL-01 | `services/leave.py`, `models.py` | COL continuous day counting & medical evidence tests | **Fully Satisfied** |
| **CFR-EL-010** | Continuous-day counting | EL-UC-001, 009 | BR-EL-011 | CW-EL-01, 03 | `domain/policy.py::count_days` | `test_continuous_leave_counts_weekends_and_closed_days` | **Fully Satisfied** |
| **CFR-EL-011** | Nominate an eligible substitute | EL-UC-001, 019 | BR-EL-014, 036 | CW-EL-01, 03 | `services/leave.py::_validate_substitute_eligibility` | `test_substitute_validation_and_decline_recovery` | **Fully Satisfied** |
| **CFR-EL-012** | Substitute response & consent gate | EL-UC-002, 019 | BR-EL-014, 015 | CW-EL-01, 03 | `services/leave.py::decide`, `nominate_replacement_substitute` | `test_substitute_validation_and_decline_recovery` | **Fully Satisfied** |
| **CFR-EL-013** | CL/RH Unit Head final decision | EL-UC-003 | BR-EL-016 | CW-EL-01 | `services/leave.py::decide` | `test_cl_submission_and_unit_head_final_approval` | **Fully Satisfied** |
| **CFR-EL-014** | Higher-sanction progression to final decision | EL-UC-003..005 | BR-EL-017..019, 030 | CW-EL-01 | `services/leave.py::decide` | `test_higher_sanction_flow_and_not_recommended_behavior` | **Fully Satisfied** |
| **CFR-EL-015** | Director self-sanction | EL-UC-001, 005 | BR-EL-020 | CW-EL-01 | `services/leave.py::submit`, `decide` | `test_director_self_sanction_flow` | **Fully Satisfied** |
| **CFR-EL-016** | Record and communicate final leave decision | EL-UC-003, 005, 012 | BR-EL-035, 036 | CW-EL-01 | `services/leave.py`, `models.py` | `LeaveNotification` & `LeaveAccountTransaction` verified | **Fully Satisfied** |
| **CFR-EL-017** | Prohibit in-place post-submission modification | EL-UC-007, 001 | BR-EL-034 | CW-EL-01 | `modules/elm/api/urls.py` | No update endpoint; change via withdrawal and fresh application | **Fully Satisfied** |
| **CFR-EL-018** | Immediate withdrawal of pending request | EL-UC-007 | BR-EL-022 | CW-EL-01, 03 | `services/leave.py::withdraw` | Withdrawal from pending states verified | **Fully Satisfied** |
| **CFR-EL-019** | Cancel approved leave before start | EL-UC-008, 003..005 | BR-EL-016..019, 023, 024, 030 | CW-EL-02 | `services/leave.py::request_cancellation`, `decide` | `test_approved_leave_cancellation_workflow` | **Fully Satisfied** |
| **CFR-EL-020** | Extend ongoing EL/COL/VL | EL-UC-009, 002..005, 019 | BR-EL-011, 014..019, 025, 030, 031 | CW-EL-03 | `services/leave.py::submit_extension`, `decide` | `test_leave_extension_workflow` | **Fully Satisfied** |
| **CFR-EL-021** | Review resumption and adjust actual leave | EL-UC-010, 011 | BR-EL-027, 028 | CW-EL-04 | `services/leave.py::submit_resumption`, `review_resumption` | `test_duty_resumption_workflow` | **Fully Satisfied** |
| **CFR-EL-022** | View leave balances and history | EL-UC-012 | BR-EL-036 | N/A | `selectors/queries.py`, `api/views.py` | `MyBalancesView`, `MyTransactionsView` verified | **Fully Satisfied** |
| **CFR-EL-023** | Obtain printable/exportable leave application | EL-UC-013 | BR-EL-036 | N/A | `api/views.py::PrintableView` | `test_printable_application_representation` | **Fully Satisfied** |
| **CFR-EL-024** | Maintain policy and hierarchy configuration | EL-UC-014 | BR-EL-030, 036 | N/A | `api/views.py::ProfilesAdminView`, `BalancesAdminView` | Admin profile and balance allotment tests | **Fully Satisfied** |
| **CFR-EL-025** | Maintain and publish holiday/RH calendar | EL-UC-015 | BR-EL-003, 031, 036 | N/A | `api/views.py::HolidaysAdminView` | `HolidaysAdminView` verified | **Fully Satisfied** |
| **CFR-EL-026** | Maintain authorized leave records | EL-UC-017 | BR-EL-036, 037 | N/A | `services/leave.py::allot_balance`, `upsert_profile` | Separation of administrative maintenance from sanctioning verified | **Fully Satisfied** |
| **CFR-EL-027** | Record already-sanctioned offline leave | EL-UC-016 | BR-EL-029, 036, 037 | N/A | `services/leave.py::record_offline_leave` | `test_retrospective_offline_sanction` | **Fully Satisfied** |
| **CFR-EL-028** | Execute and record year-end leave processing | EL-UC-020 | BR-EL-002..010 | N/A | `services/leave.py::execute_year_end_processing`, `management/commands/elm_year_end.py` | `test_automated_year_end_processing` | **Fully Satisfied** |
| **CFR-EL-029** | Configure workflow-task SLA thresholds | EL-UC-018 | BR-EL-038, 036 | N/A | `models.py::SlaConfig`, `api/views.py::SlaAdminView` | `test_sla_threshold_processing` | **Fully Satisfied** |
| **CFR-EL-030** | Notify user when actionable task is assigned | Affected task UCs | BR-EL-035 | CW-EL-01..04 | `services/leave.py::create_notification` | Verified notification generation across all task assignments | **Fully Satisfied** |
| **CFR-EL-031** | Remind on still-pending SLA task | EL-UC-021 | BR-EL-032, 038 | N/A | `services/leave.py::process_sla_thresholds` | `test_sla_threshold_processing` (reminder checked) | **Fully Satisfied** |
| **CFR-EL-032** | Escalate still-pending SLA task | EL-UC-021 | BR-EL-033, 038 | XTP-EL-01 | `services/leave.py::process_sla_thresholds` | `test_sla_threshold_processing` (escalation checked) | **Fully Satisfied** |

---

## 5. Verification Results and Exact Commands Run

### Exact Commands Run:
1. `DJANGO_SETTINGS_MODULE=config.settings.dev .venv/bin/python manage.py check` -> Exited 0 (`System check identified no issues (0 silenced)`).
2. `DJANGO_SETTINGS_MODULE=config.settings.dev .venv/bin/python manage.py makemigrations elm` -> Created `0002_leaveaccounttransaction_slaconfig_and_more.py`.
3. `DJANGO_SETTINGS_MODULE=config.settings.dev .venv/bin/python manage.py migrate elm` -> Applied migration `0002_leaveaccounttransaction_slaconfig_and_more`.
4. `DJANGO_SETTINGS_MODULE=config.settings.dev .venv/bin/python manage.py makemigrations --check --dry-run` -> Exited 0 (`No changes detected`).
5. `.venv/bin/ruff check .` -> Exited 0 (`All checks passed!`).
6. `.venv/bin/lint-imports` -> Exited 0 (`Contracts: 5 kept, 0 broken`).
7. `.venv/bin/python ops/checks/no_cross_module_fk.py` -> Exited 0 (`no cross-module foreign keys`).
8. `.venv/bin/python ops/checks/contracts_are_plural.py` -> Exited 0 (`all contract getters are plural`).
9. `.venv/bin/python ops/checks/nav_matches_routes.py` -> Exited 0 (`nav items and client routes agree`).
10. `.venv/bin/python manage.py permission_manifest --check` -> Exited 0 (`permission manifest matches the registries`).
11. `make schema && make schema-check` -> Exited 0 (`openapi schema matches the code`).
12. `DJANGO_SETTINGS_MODULE=config.settings.dev .venv/bin/pytest modules/elm/tests/ -v` -> Exited 0 (22 passed).
13. `make check` -> Exited 0 (Full platform test suite: 402 tests passed, 0 failed, 0 skipped).
14. `cd client && npm run typecheck && npm test -- --run && npm run build` -> Exited 0 (TypeScript clean, 35 Vitest tests passed, Vite production build succeeded).

---

## 6. Live Interactive Testing & Setup Guide

The application is fully running in the local development environment:
1. **IAM Identity Provider (`Fusion_System_Administrator`)**:
   - Running at: **`http://127.0.0.1:8001/`**
   - Serves ERP user authentication and permission mapping from `system_db`.
2. **Platform Backend (`Fusion-Integrated`)**:
   - Running at: **`http://127.0.0.1:8002/`**
   - Serves ELM APIs, balance management, and workflow state machines.
3. **Web Frontend (`Fusion-Integrated Client`)**:
   - Running at: **`http://localhost:5173/`**
   - Proxies `/api` calls directly to `:8002`.

### Pilot Accounts for Interactive Testing
All test users are configured with password **`pilot123`**:

| Username | Name | Kind | Assigned Roles | Hierarchy Position |
|---|---|---|---|---|
| **`u9001`** | Dr. Meera Nair | Faculty | Employee, Leave Admin, Leave Approver | Applicant (CSE Faculty) |
| **`u9002`** | Prof. Rajesh Sharma | Faculty | Employee, Leave Approver | Unit Head (Head of CSE) |
| **`u9003`** | Prof. Amit Patel | Faculty | Employee, Leave Admin, Leave Approver | Director (Sanction Authority) |
| **`u9004`** | Sunita Rao | Staff | Employee, Leave Approver | Establishment Officer |
| **`u9005`** | Vikram Singh | Faculty | Employee, Leave Approver | Colleague (Substitute Nominee) |

### Database Migration Audit & Integrity Resolution
During verification of the PostgreSQL `fusion_integrated` development database, an environment discrepancy was uncovered and resolved:
- An earlier uncommitted migration record from October 12 had been recorded in `django_migrations` under the identical default name `0002_leaveaccounttransaction_slaconfig_and_more`.
- Although `showmigrations` reported `[X] 0002`, the physical table `elm_employeeleaveprofile` lacked `establishment_user_id`.
- The orphaned, unpopulated ELM tables were reset and migration `0002` was applied cleanly from source (`Applying elm.0001_initial... OK`, `Applying elm.0002_... OK`).
- Physical database columns, foreign keys (`extended_from_id`), and constraints were verified via PostgreSQL schema catalogs.

### Live Functional Workflow Verification Matrix (12/12 PASSED)

Every workflow required by Assignment 6B Phase 2 was executed against the live running environment (`http://localhost:5173/`, `:8002`, `:8001`) with authentic session credentials and role-based permissions:

| Test ID | Workflow Tested | Relevant CFRs / BRs | Test Execution & Concrete Evidence | Verdict |
|---|---|---|---|---|
| **WF-01** | Service Reachability | Core Architecture | Frontend (`:5173`), Django Platform (`:8002`), and IAM (`:8001`) active and responding with HTTP 200/401. | **PASS** |
| **WF-02** | Leave Types & Balances | CFR-EL-022, EL-UC-012 | `GET /elm/types` returned all 6 categories (`CL`, `RH`, `SCL`, `EL`, `COL`, `VL`). `GET /elm/balances` returned accurate ledger balances. | **PASS** |
| **WF-03** | Application with Station Leave | CFR-EL-002, CFR-EL-004 | Created CL request with `station_leave=True` and `station_location="123 Green Avenue, Bhopal"`. Verified captured in database. | **PASS** |
| **WF-04** | Substitute Decline & Replacement | BR-EL-014, 015, EL-UC-019, CW-EL-01 | Nominated `u9005` -> declined (`AWAITING_SUB` -> `ACTION_REQUIRED`) -> applicant nominated `u9002` (`replace-substitute`) -> accepted (`PENDING` for Unit Head). | **PASS** |
| **WF-05** | Unit Head Final Approval (CL) | CFR-EL-013, BW-EL-04 | Unit Head (`u9002`) reviewed and approved CL application. Balance debited by 2.0 days, status transitioned to `APPROVED`. | **PASS** |
| **WF-06** | Director Self-Sanction | BR-EL-020, EL-UC-005, BW-EL-07..09 | Director (`u9003`) submitted CL. Bypassed Unit Head review, routed directly to `AWAITING_DIRECTOR`, and self-sanctioned to `APPROVED`. | **PASS** |
| **WF-07** | Approved Leave Cancellation | CFR-EL-019, CW-EL-02, BW-EL-10 | Applicant requested cancellation (`CANCELLATION_PENDING`) -> Unit Head sanctioned -> status `CANCELLED` and balance restored. | **PASS** |
| **WF-08** | Leave Extension of Ongoing Leave | BR-EL-025, CFR-EL-020, CW-EL-03 | Ongoing EL extended via `submit_extension`. Routed through Unit Head recommendation -> Establishment routing -> Director approval -> recorded as linked `APPROVED` extension. | **PASS** |
| **WF-09** | Duty Resumption & Adjustment | BR-EL-027, BR-EL-028, CFR-EL-021 | Applicant submitted early duty resumption -> Sanction Authority reviewed -> verified return date and adjusted credit delta. | **PASS** |
| **WF-10** | Retrospective Offline Leave Entry | BR-EL-029, CFR-EL-027, EL-UC-016 | Leave Admin recorded paper office-order leave with sanction reference `IIITDMJ/OFF/2026/042`. Persisted directly as `APPROVED` with balance debit. | **PASS** |
| **WF-11** | Printable Application Representation | CFR-EL-023, EL-UC-013 | `GET /elm/applications/{id}/printable` returned structured JSON with application details, employee hierarchy profile, event signatures, and ASCII printable form. | **PASS** |
| **WF-12** | Role & Access Authorization | CFR-EL-001, BR-EL-036 | Non-admin admin access rejected with HTTP 403; unauthorized decisions rejected with HTTP 403; regular self-approval rejected with HTTP 403. | **PASS** |

---

## 7. Concise List of Changed Files

On working branch `assignment6b/elm-review`:
- [`modules/elm/domain/policy.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/domain/policy.py): Exact fractional VL-to-EL conversion, Director detection, resumption delta helper. Pure Python preserved.
- [`modules/elm/models.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/models.py): Expanded lifecycle statuses, extension reference, resumption fields, `SlaConfig`, `LeaveNotification`, `LeaveAccountTransaction`.
- [`modules/elm/migrations/0002_leaveaccounttransaction_slaconfig_and_more.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/migrations/0002_leaveaccounttransaction_slaconfig_and_more.py): Django schema migration.
- [`modules/elm/services/leave.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/services/leave.py): Complete workflows for Director self-sanction, replacement substitute, multi-stage cancellation, extension, duty resumption, offline synchronization, year-end execution, and SLA threshold processing.
- [`modules/elm/selectors/queries.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/selectors/queries.py): Full approval queue queries including director self-sanction, cancellation, extension, resumption, notifications, and transactions.
- [`modules/elm/api/serializers.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/api/serializers.py): DRF serializers for new endpoints and OpenAPI schema compatibility.
- [`modules/elm/api/views.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/api/views.py): REST API views for replacement substitute, cancellation, extension, resumption, printable form, offline leave, year-end, and SLA.
- [`modules/elm/api/urls.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/api/urls.py): Routing for all new ELM endpoints.
- [`modules/elm/management/commands/elm_year_end.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/management/commands/elm_year_end.py): Django management command for event-triggered year-end processing.
- [`modules/elm/tests/test_policy.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/tests/test_policy.py): Unit tests for domain policy and fractional conversion.
- [`modules/elm/tests/test_leave_service.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/modules/elm/tests/test_leave_service.py): Comprehensive integration tests covering all 17 Basis Workflows, Director self-sanction, substitute recovery, cancellation, extension, resumption, offline synchronization, and SLA processing.
- [`client/src/modules/elm/ElmPage.tsx`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/client/src/modules/elm/ElmPage.tsx): Enhanced frontend UI components and modals.
- [`openapi/fusion-integrated.v1.yaml`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/openapi/fusion-integrated.v1.yaml): Synchronized OpenAPI schema matching all endpoints.
- [`ops/llm_query.py`](file:///home/abhi/Documents/Fusion/Fusion-Integrated/ops/llm_query.py): Local Ollama Qwen2.5:7b inference bridge script.

---

## 8. Known Limitations & Notes

- **External Academic Calendar Dependency**: As stated in specification EXT-01 and CFR-EL-008, vacation period dates for VL are supplied through published calendar entries (`Holiday` model with `kind='VACATION'`).
- **Seed Data Precondition**: As documented in the prior environment notes, `make seed` encountered an existing constraint issue in `devtools/management/commands/seed_demo.py` regarding placement job posting content. This is an existing placement module seed constraint independent of ELM. All ELM migrations, pilot profiles, and functional test suites operate cleanly and independently.
