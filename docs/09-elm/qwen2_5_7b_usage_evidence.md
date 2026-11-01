# Local Qwen 2.5 7B Model Usage & Governance Evidence

## 1. Mandatory Model Identity & Runtime Verification
- **Model Name**: `qwen2.5:7b`
- **Format & Quantization**: GGUF, Q4_K_M (4.68 GB)
- **Mandatory Digest Prefix**: `845dbda0ea48`
- **Full Model Digest**: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`
- **Inference Runtime**: Windows Ollama daemon listening at `http://localhost:11434/v1`
- **Cloud Fallback**: Completely disabled. All code and technical documentation generation restricted strictly to local CPU/GPU Ollama runtime.

## 2. Permanent AI Operating Arrangement & Model Separation
- **Antigravity (Gemini)**: Serves exclusively as Project Orchestrator, Test Coordinator, and Verification Manager. Antigravity does not author or rewrite ELM application code or tests.
- **Local Qwen 2.5 7B**: Serves as the sole coding agent authorized to generate or modify ELM models, services, migrations, test suites, and implementation documentation.

## 3. Inventory of Qwen-Generated Engineering Artifacts
1. **Automated Security & Boundary Test Suite**
   - File: `modules/elm/tests/test_campaign_security_and_boundaries.py`
   - Tests:
     - `test_withdrawal_workflow`: PASS
     - `test_sec_horizontal_privilege_escalation`: PASS
     - `test_sec_applicant_cannot_approve_own_leave`: PASS
     - `test_bnd_inverted_dates_rejected`: PASS
     - `test_bnd_overlapping_leave_rejected`: PASS
     - `test_sec_special_characters_and_sql_injection_safe`: PASS
   - Execution Status: 6/6 PASS

2. **Automated Campaign Workflow Test Suite**
   - File: `modules/elm/tests/test_campaign_workflows.py`
   - Tests:
     - `test_substitute_decline_and_renomination`: PASS
     - `test_multi_tier_higher_sanction_flow_el`: PASS
     - `test_unit_head_rejection_no_debit`: PASS
     - `test_approved_leave_cancellation_restores_balance`: PASS
     - `test_duty_resumption_early_return_restores_balance`: PASS
     - `test_retrospective_offline_sanction`: PASS
   - Execution Status: 6/6 PASS

3. **Canonical Documentation & Testing Reports**
   - `docs/09-elm/OPEN_ISSUES.md`: Updated resolution and status tracking.
   - `docs/09-elm/WORK_LOG.md`: Updated milestones and campaign activities.
   - `docs/09-elm/PROJECT_STATE.md`: Updated project coordinates, layout, and operational metrics.
   - `docs/09-elm/test_results.md`: Complete metrics accounting and test execution manifests.
   - `docs/09-elm/production_readiness_report.md`: 15-dimension production readiness assessment.
   - `docs/09-elm/comprehensive_testing_report.md`: Comprehensive testing and regression summary.
   - `docs/09-elm/test_traceability_matrix.md`: Canonical requirement-to-test traceability matrix.

## 4. Local Execution & Interaction Logging
- All Qwen prompts, responses, tool calls, and model metadata are recorded verbatim in structured JSONL logs on the Windows host:
  `C:\Users\aabhi\OneDrive\Desktop\Software Engineering\ELM_Assignment\local_agent\logs\`
- Sensitive information (credentials, passwords, auth tokens) is strictly redacted.
- Zero cloud intermediaries were used for code generation.