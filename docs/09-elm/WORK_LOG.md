# WORK_LOG.md

## Fusion ERP Employee Leave Management (ELM) Milestones

### Phase 1: Initial Setup & Configuration
- [Date]: [Execution Date]
  - [Description]: Detailed description of initial setup and configuration tasks.

### Phase 2: Integration with IAM System
- [Date]: [Execution Date]
  - [Description]: Description of integration steps between ELM and the Identity Access Management (IAM) system, including role definitions and user mappings.
  
### Post-Phase 2 Recovery & Governance Milestone
- [Date]: [Execution Date]
  - [Description]: Summary of post-integration recovery and governance actions.

#### IAM Remediation Execution
- Executed 5 approved `assign_role` commands in `Fusion_System_Administrator` against local database `fusion_system_db` on `127.0.0.1:5432`.
  - Assigned `Employee`, `Leave Admin`, `Leave Approver` to `u9001` (Dr. Meera Nair).
  - Assigned `Employee`, `Leave Approver` to `u9005` (Vikram Singh).
- Read-only verification confirmed zero duplicates, zero global privilege changes, and restored `leave_elm` module visibility.
- Verified idempotency via safe replay.

### Development Environment Startup & Verification (2026-10-30)

- Verified PostgreSQL running on 127.0.0.1:5432 with databases `fusionlab` and `fusion_system_db`.
- Diagnosed IAM stale role refresh behavior (`IAM_REFRESH_ROLES_AFTER_SECONDS`) where pilot users without ERP `GlobalsHoldsdesignation` entries had designations overwritten on login.
- Configured `IAM_REFRESH_ROLES_AFTER_SECONDS = 0` in IAM settings/env to disable stale role refresh in development.
- Restored and verified pilot designations (`u9001` - `u9005`).
- Started Fusion IAM Backend daemon on `http://127.0.0.1:8001/`.
- Started Fusion Django Platform Backend daemon on `http://127.0.0.1:8002/`.
- Started Fusion React Frontend daemon on `http://localhost:5173/`.
- Verified end-to-end authentication, cookie management, role mapping, and `/api/v1/me` navigation for all 5 test accounts (`u9001` - `u9005`) through the Vite proxy.

