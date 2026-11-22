# System Admin Specification Reference

Concrete code verification linking every specification artifact to its enforcement point.

| Specification ID | Title / Requirement | Enforcement File | Line |
|------------------|---------------------|------------------|------|
| `BR-SA-001` | Institute ID Immutability & Format | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L53) | L53 |
| `BR-SA-002` | Authorized Institute Domain Constraint | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L61) | L61 |
| `BR-SA-003` | Mandatory Category-Specific Data Completeness | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L72) | L72 |
| `BR-SA-004` | Account Deactivation Invariant | [`modules/system_admin/services/user_service.py`](../../modules/system_admin/services/user_service.py#L192) | L192 |
| `BR-SA-005` | Reversible Archival Window | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L174) | L174 |
| `BR-SA-006` | Unique User Identity Resolution | [`modules/system_admin/models/user_account.py`](../../modules/system_admin/models/user_account.py#L21) | L21 |
| `BR-SA-007` | Singular Role Occupancy Constraint | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L110) | L110 |
| `BR-SA-008` | Role Assignment Date Consistency | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L92) | L92 |
| `BR-SA-009` | Automatic Role Expiry and Status Transition | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L264) | L264 |
| `BR-SA-010` | User Type Role Eligibility Matrix | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L122) | L122 |
| `BR-SA-011` | Separation of Duties (SOD) Conflict Invariant | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L137) | L137 |
| `BR-SA-012` | Immediate vs Scheduled Role Activation | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L86) | L86 |
| `BR-SA-013` | Role Reassignment & Atomic Tenancy Transfer | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L119) | L119 |
| `BR-SA-014` | Immediate Revocation Effect | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L179) | L179 |
| `BR-SA-015` | Active User Account Precondition for Roles | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L47) | L47 |
| `BR-SA-016` | Emergency Role Revocation Override | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L183) | L183 |
| `BR-SA-017` | Role Tenure Extension Boundary | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L217) | L217 |
| `BR-SA-018` | Pre-Archival Deactivation Prerequisite | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L148) | L148 |
| `BR-SA-019` | Automated Retention Eligibility Evaluation | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L193) | L193 |
| `BR-SA-020` | Snapshot Immutability for Archived Accounts | [`modules/system_admin/services/archive_service.py`](../../modules/system_admin/services/archive_service.py#L62) | L62 |
| `BR-SA-021` | Hard Retention Lockout for Permanent Purge | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L199) | L199 |
| `BR-SA-022` | Dual Authorization for Permanent Purge | [`modules/system_admin/services/archive_service.py`](../../modules/system_admin/services/archive_service.py#L259) | L259 |
| `BR-SA-023` | Restoration Window Enforcement | [`modules/system_admin/services/archive_service.py`](../../modules/system_admin/services/archive_service.py#L109) | L109 |
| `BR-SA-024` | Historical Dataset Archival Integrity | [`modules/system_admin/services/archive_service.py`](../../modules/system_admin/services/archive_service.py#L151) | L151 |
| `BR-SA-025` | Non-Repudiable Append-Only Audit Logging | [`modules/system_admin/services/audit_service.py`](../../modules/system_admin/services/audit_service.py#L13) | L13 |
| `BR-SA-026` | Administrative Session Termination | [`modules/system_admin/services/audit_service.py`](../../modules/system_admin/services/audit_service.py#L47) | L47 |
| `BR-SA-027` | System Maintenance Mode Authorization | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L207) | L207 |
| `BR-SA-028` | Automated Database Backup Scheduling | [`modules/system_admin/models/archive.py`](../../modules/system_admin/models/archive.py#L37) | L37 |
| `BR-SA-029` | Comprehensive Log Query and Audit Review | [`modules/system_admin/selectors/audit_selectors.py`](../../modules/system_admin/selectors/audit_selectors.py#L10) | L10 |
| `BR-SA-030` | Bulk Action Batch Size Constraint | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L216) | L216 |
| `BR-SA-031` | Privileged Action Re-Authentication | [`modules/system_admin/services/archive_service.py`](../../modules/system_admin/services/archive_service.py#L239) | L239 |
| `BR-SA-032` | Granular Access Rights Matrix | [`modules/system_admin/registry.py`](../../modules/system_admin/registry.py#L16) | L16 |
| `BR-SA-033` | Log Export Security and Redaction | [`modules/system_admin/selectors/audit_selectors.py`](../../modules/system_admin/selectors/audit_selectors.py#L10) | L10 |
| `BR-SA-034` | Security Anomaly Detection and Notification | [`modules/system_admin/selectors/dashboard_selectors.py`](../../modules/system_admin/selectors/dashboard_selectors.py#L49) | L49 |
| `BR-SA-035` | Super Admin Authority Boundary | [`modules/system_admin/domain/rules.py`](../../modules/system_admin/domain/rules.py#L209) | L209 |
| `UC-SA-001` | Create User Account | [`modules/system_admin/api/views/user_views.py`](../../modules/system_admin/api/views/user_views.py#L78) | L78 |
| `UC-SA-002` | Bulk User Onboarding | [`modules/system_admin/api/views/user_views.py`](../../modules/system_admin/api/views/user_views.py#L236) | L236 |
| `UC-SA-003` | View User Profile Directory | [`modules/system_admin/api/views/user_views.py`](../../modules/system_admin/api/views/user_views.py#L46) | L46 |
| `UC-SA-004` | Update User Profile | [`modules/system_admin/services/user_service.py`](../../modules/system_admin/services/user_service.py#L129) | L129 |
| `UC-SA-005` | Deactivate User Account | [`modules/system_admin/services/user_service.py`](../../modules/system_admin/services/user_service.py#L192) | L192 |
| `UC-SA-006` | Reactivate User Account | [`modules/system_admin/services/user_service.py`](../../modules/system_admin/services/user_service.py#L223) | L223 |
| `UC-SA-007` | View Role Directory & Hierarchy | [`modules/system_admin/api/views/role_views.py`](../../modules/system_admin/api/views/role_views.py#L50) | L50 |
| `UC-SA-008` | Assign Role to User | [`modules/system_admin/api/views/role_views.py`](../../modules/system_admin/api/views/role_views.py#L73) | L73 |
| `UC-SA-009` | Reassign Role | [`modules/system_admin/api/views/role_views.py`](../../modules/system_admin/api/views/role_views.py#L111) | L111 |
| `UC-SA-010` | Revoke Role Assignment | [`modules/system_admin/api/views/role_views.py`](../../modules/system_admin/api/views/role_views.py#L141) | L141 |
| `UC-SA-011` | Extend Role Validity | [`modules/system_admin/api/views/role_views.py`](../../modules/system_admin/api/views/role_views.py#L167) | L167 |
| `UC-SA-012` | Monitor Expiring Roles | [`modules/system_admin/selectors/role_selectors.py`](../../modules/system_admin/selectors/role_selectors.py#L91) | L91 |
| `UC-SA-013` | Process Role Expiries | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L264) | L264 |
| `UC-SA-018` | Archive User Account | [`modules/system_admin/api/views/archive_views.py`](../../modules/system_admin/api/views/archive_views.py#L88) | L88 |
| `UC-SA-019` | Restore Archived User | [`modules/system_admin/api/views/archive_views.py`](../../modules/system_admin/api/views/archive_views.py#L114) | L114 |
| `UC-SA-020` | View Archival Records | [`modules/system_admin/api/views/archive_views.py`](../../modules/system_admin/api/views/archive_views.py#L54) | L54 |
| `UC-SA-021` | Archive Historical Dataset | [`modules/system_admin/api/views/archive_views.py`](../../modules/system_admin/api/views/archive_views.py#L138) | L138 |
| `UC-SA-022` | Request Permanent Purge | [`modules/system_admin/api/views/archive_views.py`](../../modules/system_admin/api/views/archive_views.py#L170) | L170 |
| `UC-SA-023` | Authorize Permanent Purge (Dual Auth) | [`modules/system_admin/api/views/archive_views.py`](../../modules/system_admin/api/views/archive_views.py#L198) | L198 |
| `UC-SA-026` | View Immutable Audit Log | [`modules/system_admin/api/views/audit_views.py`](../../modules/system_admin/api/views/audit_views.py#L21) | L21 |
| `UC-SA-027` | Monitor Failed Login Attempts | [`modules/system_admin/api/views/audit_views.py`](../../modules/system_admin/api/views/audit_views.py#L51) | L51 |
| `UC-SA-028` | Manage Administrative Sessions | [`modules/system_admin/models/audit.py`](../../modules/system_admin/models/audit.py#L54) | L54 |
| `UC-SA-029` | View System Admin Dashboard | [`modules/system_admin/api/views/dashboard_views.py`](../../modules/system_admin/api/views/dashboard_views.py#L17) | L17 |
| `UC-SA-030` | Manage System Parameters | [`modules/system_admin/api/views/config_views.py`](../../modules/system_admin/api/views/config_views.py#L27) | L27 |
| `BW-SA-01` | User Account Lifecycle Workflow | [`modules/system_admin/domain/state_machines.py`](../../modules/system_admin/domain/state_machines.py#L7) | L7 |
| `BW-SA-02` | Bulk Onboarding Batch Processing | [`modules/system_admin/services/user_service.py`](../../modules/system_admin/services/user_service.py#L254) | L254 |
| `BW-SA-03` | Standard Role Assignment Workflow | [`modules/system_admin/domain/state_machines.py`](../../modules/system_admin/domain/state_machines.py#L21) | L21 |
| `BW-SA-04` | Time-Bound Role Automatic Expiry Workflow | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L264) | L264 |
| `BW-SA-05` | Role Tenancy Transfer & Reassignment | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L119) | L119 |
| `BW-SA-06` | Emergency Role Revocation Workflow | [`modules/system_admin/services/role_service.py`](../../modules/system_admin/services/role_service.py#L183) | L183 |
| `BW-SA-07` | User Archival and Reversible Window Workflow | [`modules/system_admin/services/archive_service.py`](../../modules/system_admin/services/archive_service.py#L32) | L32 |
| `BW-SA-08` | Dual-Authorization Permanent Purge Workflow | [`modules/system_admin/domain/state_machines.py`](../../modules/system_admin/domain/state_machines.py#L41) | L41 |
| `BW-SA-09` | Historical Dataset Archival Workflow | [`modules/system_admin/services/archive_service.py`](../../modules/system_admin/services/archive_service.py#L151) | L151 |
| `CW-SA-01` | Cross-Cutting Immutable Audit Logging | [`modules/system_admin/services/audit_service.py`](../../modules/system_admin/services/audit_service.py#L13) | L13 |
| `CW-SA-02` | Security Monitoring and Failed Login Tracking | [`modules/system_admin/models/audit.py`](../../modules/system_admin/models/audit.py#L71) | L71 |
| `CW-SA-03` | System Parameter Configuration & Boundary Validation | [`modules/system_admin/services/configuration_service.py`](../../modules/system_admin/services/configuration_service.py#L14) | L14 |
