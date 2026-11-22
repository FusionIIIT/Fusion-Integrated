# Module 23: Super Admin (`superadmin`) — Architecture Blueprint

> **Specification Baseline:** `C:\Users\nikhi\OneDrive\Desktop\superAdmin` (v1.1 / v1.4 FINAL SYNCHRONIZED)
> **Module Code:** `superadmin` | **ID Prefix:** `SA-` | **Docs Folder:** `docs/23-superadmin/`
> **Environment:** `module-only` | **Reference Module:** `modules/placement`
> **Builder (Student 1):** Nikhil Jain (Roll No: 24BCS170, GitHub: `nikhiljain10905`)
> **Reviewer/Tester (Student 2):** Paladugu Taraka Ram (Roll No: 24BCS182)
> **Assigned Basis Workflow:** `BW-SA-08` (Archived User Reversibility Window Expiry)

## Executive Summary

This document establishes the formal architectural blueprint for the Super Admin module in `Fusion-Integrated`, prepared by Student 1 (Builder) and submitted to Student 2 (Reviewer/Tester) for formal written approval prior to writing application code.

Super Admin provides the administrative governance backbone of the institute ERP. It manages user account lifecycles 
(activation, deactivation, archival, reversibility window expiry, restoration), role assignments (immediate, future-dated, 
time-bound expiry, extension, handover/reassignment, revocation), bulk user operations, dual-authorized data purging, 
comprehensive immutable audit logging, and system parameter policy management.

---

## §3.1 (a) — Traceability Table

The traceability matrix in the spec package (`06_SA_Traceability_Matrix_v1.1_FINAL.xlsx`) left the mapping columns unpopulated. 
Below, every live Business Rule (35), Use Case (34), Workflow (12), Coherent Requirement (23), and Atomic Requirement (108) 
is mapped to its architectural layer and concrete enforcement point.

### 1. Business Rules (BR-SA-001 through BR-SA-035)

| Rule ID | Rule Title / Requirement | Layer | Planned Enforcement Point | Notes |
|---|---|---|---|---|
| `BR-SA-001` | Institute Identity Uniqueness and Immutability | `models/ & domain/` | `UserAccountRecord.clean(), UniqueConstraint(institute_id)` | Institute ID unique across Fusion; immutable once created. |
| `BR-SA-002` | Institute Email Validation | `domain/validators.py` | `validate_institute_email()` | Accepts only valid institute domain emails (e.g. @iiitdmj.ac.in). |
| `BR-SA-003` | User-Type Required Data | `domain/validators.py & models/` | `UserAccountRecord.clean()` | Student requires program/batch; Faculty/Staff requires dept & employee ID. |
| `BR-SA-004` | User Archival Eligibility | `domain/lifecycle.py & services/user_archive.py` | `can_archive_user()` | User must be deactivated; min deactivation interval elapsed; no pending transactions. |
| `BR-SA-005` | Archived User Reversibility Window | `domain/state_machine.py & services/user_archive.py` | `finalize_archived_user_expiry()` | Restoration permitted only during reversibility window; permanently non-restorable upon expiry (BW-SA-08). |
| `BR-SA-006` | Multiple Concurrent Roles | `domain/roles.py` | `validate_concurrent_roles()` | User may hold multiple concurrent additional roles if no policy conflict exists. |
| `BR-SA-007` | Singular Role Occupancy | `models/ & services/roles.py` | `UniqueConstraint on singular role assignment` | Singular roles (e.g. Dean, HOD) cannot be held by multiple active holders concurrently. |
| `BR-SA-008` | Role Assignment Dating | `domain/roles.py` | `validate_role_dates()` | valid_from <= valid_to; future-dated role starts in SCHEDULED status. |
| `BR-SA-009` | Automatic Role Activation and Expiry | `services/roles.py & schedule.py` | `activate_scheduled_roles(), expire_time_bound_roles()` | Celery tasks advance scheduled roles and expire elapsed time-bound roles automatically. |
| `BR-SA-010` | Role User-Type Eligibility | `domain/roles.py` | `validate_role_user_type_eligibility()` | Designation rank/office compatibility verified against user_type (student/faculty/staff). |
| `BR-SA-011` | Role Conflict Validation | `domain/roles.py` | `check_role_conflicts()` | Incompatible roles (e.g. student holding Dean Academic or exam auditor) rejected. |
| `BR-SA-012` | Reassignment Handover | `services/roles.py` | `reassign_role_with_handover()` | Role reassignment requires effective-date handover and pending-work transfer acknowledgment. |
| `BR-SA-013` | Previous Holder Audit Access | `selectors/scoping.py & contracts.py` | `get_previous_holder_audit_access()` | Previous role holder retains read-only access to records created during their tenure. |
| `BR-SA-014` | Role Revocation Handling | `services/roles.py` | `revoke_role()` | Immediate emergency or administrative role revocation; unassigns active permissions. |
| `BR-SA-015` | Automatic Revocation | `services/user_status.py` | `handle_account_deactivation_role_cascade()` | Account deactivation automatically revokes/suspends all held active additional roles. |
| `BR-SA-016` | Role Expiry Reminder and Extension | `services/roles.py & schedule.py` | `send_role_expiry_reminders(), extend_role_validity()` | Automated reminders before role expiry; authorized validity extension. |
| `BR-SA-017` | Historical Data Archival Eligibility | `domain/archive.py` | `can_archive_historical_data()` | Historical records eligible for archival once inactive and retention threshold met. |
| `BR-SA-018` | Backup Before Archival | `services/archive.py` | `verify_backup_before_archive()` | Archival requires verified snapshot backup before primary record modification. |
| `BR-SA-019` | Archive Retention Policy | `domain/archive.py & models/` | `HistoricalArchiveRecord.retention_policy` | Archive retention schedule enforced; retention-expired records marked purge-eligible. |
| `BR-SA-020` | Archived Data Access Mode | `selectors/archive.py` | `get_archived_records()` | Archived records are strictly read-only; no inline mutation permitted. |
| `BR-SA-021` | Permanent Purge Eligibility | `domain/purge.py` | `validate_purge_eligibility()` | Permanent purge only permitted for retention-expired archived records. |
| `BR-SA-022` | Dual Authorization for Purge | `services/purge.py` | `authorize_purge_request()` | Dual authorization: Super Admin request requires independent IT Head authorization. |
| `BR-SA-023` | Role Change Notification Timing | `services/notifications.py` | `emit_role_change_notification()` | Role assignment, reassignment, extension, and revocation emit immediate notifications. |
| `BR-SA-024` | Security Alert Threshold and Channels | `services/security.py` | `check_failed_login_threshold()` | Security alert emitted when consecutive failed logins exceed configured threshold. |
| `BR-SA-025` | Audit Immutability and Retention | `models/audit.py & services/audit.py` | `AuditLogRecord (append-only, no update/delete)` | Immutable audit records retained per institutional compliance policy. |
| `BR-SA-026` | Super Admin Data Isolation | `selectors/scoping.py` | `scope_superadmin_data()` | Super Admin administrative data isolated from tenant cross-contamination. |
| `BR-SA-027` | Super Admin Authentication and Session Controls | `api/permissions.py` | `SuperAdminSessionGuard` | Strict session management, idle timeout enforcement, and re-authentication. |
| `BR-SA-028` | No Self-Modification of Super Admin Status | `services/user_status.py` | `refuse_self_modification()` | Super Admin cannot deactivate or revoke their own superadmin status. |
| `BR-SA-029` | Critical Operation Reauthentication | `api/permissions.py` | `RequiresStepUpAuth` | Critical operations (archive, purge request, bulk deactivation) require step-up reauthentication. |
| `BR-SA-030` | Bulk Operation Limit | `services/bulk.py` | `validate_bulk_batch_size()` | Bulk operations capped at system maximum batch limit (e.g. 500 records). |
| `BR-SA-031` | Password Rotation | `services/security.py` | `enforce_password_rotation_policy()` | Credentials expire after configured max age; rotation prompted on first login. |
| `BR-SA-032` | Notification Channel Policy | `services/notifications.py` | `dispatch_notification()` | Notification channels selected based on severity and user preferences. |
| `BR-SA-033` | Audit Event Coverage and Record Content | `services/audit.py` | `log_audit_event()` | Mandatory audit event logging covering actor, action, target, timestamp, IP, outcome. |
| `BR-SA-034` | Active Role Selection and Permission Enforcement | `api/permissions.py` | `HasActiveRolePermission` | Only permissions of active_role are enforced; union of held roles prohibited. |
| `BR-SA-035` | Permitted System Configuration Boundary | `domain/system_config.py & models/` | `SystemParameterPolicy (effective-dated)` | System configuration parameters are versioned, effective-dated, and never edited in-place. |

### 2. Use Cases (UC-SA-001 through UC-SA-034)

| UC ID | Use Case Title | Actor | Layer | Planned Enforcement Point | Notes |
|---|---|---|---|---|---|
| `UC-SA-001` | Create Basic User | Super Admin | `api/views/users.py & services/users.py` | `create_user_account()` | Create basic user (Student, Faculty, Staff). |
| `UC-SA-002` | View User Profile | Super Admin | `api/views/users.py & selectors/users.py` | `get_user_profile()` | View basic user profile. |
| `UC-SA-003` | Update User Profile | Super Admin | `api/views/users.py & services/users.py` | `update_user_profile()` | Update editable user profile fields. |
| `UC-SA-004` | Deactivate User | Super Admin | `api/views/users.py & services/user_status.py` | `deactivate_user()` | Deactivate user account. |
| `UC-SA-005` | Reactivate User | Super Admin | `api/views/users.py & services/user_status.py` | `reactivate_user()` | Reactivate deactivated user account (BW-SA-06). |
| `UC-SA-006` | Bulk Create Users | Super Admin | `api/views/bulk.py & services/bulk.py` | `bulk_create_users()` | CSV batch user creation with pre-validation. |
| `UC-SA-007` | Bulk User Status Update | Super Admin | `api/views/bulk.py & services/bulk.py` | `bulk_update_user_status()` | Bulk user status update / deactivation. |
| `UC-SA-008` | Assign Role | Super Admin | `api/views/roles.py & services/roles.py` | `assign_role()` | Assign additional role with validity dates (BW-SA-03, BW-SA-04). |
| `UC-SA-009` | Reassign Role | Super Admin | `api/views/roles.py & services/roles.py` | `reassign_role()` | Reassign role with handover transfer. |
| `UC-SA-010` | Revoke Role | Super Admin | `api/views/roles.py & services/roles.py` | `revoke_role()` | Revoke held role assignment. |
| `UC-SA-011` | Extend Role Validity | Super Admin | `api/views/roles.py & services/roles.py` | `extend_role_validity()` | Extend validity of active role assignment (BW-SA-05). |
| `UC-SA-012` | View Role Metadata and Availability | Super Admin | `api/views/roles.py & selectors/roles.py` | `get_role_metadata()` | Read-only inspection of role definitions and holders. |
| `UC-SA-013` | Switch Active Role | Basic User | `api/views/session.py & services/session.py` | `switch_active_role()` | Basic user switches acting active role. |
| `UC-SA-014` | Access Module by Active Role | Basic User | `api/permissions.py & selectors/scoping.py` | `scope_module_access()` | Access module permitted by active role. |
| `UC-SA-015` | Archive User | Super Admin | `api/views/archive.py & services/user_archive.py` | `archive_user()` | Archive eligible deactivated user (BW-SA-08 Transition 1). |
| `UC-SA-016` | Archive Historical Data | Super Admin | `api/views/archive.py & services/archive.py` | `archive_historical_data()` | Archive inactive institutional data. |
| `UC-SA-017` | Search and View Archived Records | Super Admin | `api/views/archive.py & selectors/archive.py` | `search_archived_records()` | Search and view read-only archive records. |
| `UC-SA-018` | Restore Archived User | Super Admin | `api/views/archive.py & services/user_archive.py` | `restore_archived_user()` | Restore user within reversibility window (BW-SA-07). |
| `UC-SA-019` | Restore Archived Historical Data | Super Admin | `api/views/archive.py & services/archive.py` | `restore_historical_data()` | Restore archived historical dataset (BW-SA-09). |
| `UC-SA-020` | Generate and Export Archive Report | Super Admin | `api/views/reports.py & services/reports.py` | `generate_archive_report()` | Generate and export archive status report. |
| `UC-SA-021` | Export Archived Data for External Storage | Super Admin | `api/views/archive.py & services/archive.py` | `export_archived_data()` | Export archive package for external storage. |
| `UC-SA-022` | Request Permanent Data Purge | Super Admin | `api/views/purge.py & services/purge.py` | `request_permanent_purge()` | Request permanent data purge (BW-SA-01, BW-SA-02). |
| `UC-SA-023` | Authorize Permanent Data Purge | IT Head | `api/views/purge.py & services/purge.py` | `authorize_permanent_purge()` | IT Head dual-authorization for purge (BW-SA-01, BW-SA-02). |
| `UC-SA-024` | View Audit Log | Super Admin | `api/views/audit.py & selectors/audit.py` | `get_audit_logs()` | Search and view immutable audit logs. |
| `UC-SA-025` | Generate Audit Report | Super Admin | `api/views/audit.py & services/audit.py` | `generate_audit_report()` | Generate compliance audit log export report. |
| `UC-SA-026` | View Super Admin Dashboard | Super Admin | `api/views/dashboard.py & selectors/dashboard.py` | `get_dashboard_metrics()` | Super Admin administrative oversight dashboard. |
| `UC-SA-027` | Configure Permitted System Parameters | Super Admin | `api/views/system_config.py & services/system_config.py` | `configure_system_parameters()` | Configure versioned, effective-dated system parameters. |
| `UC-SA-028` | Activate Scheduled Role Assignment | N.A. — Event-triggered | `tasks/roles.py & schedule.py` | `activate_scheduled_roles_task()` | Event/Beat: Activate scheduled role assignment (BW-SA-04). |
| `UC-SA-029` | Expire Time-Bound Role | N.A. — Event-triggered | `tasks/roles.py & schedule.py` | `expire_time_bound_roles_task()` | Event/Beat: Expire elapsed role assignment (BW-SA-03). |
| `UC-SA-030` | Send Role-Expiry Reminder | N.A. — Event-triggered | `tasks/roles.py & schedule.py` | `send_role_reminders_task()` | Event/Beat: Send notification for upcoming role expiry. |
| `UC-SA-031` | Finalize Archived User as Permanently Non-Restorable | N.A. — Event-triggered | `tasks/archive.py & schedule.py` | `finalize_archived_user_expiry_task()` | Event/Beat: Finalize archived user as non-restorable (BW-SA-08 Transition 2). |
| `UC-SA-032` | Process Failed-Login Threshold Alert | N.A. — Event-triggered | `services/security.py & tasks/security.py` | `process_failed_login_alert()` | Event: Process failed login alert threshold. |
| `UC-SA-033` | Authenticate Super Admin and Establish Session | Super Admin | `api/views/session.py & services/session.py` | `authenticate_superadmin()` | Authenticate Super Admin and establish privileged session. |
| `UC-SA-034` | Terminate Inactive Super Admin Session | N.A. — Event-triggered | `tasks/session.py & schedule.py` | `terminate_inactive_sessions_task()` | Event/Beat: Terminate idle Super Admin sessions. |

### 3. Workflows (BW-SA-01 through BW-SA-09, CW-SA-01 through CW-SA-03)

| Workflow ID | Title | Type | Key Participants | Primary Trigger / Outcome | Assigned Focus |
|---|---|---|---|---|---|
| `BW-SA-01` | Permanent Data Purge — Approved Path | Basis | Super Admin, IT Head | Super Admin requests purge; IT Head authorizes; data permanently purged. | Supporting |
| `BW-SA-02` | Permanent Data Purge — Rejected Path | Basis | Super Admin, IT Head | Super Admin requests purge; IT Head rejects; data remains archived. | Supporting |
| `CW-SA-01` | Permanent Data Purge Authorization Lifecycle | Composite | Super Admin, IT Head | Composition of purge request, dual review, and terminal purge/rejection. | Supporting |
| `BW-SA-03` | Immediate Time-Bound Role Assignment to Expiry | Basis | Super Admin, System | Active role assigned immediately; Celery beat expires it at valid_to. | Supporting |
| `BW-SA-04` | Future-Dated Role Assignment to Expiry | Basis | Super Admin, System | Scheduled role assigned; activated on valid_from; expired on valid_to. | Supporting |
| `BW-SA-05` | Role Validity Extension — One Traversal | Basis | Super Admin, System | Active role extended with new valid_to; expires at extended date. | Supporting |
| `CW-SA-02` | Time-Bound Role Validity Lifecycle | Composite | Super Admin, System | Composition of role scheduling, activation, extension, and expiry. | Supporting |
| `BW-SA-06` | Deactivated User Reactivation | Basis | Super Admin | Deactivated account returned to active status upon authorization. | Supporting |
| `BW-SA-07` | Archived User Restoration Within Reversible Window | Basis | Super Admin | Archived account restored to active within configured reversibility period. | Supporting |
| `BW-SA-08` | Archived User Reversibility Window Expiry | Basis | Super Admin, System | Archived account reaches reversibility expiry; becomes permanently non-restorable. | **ASSIGNED BASIS WORKFLOW** |
| `CW-SA-03` | Deactivated User Resolution and Archive Lifecycle | Composite | Super Admin, System | Composition of deactivation, archival, restoration or permanent non-restorable expiry. | Supporting Lifecycle |
| `BW-SA-09` | Historical Data Archive and Restore | Basis | Super Admin | Inactive historical dataset archived with backup and restored upon request. | Supporting |

### 4. Coherent Requirements (CFR-SA-001 through CFR-SA-023)

| CFR ID | CFR Name | Statement | Architectural Layer | Primary Enforcement |
|---|---|---|---|---|
| `CFR-SA-001` | Create Basic User Account | The system shall enable an authenticated Super Admin to create a valid Student, Faculty, or Staff basic-user account, validate institutional identity, establish initial credentials and baseline dashboard access, and issue first-login guidance. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-002` | View and Maintain Basic User Profile | The system shall enable a Super Admin to view permitted basic-user profile data and update only editable profile information while preserving immutable identity fields. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-003` | Manage User Activation Status | The system shall enable a Super Admin to deactivate and, when policy permits, reactivate basic-user accounts with controlled status transitions. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-004` | Execute Bulk User Operations | The system shall support PS-authorized bulk user operations—CSV batch creation, bulk deactivation, and permitted bulk status updates—with pre-validation, bounded size, result reporting, detailed logs, and completion notification. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-005` | Inspect Role Definitions and Availability | The system shall provide read-only access to system-maintained role definitions, assignment metadata, availability, and current/past holder information needed for role administration. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-006` | Assign Additional Roles | The system shall enable a Super Admin to assign an additional role to an eligible basic user with required scope, dates, and reason; enforce eligibility, singularity, and conflict rules; support concurrent roles and scheduled activation; notify the affected user; and preserve assignment history. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-007` | Reassign Existing Role | The system shall enable controlled reassignment of an existing role to a new eligible holder with effective-date handover, pending-work transfer, notifications, prior-holder audit access, and history preservation. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-008` | Revoke Role | The system shall enable controlled early or emergency role revocation and automatically remove role access when account deactivation requires it, while handling pending work, notifying affected parties, and preserving audit evidence. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-009` | Manage Time-Bound Role Validity | The system shall manage time-bound role validity by tracking validity, reminding before expiry, allowing extension, and automatically expiring or inactivating the role at the applicable end date. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-010` | Switch Active Role and Enforce Access | The system shall allow a user with multiple valid roles to view and select the active role and shall authorize module access only according to the active role permissions. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-011` | Archive User Account | The system shall archive only eligible deactivated users, capture required archival data, disable access, roles, and credentials, move retained information to the archive, and preserve policy-required history. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-012` | Restore or Permanently Finalize Archived User | The system shall permit archived-user restoration only within the configured reversible period with required authorization and shall make the archived account permanently non-restorable when that period expires. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-013` | Archive Historical Data | The system shall archive eligible historical data by category and date range only after policy and dependency checks, authenticated confirmation, and backup, and shall generate an archival summary. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-014` | Access, Report, and Export Archived Records | The system shall provide read-only search and retrieval of permitted archived records and support archive reporting and authorized exports without violating data-isolation policy. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-015` | Restore Archived Historical Data | The system shall restore archived historical data to the active system only when the required approval exists. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-016` | Permanently Purge Archived Data | The system shall permit permanent purge of archived data only after retention expiry and dual authorization by Super Admin and IT Head. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-017` | Maintain Audit Evidence and History | The system shall create, structure, preserve, and protect comprehensive audit evidence and role/user lifecycle history for Super Admin operations. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-018` | Audit Reporting and Administrative Monitoring | The system shall provide read-only audit inspection, configurable audit reporting and export, and the defined Super Admin dashboard and monitoring views. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-019` | Deliver Administrative Notifications | The system shall deliver the defined account, role, bulk-operation, archival, and security notifications to the required recipients through supported channels and timing. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-020` | Protect Administrative Access Boundary | The system shall enforce the Super Admin administrative boundary by preventing access to prohibited operational content and preventing self-modification of Super Admin status. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-021` | Secure Super Admin Authentication and Sessions | The system shall secure Super Admin authentication and sessions through configured password controls, mandatory two-factor authentication, optional IP-whitelist enforcement, single-session and inactivity controls, failed-login monitoring, session logging, and password rotation. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-022` | Confirm Critical Operations | The system shall require authenticated confirmation before executing operations designated critical. | `services/` & `api/` | `modules/superadmin/` |
| `CFR-SA-023` | Configure Only Permitted System Parameters | The system shall allow configuration only of the limited system-wide parameters allocated to Super Admin control and shall deny changes to excluded module, academic, financial, and operational-workflow configuration. | `services/` & `api/` | `modules/superadmin/` |

### 5. Atomic Requirements Summary (AFR-SA-001 through AFR-SA-082, 108 total)

All 108 AFRs from `02_SA_Requirement_Registry_CFR_AFR_v1.1_FINAL.docx` are mapped to the domain model, services, and API endpoints. 
Key highlights include:

- **User Identity & Immutability:** `AFR-SA-001` through `AFR-SA-011` -> `UserAccountRecord`, `validate_institute_email()`, `clean()` immutability guards.
- **Activation & Archival:** `AFR-SA-012` through `AFR-SA-014` -> `UserAccountRecord.activation_status`, `user_archive.py`.
- **Bulk Operations:** `AFR-SA-015` through `AFR-SA-020`, `AFR-SA-078` -> `services/bulk.py`, pre-validation batches, results reporting.
- **Role Administration:** `AFR-SA-021` through `AFR-SA-044B` -> `RoleAssignmentRecord`, `roles.py`, `schedule.py`.
- **Archive & Purge:** `AFR-SA-045` through `AFR-SA-063` -> `HistoricalArchiveRecord`, `PurgeRequestRecord`, dual authorization.
- **Audit & Governance:** `AFR-SA-064` through `AFR-SA-077`, `AFR-SA-079` through `AFR-SA-082` -> `AuditLogRecord`, immutable storage, session timeout guards.

---

## §3.2 (b) — Domain Model and Database Constraints

In strict compliance with **ADR-0013** (Decoupled Module Storage & Independent Bounded Contexts):

- **Zero Cross-Module Foreign Keys:** No ForeignKey references tables in `fusionlab` (ERP), `fusion_system_db` (IAM), or other modules.
- **Integer User References:** All user references are stored as integer `user_id` (`core/db/mixins.py::UserScopedModel`).
- **No Auth Tables Duplicated:** Super Admin owns its business models; permissions are published via `registry.py` to the IAM.

```python
# modules/superadmin/models/user_account.py

from django.db import models
from core.db.mixins import TimeStampedModel


class UserActivationStatus(models.TextChoices):

    ACTIVE = 'ACTIVE', 'Active'

    DEACTIVATED = 'DEACTIVATED', 'Deactivated'

    ARCHIVED_REVERSIBLE = 'ARCHIVED_REVERSIBLE', 'Archived (Reversible)'

    ARCHIVED_PERMANENT = 'ARCHIVED_PERMANENT', 'Archived (Permanently Non-Restorable)'


class UserType(models.TextChoices):

    STUDENT = 'STUDENT', 'Student'

    FACULTY = 'FACULTY', 'Faculty'

    STAFF = 'STAFF', 'Staff'


class UserAccountRecord(TimeStampedModel):

    user_id = models.IntegerField(unique=True, db_index=True)

    institute_id = models.CharField(max_length=64, unique=True, db_index=True)

    email = models.EmailField(unique=True, db_index=True)

    user_type = models.CharField(max_length=16, choices=UserType.choices)

    activation_status = models.CharField(max_length=32, choices=UserActivationStatus.choices, default=UserActivationStatus.ACTIVE, db_index=True)

    deactivation_date = models.DateTimeField(null=True, blank=True)

    archival_date = models.DateTimeField(null=True, blank=True)

    reversibility_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    department = models.CharField(max_length=128, blank=True, default='')

    program = models.CharField(max_length=64, blank=True, default='')

    batch = models.CharField(max_length=32, blank=True, default='')

    deactivation_reason = models.TextField(blank=True, default='')

    archival_reason = models.TextField(blank=True, default='')


    class Meta:

        db_table = 'superadmin_user_account'

        indexes = [

            models.Index(fields=['activation_status', 'reversibility_expires_at'], name='sa_usr_status_exp_idx'),

            models.Index(fields=['user_type', 'activation_status'], name='sa_usr_type_status_idx'),

        ]

        constraints = [

            models.CheckConstraint(

                check=models.Q(activation_status__in=UserActivationStatus.values),

                name='sa_usr_valid_status_check'

            ),

        ]
```

```python
# modules/superadmin/models/role_assignment.py

class RoleAssignmentStatus(models.TextChoices):

    SCHEDULED = 'SCHEDULED', 'Scheduled'

    ACTIVE = 'ACTIVE', 'Active'

    EXTENDED = 'EXTENDED', 'Extended'

    EXPIRED = 'EXPIRED', 'Expired'

    REVOKED = 'REVOKED', 'Revoked'

    REASSIGNED = 'REASSIGNED', 'Reassigned'


class RoleAssignmentRecord(TimeStampedModel):

    user_id = models.IntegerField(db_index=True)

    role_name = models.CharField(max_length=128, db_index=True)

    scope_type = models.CharField(max_length=64, blank=True, default='')

    scope_id = models.CharField(max_length=64, blank=True, default='')

    valid_from = models.DateTimeField(db_index=True)

    valid_to = models.DateTimeField(null=True, blank=True, db_index=True)

    status = models.CharField(max_length=32, choices=RoleAssignmentStatus.choices, default=RoleAssignmentStatus.SCHEDULED, db_index=True)

    is_singular = models.BooleanField(default=False)

    assigned_by_user_id = models.IntegerField()

    assignment_reason = models.TextField(blank=True, default='')


    class Meta:

        db_table = 'superadmin_role_assignment'

        indexes = [

            models.Index(fields=['user_id', 'status'], name='sa_role_usr_status_idx'),

            models.Index(fields=['role_name', 'status'], name='sa_role_name_status_idx'),

            models.Index(fields=['status', 'valid_to'], name='sa_role_status_vto_idx'),

            models.Index(fields=['status', 'valid_from'], name='sa_role_status_vfrom_idx'),

        ]

        constraints = [

            models.UniqueConstraint(

                fields=['role_name'],

                condition=models.Q(is_singular=True, status__in=['ACTIVE', 'EXTENDED']),

                name='sa_singular_role_unique_active_holder'

            ),

        ]
```

```python
# modules/superadmin/models/archive_purge.py

class ArchiveStatus(models.TextChoices):

    ARCHIVED = 'ARCHIVED', 'Archived'

    RESTORED = 'RESTORED', 'Restored'

    PURGED = 'PURGED', 'Purged'


class HistoricalArchiveRecord(TimeStampedModel):

    entity_type = models.CharField(max_length=64, db_index=True)

    record_identifier = models.CharField(max_length=128, db_index=True)

    payload = models.JSONField()

    backup_reference = models.CharField(max_length=255)

    retention_period_days = models.IntegerField(default=1825)

    purge_eligible_at = models.DateTimeField(db_index=True)

    status = models.CharField(max_length=32, choices=ArchiveStatus.choices, default=ArchiveStatus.ARCHIVED, db_index=True)

    archived_by_user_id = models.IntegerField()


    class Meta:

        db_table = 'superadmin_historical_archive'


class PurgeRequestStatus(models.TextChoices):

    PENDING_AUTHORIZATION = 'PENDING', 'Pending Dual Authorization'

    AUTHORIZED = 'AUTHORIZED', 'Authorized'

    REJECTED = 'REJECTED', 'Rejected'

    COMPLETED = 'COMPLETED', 'Purge Executed'


class PurgeRequestRecord(TimeStampedModel):

    archive_record_id = models.IntegerField(db_index=True)

    requested_by_user_id = models.IntegerField()

    request_reason = models.TextField()

    status = models.CharField(max_length=32, choices=PurgeRequestStatus.choices, default=PurgeRequestStatus.PENDING_AUTHORIZATION, db_index=True)

    authorized_by_user_id = models.IntegerField(null=True, blank=True)

    authorized_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True, default='')


    class Meta:

        db_table = 'superadmin_purge_request'
```

```python
# modules/superadmin/models/audit_system.py

class AuditLogRecord(TimeStampedModel):

    event_type = models.CharField(max_length=128, db_index=True)

    actor_user_id = models.IntegerField(db_index=True)

    target_entity = models.CharField(max_length=64, db_index=True)

    target_id = models.CharField(max_length=128, db_index=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    action_details = models.JSONField(default=dict)

    is_immutable = models.BooleanField(default=True)


    class Meta:

        db_table = 'superadmin_audit_log'

        indexes = [

            models.Index(fields=['actor_user_id', 'created_at'], name='sa_aud_actor_dt_idx'),

            models.Index(fields=['event_type', 'created_at'], name='sa_aud_evt_dt_idx'),

        ]


class SystemParameterPolicy(TimeStampedModel):

    parameter_key = models.CharField(max_length=128, db_index=True)

    parameter_value = models.JSONField()

    version = models.IntegerField(default=1)

    effective_from = models.DateTimeField(db_index=True)

    effective_to = models.DateTimeField(null=True, blank=True, db_index=True)

    is_active = models.BooleanField(default=True, db_index=True)

    updated_by_user_id = models.IntegerField()


    class Meta:

        db_table = 'superadmin_system_parameter'

        constraints = [

            models.UniqueConstraint(

                fields=['parameter_key', 'version'],

                name='sa_sys_param_key_ver_unique'

            ),

        ]
```

---

## §3.3 (c) — Declarative State Machine Table

State transitions are modeled as a declarative dictionary data structure: `(current_state, event, actor) -> (guard, next_state)`. 
Illegal transitions are inexpressible and raise `IllegalStateTransitionError`.

### 1. User Account Lifecycle (Focus Workflow: `BW-SA-08`)

| From State | Event / Trigger | Actor | Guard / Condition | Resulting State | Cites |
|---|---|---|---|---|---|
| `ACTIVE` | `DEACTIVATE` | Super Admin | Pending transactions cleared; reason provided | `DEACTIVATED` | `UC-SA-004`, `BR-SA-015` |
| `DEACTIVATED` | `REACTIVATE` | Super Admin | Authorized justification present | `ACTIVE` | `UC-SA-005`, `BW-SA-06` |
| `DEACTIVATED` | `ARCHIVE` | Super Admin | Min deactivation interval met (e.g. 30 days); step-up auth passed | `ARCHIVED_REVERSIBLE` | `UC-SA-015`, `BR-SA-004`, `BW-SA-08` T1 |
| `ARCHIVED_REVERSIBLE` | `RESTORE` | Super Admin | `now() <= reversibility_expires_at`; authorized justification | `ACTIVE` | `UC-SA-018`, `BR-SA-005`, `BW-SA-07` |
| `ARCHIVED_REVERSIBLE` | `EXPIRE_REVERSIBILITY` | System / Celery Beat | `now() > reversibility_expires_at`; no restoration in progress | `ARCHIVED_PERMANENT` | `UC-SA-031`, `BR-SA-005`, `BW-SA-08` T2 |
| `ARCHIVED_PERMANENT` | `RESTORE` | Any Actor | **ILLEGAL** — account is permanently non-restorable | **REFUSED (409)** | `BR-SA-005` |
| `ACTIVE` | `ARCHIVE` | Any Actor | **ILLEGAL** — must be deactivated first | **REFUSED (409)** | `BR-SA-004` |

### 2. Time-Bound Role Assignment Lifecycle (`BW-SA-03`, `BW-SA-04`, `BW-SA-05`, `CW-SA-02`)

| From State | Event / Trigger | Actor | Guard / Condition | Resulting State | Cites |
|---|---|---|---|---|---|
| `[NONE]` | `ASSIGN_FUTURE` | Super Admin | `valid_from > now()`; user eligible; no conflict | `SCHEDULED` | `UC-SA-008`, `BW-SA-04` |
| `[NONE]` | `ASSIGN_IMMEDIATE` | Super Admin | `valid_from <= now()`; user eligible; no conflict | `ACTIVE` | `UC-SA-008`, `BW-SA-03` |
| `SCHEDULED` | `ACTIVATE_SCHEDULED` | System / Celery Beat | `now() >= valid_from`; not superseded by revocation | `ACTIVE` | `UC-SA-028`, `BW-SA-04` |
| `ACTIVE` | `EXTEND` | Super Admin | `now() < valid_to`; `new_valid_to > valid_to`; justified | `EXTENDED` | `UC-SA-011`, `BW-SA-05` |
| `ACTIVE` / `EXTENDED` | `EXPIRE` | System / Celery Beat | `now() >= valid_to`; not extended or revoked | `EXPIRED` | `UC-SA-029`, `BW-SA-03` |
| `SCHEDULED` / `ACTIVE` | `REVOKE` | Super Admin / System | Administrative revocation or account deactivation | `REVOKED` | `UC-SA-010`, `BR-SA-014`, `BR-SA-015` |
| `ACTIVE` | `REASSIGN` | Super Admin | Successor eligible; handover completed | `REASSIGNED` | `UC-SA-009`, `BR-SA-012` |

### 3. Permanent Data Purge Lifecycle (`BW-SA-01`, `BW-SA-02`, `CW-SA-01`)

| From State | Event / Trigger | Actor | Guard / Condition | Resulting State | Cites |
|---|---|---|---|---|---|
| `ARCHIVED` | `REQUEST_PURGE` | Super Admin | `now() >= purge_eligible_at`; step-up auth verified | `PENDING_AUTHORIZATION` | `UC-SA-022`, `BR-SA-021` |
| `PENDING_AUTHORIZATION` | `AUTHORIZE_PURGE` | IT Head | `actor != requester`; verified institutional sign-off | `PURGED` | `UC-SA-023`, `BR-SA-022`, `BW-SA-01` |
| `PENDING_AUTHORIZATION` | `REJECT_PURGE` | IT Head | Rejection reason recorded | `REJECTED` | `UC-SA-023`, `BW-SA-02` |

---

## §3.4 (d) — Permission List and RBAC Model

In strict compliance with `docs/02-iam/rbac-model.md`:

- Format: `<module_code>.<singular_noun>.<verb>`.
- Verbs chosen exclusively from the closed vocabulary: `view`, `create`, `update`, `delete`, `approve`, `publish`, `review`, `assign`, `revoke`, `export`, `import`, `restore`, `manage`.
- Scoping is handled in `selectors/scoping.py` (narrowing querysets to return 404, never 403).

```python
# modules/superadmin/registry.py

MODULE = {

    'code': 'superadmin',

    'label': 'Super Admin',

    'icon': 'ShieldCheck',

    'base_path': '/superadmin',

    'nav_section': 'Administration',

    'sort_order': 1,

    'status': 'active',

}


NAV_ITEMS = [

    {'code': 'superadmin.dashboard', 'label': 'Dashboard', 'icon': 'ChartBar', 'to': '/superadmin/dashboard', 'required_permission': 'superadmin.user.view', 'sort_order': 10},

    {'code': 'superadmin.users', 'label': 'User Accounts', 'icon': 'Users', 'to': '/superadmin/users', 'required_permission': 'superadmin.user.view', 'sort_order': 20},

    {'code': 'superadmin.roles', 'label': 'Role Assignments', 'icon': 'IdentificationBadge', 'to': '/superadmin/roles', 'required_permission': 'superadmin.role.view', 'sort_order': 30},

    {'code': 'superadmin.archive', 'label': 'Archive & Restoration', 'icon': 'Archive', 'to': '/superadmin/archive', 'required_permission': 'superadmin.archive.view', 'sort_order': 40},

    {'code': 'superadmin.purge', 'label': 'Purge Authorizations', 'icon': 'Trash', 'to': '/superadmin/purge', 'required_permission': 'superadmin.purge.approve', 'sort_order': 50},

    {'code': 'superadmin.audit', 'label': 'Audit Logs', 'icon': 'Scroll', 'to': '/superadmin/audit', 'required_permission': 'superadmin.audit_log.view', 'sort_order': 60},

    {'code': 'superadmin.config', 'label': 'System Policy', 'icon': 'GearSix', 'to': '/superadmin/config', 'required_permission': 'superadmin.system_config.view', 'sort_order': 70},

]


PERMISSIONS = [

    ('superadmin.user.view', 'View user accounts and profiles'),

    ('superadmin.user.create', 'Create new basic user accounts'),

    ('superadmin.user.update', 'Update user profiles and statuses'),

    ('superadmin.user.delete', 'Deactivate user accounts'),

    ('superadmin.user.restore', 'Reactivate or restore user accounts'),

    ('superadmin.user.import', 'Bulk import user accounts from CSV'),

    ('superadmin.user.export', 'Export user account directories'),

    ('superadmin.role.view', 'Inspect role definitions and assignments'),

    ('superadmin.role.assign', 'Assign or reassign roles to users'),

    ('superadmin.role.revoke', 'Revoke held role assignments'),

    ('superadmin.role.update', 'Extend validity of active role assignments'),

    ('superadmin.archive.view', 'Search and inspect archived records'),

    ('superadmin.archive.create', 'Archive deactivated users or historical data'),

    ('superadmin.archive.restore', 'Restore reversible archived users or data'),

    ('superadmin.archive.export', 'Export archive status reports'),

    ('superadmin.purge.create', 'Request permanent data purge'),

    ('superadmin.purge.approve', 'Authorize permanent data purge (IT Head)'),

    ('superadmin.audit_log.view', 'Inspect security and audit event logs'),

    ('superadmin.audit_log.export', 'Export compliance audit reports'),

    ('superadmin.system_config.view', 'View system parameter configurations'),

    ('superadmin.system_config.update', 'Update system parameter policies'),

]


SYSTEM_PERMISSIONS = [

    'superadmin.role.assign',

    'superadmin.role.revoke',

    'superadmin.user.update',

]


_SUPER_ADMIN_PERMISSIONS = [

    'superadmin.user.view', 'superadmin.user.create', 'superadmin.user.update',

    'superadmin.user.delete', 'superadmin.user.restore', 'superadmin.user.import',

    'superadmin.user.export', 'superadmin.role.view', 'superadmin.role.assign',

    'superadmin.role.revoke', 'superadmin.role.update', 'superadmin.archive.view',

    'superadmin.archive.create', 'superadmin.archive.restore', 'superadmin.archive.export',

    'superadmin.purge.create', 'superadmin.audit_log.view', 'superadmin.audit_log.export',

    'superadmin.system_config.view', 'superadmin.system_config.update',

]


_IT_HEAD_PERMISSIONS = [

    'superadmin.purge.approve',

    'superadmin.audit_log.view',

]


ROLE_GRANTS = {

    'Super Admin': _SUPER_ADMIN_PERMISSIONS,

    'super_admin': _SUPER_ADMIN_PERMISSIONS,

    'iam_admin': _SUPER_ADMIN_PERMISSIONS,

    'IT Head': _IT_HEAD_PERMISSIONS,

    'Director': _IT_HEAD_PERMISSIONS,

}
```

---

## §3.5 (e) — Endpoint List and Route Guarding

All endpoints live under `/api/v1/superadmin/` and enforce both `HasModuleGrant('superadmin')` and fine-grained `HasPermission`.

| HTTP Method | Endpoint Path | Required Permission | Step-Up Auth | Request / Body | Response Status & Body | Enforces |
|---|---|---|---|---|---|---|
| `GET` | `/api/v1/superadmin/users/` | `superadmin.user.view` | No | `?search=&type=&status=` | `200 OK` `[UserAccountSummary]` | `UC-SA-002`, `BR-SA-026` |
| `POST` | `/api/v1/superadmin/users/` | `superadmin.user.create` | No | `{institute_id, email, user_type, ...}` | `201 Created` `{user_id, ...}` | `UC-SA-001`, `BR-SA-001`, `BR-SA-002`, `BR-SA-003` |
| `GET` | `/api/v1/superadmin/users/{user_id}/` | `superadmin.user.view` | No | None | `200 OK` `{user_id, institute_id, ...}` | `UC-SA-002`, `BR-SA-026` |
| `PATCH` | `/api/v1/superadmin/users/{user_id}/` | `superadmin.user.update` | No | `{department, program, ...}` | `200 OK` `{updated user}` | `UC-SA-003`, `BR-SA-001` (immutable id) |
| `POST` | `/api/v1/superadmin/users/{user_id}/deactivate/` | `superadmin.user.delete` | Yes | `{reason}` | `200 OK` `{status: 'DEACTIVATED'}` | `UC-SA-004`, `BR-SA-015`, `BR-SA-028` |
| `POST` | `/api/v1/superadmin/users/{user_id}/reactivate/` | `superadmin.user.restore` | No | `{reason}` | `200 OK` `{status: 'ACTIVE'}` | `UC-SA-005`, `BW-SA-06` |
| `POST` | `/api/v1/superadmin/users/bulk-create/` | `superadmin.user.import` | Yes | `multipart/form-data CSV` | `200 OK` `{total, created, errors}` | `UC-SA-006`, `BR-SA-030` |
| `POST` | `/api/v1/superadmin/users/bulk-status/` | `superadmin.user.update` | Yes | `{user_ids: [], action, reason}` | `200 OK` `{updated_count}` | `UC-SA-007`, `BR-SA-030` |
| `GET` | `/api/v1/superadmin/roles/` | `superadmin.role.view` | No | `?user_id=&status=&role_name=` | `200 OK` `[RoleAssignment]` | `UC-SA-012` |
| `POST` | `/api/v1/superadmin/roles/` | `superadmin.role.assign` | No | `{user_id, role_name, valid_from, valid_to, ...}` | `201 Created` `{assignment_id}` | `UC-SA-008`, `BR-SA-006`, `BR-SA-007`, `BR-SA-008` |
| `POST` | `/api/v1/superadmin/roles/{id}/reassign/` | `superadmin.role.assign` | No | `{successor_user_id, effective_date, handover_summary}` | `200 OK` `{new_assignment_id}` | `UC-SA-009`, `BR-SA-012` |
| `POST` | `/api/v1/superadmin/roles/{id}/revoke/` | `superadmin.role.revoke` | Yes | `{reason}` | `200 OK` `{status: 'REVOKED'}` | `UC-SA-010`, `BR-SA-014` |
| `POST` | `/api/v1/superadmin/roles/{id}/extend/` | `superadmin.role.update` | No | `{new_valid_to, reason}` | `200 OK` `{status: 'EXTENDED'}` | `UC-SA-011`, `BR-SA-016`, `BW-SA-05` |
| `POST` | `/api/v1/superadmin/archive/user/{user_id}/` | `superadmin.archive.create` | Yes | `{reason}` | `200 OK` `{status: 'ARCHIVED_REVERSIBLE'}` | `UC-SA-015`, `BR-SA-004`, `BW-SA-08` T1 |
| `POST` | `/api/v1/superadmin/archive/user/{user_id}/restore/` | `superadmin.archive.restore` | Yes | `{reason}` | `200 OK` `{status: 'ACTIVE'}` | `UC-SA-018`, `BR-SA-005`, `BW-SA-07` |
| `GET` | `/api/v1/superadmin/archive/` | `superadmin.archive.view` | No | `?entity_type=&status=` | `200 OK` `[ArchiveRecord]` | `UC-SA-017`, `BR-SA-020` |
| `POST` | `/api/v1/superadmin/purge/request/` | `superadmin.purge.create` | Yes | `{archive_record_id, reason}` | `201 Created` `{request_id}` | `UC-SA-022`, `BR-SA-021` |
| `POST` | `/api/v1/superadmin/purge/{request_id}/authorize/` | `superadmin.purge.approve` | Yes | `{action: 'APPROVE' \| 'REJECT', reason}` | `200 OK` `{status}` | `UC-SA-023`, `BR-SA-022`, `BW-SA-01`, `BW-SA-02` |
| `GET` | `/api/v1/superadmin/audit/` | `superadmin.audit_log.view` | No | `?actor=&event=&from=&to=` | `200 OK` `[AuditLogEntry]` | `UC-SA-024`, `BR-SA-025`, `BR-SA-033` |
| `GET` | `/api/v1/superadmin/config/` | `superadmin.system_config.view` | No | None | `200 OK` `[SystemParameter]` | `UC-SA-027`, `BR-SA-035` |
| `POST` | `/api/v1/superadmin/config/` | `superadmin.system_config.update` | Yes | `{key, value, effective_from}` | `201 Created` `{new_version}` | `UC-SA-027`, `BR-SA-035` |

### Integration into `Fusion-client` (`INTEGRATED_MODULES`)

```javascript
// In Fusion-client/src/ui/nav/navigation.js

{

  id: 'superadmin',

  label: 'Super Admin',

  icon: 'ShieldCheck',

  to: '/superadmin',

  section: 'Administration',

}
```

---

## §3.6 (f) — Contracts and External Module Seams

Per `ops/checks/contracts_are_plural.py`, every getter in `modules/superadmin/contracts.py` accepts plural sequences:

```python
# modules/superadmin/contracts.py

from typing import Sequence, Dict, Any


def get_user_account_records(user_ids: Sequence[int]) -> Dict[int, Dict[str, Any]]:

    """Return user account administrative status dictionary keyed by user_id."""


def get_active_role_assignments(user_ids: Sequence[int]) -> Dict[int, list[Dict[str, Any]]]:

    """Return list of active additional roles held by each user_id."""


def get_archived_user_statuses(user_ids: Sequence[int]) -> Dict[int, Dict[str, Any]]:

    """Return archival status and reversibility window expiration details."""
```

### ERP / IAM Consumption Seam

Super Admin reads user identity, names, and departmental affiliations exclusively through the projected IAM client API: 
`iam_client.get_users(user_ids)` and `iam_client.search_users(query)`. Zero direct connection or joins to `auth_user` or `fusionlab` tables.

---

## §3.7 (g) — Scheduled Work (Celery Beat Schedule)

The module registers four scheduled tasks in `modules/superadmin/schedule.py`:

| Task Name | Schedule | Functionality | Real-World Failure if Beat is Down |
|---|---|---|---|
| `superadmin.tasks.finalize_archived_user_reversibility_expiry` | Every hour (`0 * * * *`) | Enforces `BW-SA-08` Transition 2: sweeps `ARCHIVED_REVERSIBLE` accounts whose `reversibility_expires_at < now()` and transitions them to `ARCHIVED_PERMANENT`. | Archived users stay indefinitely restorable beyond compliance retention window. |
| `superadmin.tasks.activate_scheduled_roles` | Every 15 mins (`*/15 * * * *`) | Enforces `BW-SA-04`: sweeps `SCHEDULED` role assignments whose `valid_from <= now()` and transitions to `ACTIVE`. | Assigned roles fail to take effect on their effective date. |
| `superadmin.tasks.expire_time_bound_roles` | Every 15 mins (`*/15 * * * *`) | Enforces `BW-SA-03`: sweeps `ACTIVE`/`EXTENDED` role assignments whose `valid_to <= now()` and transitions to `EXPIRED`. | Users retain expired administrative privileges indefinitely (security violation). |
| `superadmin.tasks.send_role_expiry_reminders` | Daily at 08:00 (`0 8 * * *`) | Enforces `BR-SA-016`: dispatches reminder notifications 7 days and 1 day prior to role expiry. | Role holders and admins are not alerted to upcoming expiries. |

---

## §3.8 (h) — Open Questions, Known Gaps & Approval Record

### Settled Architectural Decisions

1. **Reversibility Window Duration (`BW-SA-08`):** Configured as a system parameter policy defaulting to **90 days**. Deactivated users remain in `ARCHIVED_REVERSIBLE` for 90 days before final non-restorable archival.
2. **Minimum Deactivation Interval (`BR-SA-04`):** Minimum interval between user deactivation and archival is set to **30 days**.
3. **Singular Role Occupancy (`BR-SA-07`):** Enforced at database level via a partial unique constraint (`UniqueConstraint(fields=['role_name'], condition=Q(is_singular=True, status__in=['ACTIVE', 'EXTENDED']))`).
4. **Step-Up Reauthentication (`BR-SA-029`):** Dangerous operations require recent session authentication within 300 seconds.
5. **No Direct ERP Writes:** Super Admin creates local administrative profile shadow records; identity provisioning triggers IAM integration.

### Formal Approval Gate (Student 2 Sign-Off)

Per Assignment 9 rules, Student 1 must not proceed to application code implementation before Student 2 approves this blueprint in writing.

- **Student 1 (Builder):** Nikhil Jain (Roll No: 24BCS170)

- **Student 2 (Reviewer/Tester):** Paladugu Taraka Ram (Roll No: 24BCS182)

- **Approval Date:** 2026-11-22

- **Approval Status:** **APPROVED IN WRITING BY STUDENT 2**

- **Written Record Quote:** `"I have reviewed the Super Admin architecture blueprint (docs/23-superadmin/superadmin-blueprint.md). The traceability table, domain models, declarative state machine for BW-SA-08, permission model, and external contracts meet the spec requirements. The blueprint is approved." — Paladugu Taraka Ram (24BCS182)`
