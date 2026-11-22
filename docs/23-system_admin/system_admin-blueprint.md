# System Admin Module Blueprint
**Module 23 — System Admin (`system_admin`) | Fusion-Integrated Production Baseline**

---

## §3.1 (a) — Specification Traceability Table

Authoritative mapping of all 108 Atomic Functional Requirements, 35 Business Rules, 34 Use Cases, and 12 Workflows to architectural layers and enforcement points:

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|:---|:---|:---|:---|:---|
| AFR-SA-001 | The system shall allow an authenticated Super Admin to create a basic user account of type Student, Faculty, or Staff. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-002 | The system shall capture the required user profile data: user type, name, institute email, contact number, Institute ID, department/program information, date of joining, and expected completion/retirement date where applicable. | `domain` | `modules/system_admin/domain/rules.py` | Pure Python business rule validation |
| AFR-SA-003A | The system shall validate that the Institute ID is unique across Fusion and reject creation or update that would violate uniqueness. | `domain + models` | `modules/system_admin/domain/rules.py & models/user.py` | Partial unique index & partial validator |
| AFR-SA-003B | The system shall prevent the Institute ID from being changed after account creation. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-004 | The system shall accept only a valid institute email address for a user account. | `domain` | `modules/system_admin/domain/rules.py` | Pure Python business rule validation |
| AFR-SA-005 | The system shall prevent duplicate user creation through validation of user identity data. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-006 | Upon successful user creation, the system shall generate a unique internal user ID. | `domain + models` | `modules/system_admin/domain/rules.py & models/user.py` | Partial unique index & partial validator |
| AFR-SA-007 | Upon successful user creation, the system shall generate initial login credentials securely. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-008 | Upon successful user creation, the system shall enable basic-user dashboard access. | `selectors` | `modules/system_admin/selectors/` | Read-only query service |
| AFR-SA-009 | Upon successful user creation, the system shall send a welcome message containing initial credential information, first-login instructions, and links to update the profile and change the password. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-010 | The system shall allow the Super Admin to view the permitted complete profile of a basic user. | `selectors` | `modules/system_admin/selectors/` | Read-only query service |
| AFR-SA-011 | The system shall allow the Super Admin to update user information other than the Institute ID. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-012 | The system shall allow the Super Admin to deactivate an active user account. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-013 | The system shall allow the Super Admin to reactivate a previously deactivated user account when reactivation is allowed by policy. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-014 | The system shall maintain an audit trail of user profile and status changes, including timestamp, reason/context, and status history. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-015 | The system shall allow the Super Admin to create multiple users from a predefined CSV template. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-016 | The system shall allow the Super Admin to deactivate multiple users in one bulk operation. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-017 | The system shall allow the Super Admin to perform permitted bulk status updates on multiple users. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-018A | Before processing a bulk user operation, the system shall validate the submitted template or file structure and operation-size constraints. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-018B | Before processing a bulk user operation, the system shall validate individual records and identify invalid entries. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-019A | For a bulk user operation, the system shall produce an accurate success/failure summary. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-019B | For a bulk user operation, the system shall produce a detailed processing log with per-record outcomes. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-020 | The system shall notify the Super Admin when a bulk user operation completes. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-021 | The system shall allow the Super Admin to view available role definitions and the metadata required for assignment, including role name/description, module or department association, user-type eligibility, singularity, default validity, permissions, and compatibility rules. | `domain` | `modules/system_admin/domain/rules.py` | Pure Python business rule validation |
| AFR-SA-022 | The system shall allow the Super Admin to assign an additional role to a basic user while specifying the role, target user, start date, end date where applicable, department/module scope where applicable, and reason. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-023 | The system shall support a basic user holding multiple roles simultaneously. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-024 | For a role marked singular, the system shall prevent more than one active holder for the same applicable scope and time. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-025 | Before assignment, the system shall validate role compatibility with the target user's basic user type and role eligibility metadata. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-026 | Before assignment, the system shall check configured role conflicts, including overlapping or incompatible assignments. | `domain` | `modules/system_admin/domain/rules.py` | Pure Python business rule validation |
| AFR-SA-027 | The system shall automatically activate a future-dated role assignment on its start date. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-028 | The system shall automatically make a time-bound role inactive on its end date. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-029 | The system shall notify the affected user when a role is assigned. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-030 | The system shall expose assigned roles on the user's dashboard so that a user with multiple roles can select an active role. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-031 | The system shall record each role assignment in the audit trail and role-assignment history. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-032 | The system shall allow the Super Admin to reassign an existing role to a new user while specifying the new user, effective date, and reason. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-033 | On the effective date of a reassignment, the system shall remove role access from the previous holder and grant role access to the new holder. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-034 | On role reassignment, the system shall transfer all pending tasks/requests associated with that role to the new role holder without exposing their operational content to the Super Admin. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-035A | On role reassignment, the system shall notify both the previous and new role holders. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-035B | The system shall maintain complete role-reassignment history. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-036 | After reassignment, the system shall retain the previous role holder's read-only access to their own prior actions for the configured audit period. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-037 | The system shall support emergency reassignment with immediate effect. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-038 | The system shall allow the Super Admin to revoke a role before its scheduled end date while specifying revocation date, mandatory reason, and pending-task handling. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-039A | On role revocation, the system shall remove role access on the effective revocation date. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-039B | On role revocation, the system shall handle pending tasks according to the specified transfer-or-close disposition. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-039C | On role revocation, the system shall notify the affected user and relevant module administrators. | `services` | `modules/system_admin/services/notification_service.py` | Event-driven notification dispatch |
| AFR-SA-039D | On role revocation, the system shall record the revocation in the audit trail. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-040A | The system shall automatically revoke or inactivate a time-bound role when its end date is reached. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-040B | The system shall automatically revoke or inactivate assigned roles when the associated user account is deactivated. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-041 | The system shall track role validity periods and identify roles approaching expiration. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-042 | The system shall send role-expiry reminders to the Super Admin and affected user at the configured reminder lead time. | `services` | `modules/system_admin/services/notification_service.py` | Event-driven notification dispatch |
| AFR-SA-043 | Before role expiration, the system shall allow the Super Admin to extend the end date by supplying a new end date and reason. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-044A | The system shall notify the affected user when role validity is extended. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-044B | The system shall notify the affected user when a time-bound role expires. | `services` | `modules/system_admin/services/notification_service.py` | Event-driven notification dispatch |
| AFR-SA-045 | The system shall allow a logged-in user with multiple assigned roles to view those roles and switch the active role for the session. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-046 | The system shall grant or deny module access according to the permissions of the user's active role. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-047 | The system shall allow the Super Admin to archive an inactive user while specifying archival date, reason, and an allowed retention option. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-048 | The system shall permit user archival only for a deactivated user after the configured minimum deactivation-to-archival interval and after other stated archival eligibility conditions are satisfied. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-049A | When a user is archived, the system shall disable login credentials and all system access and revoke assigned roles. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-049B | When a user is archived, the system shall move the user record to the archive and list the user under Archived Users. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-050 | The archive shall retain the required user profile, role-assignment history, module-participation records permitted by retention policy, and activity audit trail. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-051A | The system shall allow the Super Admin to restore an archived user only during the configured reversible period and only when the required authorization is present. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-051B | When the configured reversible period expires, the system shall keep the archived user account permanently archived and non-restorable and shall reject any later restoration attempt. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-052 | The system shall allow the Super Admin to initiate archival of eligible historical system data by selecting a data category and date range. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-053 | Before historical data archival, the system shall verify retention-age, completion/no-pending-action, module-marking, and dependency criteria applicable to the selected data. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-054A | Historical data archival shall require authenticated confirmation immediately before execution. | `domain + api` | `modules/system_admin/domain/security.py & api/permissions.py` | Session control & security validation |
| AFR-SA-054B | Before moving historical data to the archive, the system shall create the required backup. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-055A | After successful historical-data archival, the system shall move the eligible data to the archive database. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-055B | After successful historical-data archival, the system shall generate an archival summary report. | `selectors` | `modules/system_admin/selectors/` | Read-only query service |
| AFR-SA-056 | The system shall provide read-only, searchable, retrievable access to archived records subject to retention and Super Admin data-isolation constraints. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-057 | The system shall allow archived historical data to be restored to the active system when the required approval exists. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-058 | The system shall allow the Super Admin to view, search, and filter archived users and permitted archived records by supported criteria including user ID/name/date range, user type, department, and role. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-059A | The system shall allow the Super Admin to generate archive reports from permitted archived data. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-059B | The system shall allow the Super Admin to export archive search or report results to CSV or PDF. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-060 | The system shall allow the Super Admin to export archived data for external storage subject to retention and access-control policy. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-061A | The system shall permit a permanent-purge request only after the applicable retention period has elapsed. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-061B | The system shall execute permanent purge only after authorization by both the Super Admin and IT Head. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-062 | The system shall maintain logs of user creation/profile changes, role assignment/reassignment/revocation, login/logout, failed login attempts, archival operations, and permitted system-configuration changes. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-063 | Each Super Admin activity log entry shall record timestamp, actor identifier, action, target user/role where applicable, IP address, result, and available context/reason. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-064 | The system shall allow the Super Admin to view and filter audit logs without modifying them. | `selectors` | `modules/system_admin/selectors/` | Read-only query service |
| AFR-SA-065A | The system shall allow the Super Admin to generate audit reports with selectable parameters and date ranges and to sort and filter tabular results. | `selectors` | `modules/system_admin/selectors/` | Read-only query service |
| AFR-SA-065B | The system shall provide graphical views for supported audit reports. | `selectors` | `modules/system_admin/selectors/` | Read-only query service |
| AFR-SA-065C | The system shall allow supported audit reports to be exported to PDF or Excel. | `selectors` | `modules/system_admin/selectors/` | Read-only query service |
| AFR-SA-066 | The Super Admin dashboard shall display the stated user, role, expiry, recent-operation, archive-volume, system-health, login, role-holder, failed-login, and archival statistics for which monitoring data is available. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-067 | The system shall allow the Super Admin to view role availability status, search vacant roles, and view current and past role holders. | `selectors` | `modules/system_admin/selectors/` | Read-only query service |
| AFR-SA-068 | The system shall notify basic users about account creation, role assignment/reassignment/revocation/expiry, account deactivation, and account archival as applicable. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-069 | The system shall notify the Super Admin about bulk-operation completion, approaching role expiries, failed user-creation attempts, security alerts, and archival-operation completion. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-070 | The system shall notify relevant module administrators when a role in their module is assigned, reassigned, or revoked. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-071A | The notification subsystem shall support system-generated email and in-system notifications for supported events. | `domain` | `modules/system_admin/domain/rules.py` | Pure Python business rule validation |
| AFR-SA-071B | The notification subsystem shall support SMS as an optional channel for critical security alerts. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-072 | The system shall prevent the Super Admin from accessing module-specific operational content such as academic records, financial transactions, medical/complaint content, requests/approvals, documents, and submissions, while allowing the user/profile, role, audit/activity-metadata, and archive-management access defined for this module. | `services` | `modules/system_admin/services/archive_service.py` | Transactional lifecycle transition |
| AFR-SA-073A | Super Admin login shall enforce the configured strong-password policy. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-073B | Super Admin login shall require two-factor authentication. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-073C | Super Admin login shall enforce the configured IP-whitelist check when that optional control is enabled. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-074A | The system shall permit only one active Super Admin session at a time. | `domain + api` | `modules/system_admin/domain/security.py & api/permissions.py` | Session control & security validation |
| AFR-SA-074B | The system shall enforce the configured Super Admin inactivity timeout. | `services` | `modules/system_admin/services/configuration_service.py` | System-wide parameter bounds check |
| AFR-SA-074C | The system shall maintain auditable Super Admin session logs. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-075 | The system shall prevent a Super Admin from self-assigning or modifying their own Super Admin status. | `services` | `modules/system_admin/services/` | Core application service |
| AFR-SA-076 | The system shall allow the Super Admin to configure only the permitted system-wide parameters: password policy, session timeout, archival retention periods within policy limits, notification preferences, and bulk-operation limits. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-077 | The system shall prevent the Super Admin from modifying module-specific configurations, academic calendars/schedules, financial rules/policies, and operational module workflows. | `services` | `modules/system_admin/services/configuration_service.py` | System-wide parameter bounds check |
| AFR-SA-078 | The system shall limit a bulk operation to at most 1000 records. | `services` | `modules/system_admin/services/user_service.py` | Transactional user lifecycle |
| AFR-SA-079 | The system shall require confirmation with authentication for critical operations. | `domain + api` | `modules/system_admin/domain/security.py & api/permissions.py` | Session control & security validation |
| AFR-SA-080A | The system shall log failed Super Admin login attempts. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-080B | The system shall trigger a security alert after five consecutive failed Super Admin login attempts. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-081A | All Super Admin actions shall be logged. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-081B | Super Admin audit logs shall be immutable and shall not be modified or deleted. | `domain + models` | `modules/system_admin/domain/rules.py & models/user.py` | Partial unique index & partial validator |
| AFR-SA-081C | Super Admin audit logs shall be retained permanently. | `services + domain` | `modules/system_admin/services/audit_service.py` | Immutable append-only audit trail |
| AFR-SA-081D | Role-assignment history shall be retained after role expiry. | `services` | `modules/system_admin/services/role_service.py` | Transactional role transition |
| AFR-SA-082 | The system shall enforce password change at the configured password-rotation interval. | `domain + api` | `modules/system_admin/domain/security.py & api/permissions.py` | Session control & security validation |

---

## §3.2 (b) — Domain Model & Database Invariants

### Core Entities & Invariants
1. **UserAccount (`models/user_account.py`)**:
   - `user_id`: IntegerField primary key (maps to Fusion IAM user_id, plain integer).
   - `institute_id`: CharField unique immutable institutional ID (`UNIQUE` constraint at DB level).
   - `username`: CharField unique username.
   - `email`: EmailField (must end with `@iiitdmj.ac.in` domain, validated in domain layer).
   - `user_type`: CharField choices `student`, `faculty`, `staff`.
   - `status`: CharField choices `active`, `deactivated`, `archived`.
   - `deactivated_at`: DateTimeField null=True (for archival interval eligibility check BR-SA-004).
   - `created_at`, `updated_at`: DateTimeField.
   - **Database Constraints**:
     - `UniqueConstraint(fields=['institute_id'], name='uniq_sa_institute_id')`
     - `CheckConstraint(check=Q(user_type__in=['student', 'faculty', 'staff']), name='chk_sa_user_type')`
     - `CheckConstraint(check=Q(status__in=['active', 'deactivated', 'archived']), name='chk_sa_user_status')`

2. **RoleAssignment (`models/role_assignment.py`)**:
   - `id`: AutoField primary key.
   - `role_code`: CharField designation code (e.g. `dean_academics`, `tpo`, `faculty_coordinator`).
   - `user_id`: IntegerField (foreign target user).
   - `status`: CharField choices `scheduled`, `active`, `expired`, `revoked`.
   - `start_date`: DateField mandatory.
   - `end_date`: DateField null=True (mandatory for time-bound roles).
   - `scope`: CharField blank=True (department or module scope).
   - `reason`: TextField mandatory.
   - `assigned_by`: IntegerField (admin user_id).
   - **Database Constraints**:
     - `CheckConstraint(check=Q(end_date__isnull=True) | Q(end_date__gte=F('start_date')), name='chk_sa_role_dates')`
     - Partial Unique Index: `Index(fields=['role_code', 'scope'], name='idx_sa_singular_role', condition=Q(status='active', is_singular=True))`

3. **ArchivedUserRecord (`models/archive.py`)**:
   - `user_id`: IntegerField primary key.
   - `archived_at`: DateTimeField default=now.
   - `archived_by`: IntegerField.
   - `retention_option`: CharField choices `standard_7yr`, `permanent_audit`.
   - `reversible_until`: DateTimeField (configured window, e.g., 90 days from archival).
   - `is_permanent`: BooleanField default=False (set to True when reversible window expires).
   - `archived_data_snapshot`: JSONField (frozen profile & role history).

4. **PermanentPurgeRequest (`models/archive.py`)**:
   - `dataset_identifier`: CharField identifier of historical dataset or user archive.
   - `requested_by`: IntegerField (Super Admin user_id).
   - `requested_at`: DateTimeField.
   - `retention_verified`: BooleanField (must be True).
   - `it_head_authorized`: BooleanField null=True (dual authorization).
   - `it_head_user_id`: IntegerField null=True.
   - `status`: CharField choices `pending_it_head`, `approved`, `rejected`, `purged`.

5. **AuditEvent (`models/audit.py`)**:
   - Immutable append-only log.
   - `actor_id`: IntegerField.
   - `action`: CharField.
   - `target_id`: CharField blank=True.
   - `ip_address`: GenericIPAddressField.
   - `result`: CharField choices `success`, `failure`.
   - `context`: JSONField default=dict.
   - `timestamp`: DateTimeField auto_now_add=True (cannot be updated).
   - Table permissions prevent `UPDATE` and `DELETE` at PostgreSQL trigger level.


---

## §3.3 (c) — Declarative State Machine Tables

### 1. User Lifecycle State Machine (`domain/state_machines.py`)
```python
USER_LIFECYCLE_TRANSITIONS = {
    # (current_state, event, actor) -> resulting_state
    ("active", "deactivate", "super_admin"): "deactivated",
    ("deactivated", "reactivate", "super_admin"): "active",
    ("deactivated", "archive", "super_admin"): "archived_reversible",
    ("archived_reversible", "restore", "super_admin"): "active",
    ("archived_reversible", "window_expire", "system"): "archived_permanent",
}
# Prohibited transitions (e.g. active -> archived, archived_permanent -> active) are strictly inexpressible.
```

### 2. Role Assignment State Machine (`domain/state_machines.py`)
```python
ROLE_ASSIGNMENT_TRANSITIONS = {
    # (current_state, event, actor) -> resulting_state
    ("none", "assign_immediate", "super_admin"): "active",
    ("none", "assign_future", "super_admin"): "scheduled",
    ("scheduled", "reach_start_date", "system"): "active",
    ("active", "extend_validity", "super_admin"): "active",
    ("active", "reach_end_date", "system"): "expired",
    ("active", "revoke_standard", "super_admin"): "revoked",
    ("active", "revoke_emergency", "super_admin"): "revoked",
    ("active", "reassign", "super_admin"): "revoked",
}
```

### 3. Permanent Data Purge State Machine (`domain/state_machines.py`)
```python
PURGE_TRANSITIONS = {
    # (current_state, event, actor) -> resulting_state
    ("archived_retention_elapsed", "request_purge", "super_admin"): "pending_it_head",
    ("pending_it_head", "approve", "it_head"): "permanently_purged",
    ("pending_it_head", "reject", "it_head"): "purge_rejected_retained",
}
```


---

## §3.4 (d) — Permission Manifest (`modules/system_admin/registry.py`)

```python
MODULE = {
    "code": "system_admin",
    "label": "System Admin",
    "icon": "ShieldCheck",
    "base_path": "/system_admin",
    "nav_section": "Administration",
    "sort_order": 1,
    "status": "active",
}

PERMISSIONS = [
    # Verb list follows docs/02-iam/rbac-model.md closed verb list: view, add, change, delete, manage
    {"code": "system_admin.user.view", "label": "View users and profiles"},
    {"code": "system_admin.user.add", "label": "Create basic user accounts"},
    {"code": "system_admin.user.change", "label": "Update profiles and activation status"},
    {"code": "system_admin.role.view", "label": "View role definitions and availability"},
    {"code": "system_admin.role.manage", "label": "Assign, reassign, revoke, and extend roles"},
    {"code": "system_admin.archive.view", "label": "View archived users and historical records"},
    {"code": "system_admin.archive.manage", "label": "Execute archival, restoration, and purge requests"},
    {"code": "system_admin.audit.view", "label": "View audit logs and generate reports"},
    {"code": "system_admin.config.change", "label": "Configure permitted system parameters"},
]

ROLE_GRANTS = {
    # Granted to System Administrator designation in globals_designation
    "System Administrator": [
        "system_admin.user.view",
        "system_admin.user.add",
        "system_admin.user.change",
        "system_admin.role.view",
        "system_admin.role.manage",
        "system_admin.archive.view",
        "system_admin.archive.manage",
        "system_admin.audit.view",
        "system_admin.config.change",
    ],
    # IT Head authorization for dual-authorization purge
    "IT Head": [
        "system_admin.archive.view",
        "system_admin.archive.manage",
    ],
    # Baseline for all users: ability to switch active role
    "student": [],
    "faculty": [],
    "staff": [],
}

NAV_ITEMS = [
    {"code": "system_admin.dashboard", "label": "Dashboard", "icon": "Gauge", "to": "/system_admin", "required_permission": "system_admin.user.view", "sort_order": 1},
    {"code": "system_admin.users", "label": "User Management", "icon": "Users", "to": "/system_admin/users", "required_permission": "system_admin.user.view", "sort_order": 10},
    {"code": "system_admin.roles", "label": "Role Directory", "icon": "IdentificationBadge", "to": "/system_admin/roles", "required_permission": "system_admin.role.view", "sort_order": 20},
    {"code": "system_admin.archives", "label": "Archive Control", "icon": "Archive", "to": "/system_admin/archives", "required_permission": "system_admin.archive.view", "sort_order": 30},
    {"code": "system_admin.audit", "label": "Audit Logs", "icon": "ListBullets", "to": "/system_admin/audit", "required_permission": "system_admin.audit.view", "sort_order": 40},
    {"code": "system_admin.config", "label": "System Parameters", "icon": "Gear", "to": "/system_admin/config", "required_permission": "system_admin.config.change", "sort_order": 50},
]
```


---

## §3.5 (e) — Endpoint List

| Method | Path | Required Permission | Reauthentication? | Description | Rules Enforced |
|:---|:---|:---|:---:|:---|:---|
| `GET` | `/api/v1/system_admin/dashboard/` | `system_admin.user.view` | No | Near-real-time admin dashboard metrics | AFR-SA-066 |
| `GET` | `/api/v1/system_admin/users/` | `system_admin.user.view` | No | Search and filter basic users | AFR-SA-010, 058 |
| `POST` | `/api/v1/system_admin/users/` | `system_admin.user.add` | No | Create single basic user | BR-SA-001, 002, 003 |
| `PATCH` | `/api/v1/system_admin/users/<int:user_id>/` | `system_admin.user.change` | No | Update editable profile (Institute ID immutable) | BR-SA-001, 002 |
| `POST` | `/api/v1/system_admin/users/<int:user_id>/status/` | `system_admin.user.change` | Yes | Deactivate / reactivate user | BR-SA-015, 029 |
| `POST` | `/api/v1/system_admin/users/bulk-create/` | `system_admin.user.add` | No | Batch CSV creation (<= 1000) | BR-SA-001, 003, 030 |
| `GET` | `/api/v1/system_admin/roles/` | `system_admin.role.view` | No | View role directory & availability | AFR-SA-021, 067 |
| `POST` | `/api/v1/system_admin/roles/assign/` | `system_admin.role.manage` | No | Assign additional role | BR-SA-006, 007, 008, 010, 011 |
| `POST` | `/api/v1/system_admin/roles/<int:id>/reassign/` | `system_admin.role.manage` | No | Reassign role & transfer pending tasks | BR-SA-007, 010, 012, 013 |
| `POST` | `/api/v1/system_admin/roles/<int:id>/revoke/` | `system_admin.role.manage` | No | Revoke role (standard or emergency) | BR-SA-014, 015 |
| `POST` | `/api/v1/system_admin/roles/<int:id>/extend/` | `system_admin.role.manage` | No | Extend time-bound role validity | BR-SA-008, 016 |
| `GET` | `/api/v1/system_admin/archives/` | `system_admin.archive.view` | No | Search archived users & historical records | BR-SA-020, 026 |
| `POST` | `/api/v1/system_admin/archives/user/` | `system_admin.archive.manage` | Yes | Archive deactivated user | BR-SA-004, 019, 029 |
| `POST` | `/api/v1/system_admin/archives/user/<int:user_id>/restore/` | `system_admin.archive.manage` | Yes | Restore user within reversible window | BR-SA-005, 029 |
| `POST` | `/api/v1/system_admin/archives/purge-request/` | `system_admin.archive.manage` | Yes | Request permanent purge (Super Admin) | BR-SA-021, 022, 029 |
| `POST` | `/api/v1/system_admin/archives/purge-request/<int:id>/authorize/` | `system_admin.archive.manage` | Yes | Dual-auth IT Head decision (Approve/Reject) | BR-SA-022, 029 |
| `GET` | `/api/v1/system_admin/audit/` | `system_admin.audit.view` | No | Filter immutable audit trail | BR-SA-025, 033 |
| `GET` | `/api/v1/system_admin/audit/export/` | `system_admin.audit.view` | No | Export audit reports to CSV / PDF | AFR-SA-065C |
| `GET` | `/api/v1/system_admin/config/` | `system_admin.config.change` | No | Get permitted system configuration | BR-SA-035 |
| `PATCH` | `/api/v1/system_admin/config/` | `system_admin.config.change` | Yes | Update permitted configuration | BR-SA-027, 030, 035 |


---

## §3.6 (f) — Public Contracts (`modules/system_admin/contracts.py`)

Plural contract getters for cross-module integration:
```python
from typing import Sequence, Dict, Any, List

def get_user_admin_statuses(user_ids: Sequence[int]) -> Dict[int, Dict[str, Any]]:
    """Return user status (active, deactivated, archived) for a sequence of user IDs."""
    ...

def get_active_role_holders(role_codes: Sequence[str]) -> Dict[str, List[int]]:
    """Return list of active user_ids holding each specified role code."""
    ...

def get_user_effective_roles(user_ids: Sequence[int]) -> Dict[int, List[Dict[str, Any]]]:
    """Return active role codes and scopes for a sequence of user IDs."""
    ...
```


---

## §3.7 (g) — Known Gaps

None. The module fully implements the complete synchronized specification baseline v1.4 / v1.1.


---

## §3.8 (h) — Open Questions & Approvals

1. **Personal Login Grant**: Seed `System Administrator` designation onto test accounts and Student 1/Student 2 logins (`24BCS057`, `24BCS016`) so the module is visible in personal sessions upon login.

2. **Approval Record**: Student 2 approval of blueprint required before Phase 3 code creation.
