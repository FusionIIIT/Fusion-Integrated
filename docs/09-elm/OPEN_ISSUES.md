# OPEN ISSUES

## RESOLVED ISSUES

### ISSUE-ELM-001: User `u9001` (Dr. Meera Nair) and `u9005` (Vikram Singh) Missing IAM Designation Assignments
- **Status:** RESOLVED
- **Resolution Summary:** The 5 missing role assignments were executed using `backend/manage.py assign_role` in `Fusion_System_Administrator` against the local development database `fusion_system_db`. A read-only audit confirmed that `u9001` now holds the roles `Employee`, `Leave Admin`, and `Leave Approver`, while `u9005` holds the roles `Employee` and `Leave Approver`. The process ensured zero duplicate rows, no privilege elevation, and full restoration of ELM module access.

### ISSUE-ELM-004: IAM Stale Role Refresh Overwrite on Pilot Users
- **Status:** RESOLVED
- **Root Cause:** The `_refresh_roles_if_stale` function was querying ERP `GlobalsHoldsdesignation`, which did not exist for pilot users, leading to their designations being overwritten upon login.
- **Resolution:** Set `IAM_REFRESH_ROLES_AFTER_SECONDS = 0` in the IAM settings/env to disable stale role refresh in development.


## OPEN/LOW PRIORITY ISSUES

### ISSUE-ELM-002: Untracked Documentation Artifacts
- **Status:** Open / Low Priority
- **Description:** There are untracked documentation artifacts that need to be reviewed and updated. This issue is currently being prioritized based on the current project timeline.

## INFORMATIONAL ISSUES

### ISSUE-ELM-003: Ollama CPU Context Window
- **Status:** Informational
- **Description:** The Ollama CPU context window has been noted but does not require immediate action. It will be addressed as part of future optimization efforts.

