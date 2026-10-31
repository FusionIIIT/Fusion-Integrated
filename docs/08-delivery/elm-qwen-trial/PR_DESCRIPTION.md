# Phase 2: Review, Test, and Improve the ELM Module (`qwen2.5-coder:3b`)

Improves the preserved Phase-1 ELM implementation (`e8b33a5` on `codex/elm-qwen-trial`) into a tested, deployment-ready Fusion ERP module on `codex/elm-qwen-phase2` using only local Ollama `qwen2.5-coder:3b` generation via `devtools/qwen_elm_trial.py` (Prompts `037`–`094`).

## Key Improvements
- **Permissions & Registry (`038`):** Resolved `SYSTEM_PERMISSIONS` vs `ROLE_GRANTS` collision and enforced all 8 ELM permission checks across services and views.
- **Schema & Models (`087` + `0002_phase2_schema_fixes`):** Fixed `LeaveBalance` foreign-key queries and added `AttachmentRecord`, `NotificationDispatchLog`, `LeaveAuditEvent`, and policy configuration columns.
- **Domain Policy & Services (`065`, `072`, `077`, `081`, `082`):** Implemented pure domain validation (half-day, joining date, probation, proof requirements, advance notice) and end-to-end draft, submit, cancel, substitute response, review, and sanction/reject workflows with atomic balance deduction and restoration.
- **API & Frontend (`058`, `059`, `066`, `067`, `079`, `083`, `084`, `089`, `090`):** Aligned DRF serializers, added `/submit`, `/cancel`, and admin CRUD endpoints, and updated `MyLeavePage`, `LeaveTasksPage`, and `LeaveAdminPage`.
- **Verification (`091`):** Passes `manage.py check`, `migrate`, `permission_manifest --check`, `lint-imports`, `schema-check`, `tsc --noEmit`, `npm run build`, and `pytest` (`4 passed` in `test_elm_phase2.py`, `384 passed` repository-wide).
