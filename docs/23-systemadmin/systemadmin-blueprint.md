# System Administration Module Architectural Blueprint

**Module Name**: System Administration (`systemadmin`)  
**Module Code**: `systemadmin`  
**Docs Folder**: `docs/23-systemadmin/`  
**Specification Baseline**: Super Admin (SA) Specification Bundle v1.4 / v1.1 FINAL SYNCHRONIZED  
**Author (Student 1)**: Manda Srikanth Harsha (`24BCS142` / `SRIKANTH-HARSHA-MANDA`)  
**Approver (Student 2)**: Katika Rohith (`24BCS117` / `katikarohith`)  
**Approval Date**: 2026-11-01  
**Status**: APPROVED  

---

## 1. Executive Summary & Module Purpose

The **System Administration (`systemadmin`)** module serves as the authoritative administrative control plane for Fusion ERP at IIITDM Jabalpur. It provides centralized lifecycle management for basic users (Student, Faculty, Staff), additional-role lifecycle governance, user and historical data archival with dual-authorization permanent purge controls, immutable audit logging, security event monitoring, and administrative system parameters.

In strict accordance with the problem statement and Fusion architectural standards:
- The module is deployed with dedicated administrative boundaries and does not expose or mutate academic, financial, or other operational domain records.
- All basic identity authentication and designation grants join via central IAM contracts (`fusion_auth`).
- All reads go through dedicated selector layers; all state mutations are encapsulated in domain services.

---

## 2. Traceability Matrix

| Requirement / Rule ID | Specification Obligation Summary | Layer | Planned Enforcement Point | Notes |
|:---|:---|:---|:---|:---|
| **CFR-SA-001 / AFR-SA-001** | Basic User Account Creation (Student, Faculty, Staff) | Services / Models | `modules.systemadmin.services.user_service.UserService.create_basic_user` | Validates required fields per user type |
| **CFR-SA-002 / AFR-SA-009** | Institute ID Uniqueness and Immutability | Models / DB / API | `BasicUserProfile.institute_id` (UniqueConstraint) & `UserUpdateSerializer` | Rejects alterations with HTTP 400 |
| **CFR-SA-003 / AFR-SA-011** | Institute Domain Email Validation | Domain / Policy | `UserService._validate_institute_email` | Requires `@iiitdmj.ac.in` domain |
| **CFR-SA-004 / AFR-SA-015** | Initial Credentials & Notification Dispatch | Services | `UserService._generate_initial_credentials` & `NotificationService` | Auto-generates initial credentials |
| **CFR-SA-005 / AFR-SA-018** | User Profile Update (Editable Fields Only) | Services / API | `UserService.update_user_profile` | Rejects immutable identifier mutations |
| **CFR-SA-006 / AFR-SA-021** | User Deactivation and Reactivation | Services / Models | `UserService.deactivate_user`, `UserService.reactivate_user` | Updates status and revokes active roles |
| **CFR-SA-007 / AFR-SA-025** | Bulk User Operations (CSV Batch Creation, Batch Status) | Services / API | `UserService.bulk_create_users`, `UserService.bulk_update_status` | Enforces 1000 record batch boundary |
| **CFR-SA-008 / AFR-SA-031** | Additional Role Assignment & Compatibility Checks | Services / Models | `RoleService.assign_role` | Checks eligibility, singularity & static conflicts |
| **CFR-SA-009 / AFR-SA-035** | Role Reassignment with Handover & Access Transfer | Services | `RoleService.reassign_role` | Revokes predecessor, grants successor, logs handover |
| **CFR-SA-010 / AFR-SA-039** | Role Revocation (Standard vs Emergency) | Services | `RoleService.revoke_role` | Enforces >= 1 day notice for standard revocation |
| **CFR-SA-011 / AFR-SA-043** | Time-Bound Role Validity Tracking & Extension | Services | `RoleService.extend_role_validity` | Extends future end date with mandatory justification |
| **CFR-SA-012 / AFR-SA-048** | Deactivated User Archival Lifecycle | Services / Models | `ArchivalService.archive_user` | Enforces 30-day deactivation cooling interval |
| **CFR-SA-013 / AFR-SA-052** | Reversible User Archival Restoration Window | Services / Models | `ArchivalService.restore_archived_user` | Allows restoration within configured reversibility period |
| **CFR-SA-014 / AFR-SA-056** | Finalization of Non-Restorable Archived Users | Services | `ArchivalService.finalize_non_restorable_archived_users` | Marks expired reversible users non-restorable |
| **CFR-SA-015 / AFR-SA-060** | Historical Dataset Archival by Category & Date Range | Services / Models | `ArchivalService.archive_historical_data` | Enforces mandatory category & date range validation |
| **CFR-SA-016 / AFR-SA-064** | Historical Dataset Read-Only Inspection & Export | Selectors / API | `ArchivalService.export_historical_archive` | Generates structured archive package |
| **CFR-SA-017 / AFR-SA-070** | Dual-Authorization Permanent Purge (Super Admin + IT Head) | Services / Models | `ArchivalService.request_permanent_purge`, `authorize_permanent_purge` | Requires dual authorization & retention expiry |
| **CFR-SA-018 / AFR-SA-076** | Immutable Super Admin Audit Trail | Services / Models | `AuditService.log_action`, `SystemAdminAuditLog` | Permanent retention; updates/deletions blocked |
| **CFR-SA-019 / AFR-SA-080** | Configurable Audit Reports & Multi-Format Export | Services / API | `AuditService.generate_audit_report` | Tabular summaries and CSV/Excel exports |
| **CFR-SA-020 / AFR-SA-082** | Administrative Monitoring Dashboard Metrics | Selectors / API | `modules.systemadmin.selectors.dashboard_selectors` | Consolidated user, role, archive, health metrics |
| **CFR-SA-021 / AFR-SA-084** | Session Tracking & Concurrency Management | Services / Models | `SecurityService.track_session_activity` | Enforces idle timeouts and concurrent session limits |
| **CFR-SA-022 / AFR-SA-086** | Account Lockout & Security Alert Dispatch | Services / Models | `SecurityService.record_login_attempt` | Threshold-based lockouts and alerts |
| **CFR-SA-023 / AFR-SA-088** | Configurable Administrative Parameters | Services / Models | `ConfigService.get_value`, `ConfigService.set_value` | Key-value store with validation rules |

---

## 3. Data Architecture & Domain Models

All models reside under `modules/systemadmin/models/` across four domain aggregate files:

### 3.1 User Management Aggregate (`user_mgmt.py`)
- `BasicUserProfile`:
  - `institute_id` (CharField, max_length=32, unique=True, db_index=True) — immutable identifier
  - `user_type` (CharField, choices=['student', 'faculty', 'staff'])
  - `full_name` (CharField, max_length=150)
  - `institute_email` (EmailField, unique=True, db_index=True)
  - `status` (CharField, choices=['active', 'deactivated', 'archived'], default='active')
  - `has_dashboard_access` (BooleanField, default=True)
  - `date_of_joining` (DateField)
  - `programme`, `discipline`, `batch_year`, `employee_id`, `department` (specific metadata)
- `UserStatusHistory`:
  - Foreign key to `BasicUserProfile`, `old_status`, `new_status`, `changed_by`, `reason`, `timestamp`

### 3.2 Role Governance Aggregate (`role_mgmt.py`)
- `RoleDefinition`:
  - `code` (CharField, unique=True), `name`, `department`, `is_singular`, `max_holders`, `eligibility_user_types`
- `RoleAssignment`:
  - Foreign keys to `RoleDefinition` and `BasicUserProfile`
  - `start_date`, `end_date`, `scope`, `status` (`active`, `scheduled`, `revoked`, `expired`, `extended`)
  - `revocation_effective_date`, `revocation_reason`, `revocation_task_disposition`
- `RoleConflict`:
  - `role_a`, `role_b`, `conflict_type` (SoD separation of duties)
- `RoleAssignmentHistory`:
  - `assignment`, `action` (`assigned`, `reassigned`, `revoked`, `extended`), `actor_username`, `timestamp`, `details`

### 3.3 Archival & Purge Aggregate (`archival.py`)
- `ArchivedUser`:
  - OneToOneField to `BasicUserProfile`, `archived_at`, `archived_by`, `status` (`reversible`, `non_restorable`, `purged`), `reversibility_deadline`
- `ArchivedHistoricalData`:
  - `category` (CharField), `date_range_start`, `date_range_end`, `record_count`, `backup_reference`, `retention_expiry_date`, `status`
- `PermanentPurgeRequest`:
  - `target_type` (`historical_data`, `archived_user`), `historical_data`, `archived_user`
  - `requested_by`, `requested_at`, `super_admin_authenticated`
  - `it_head_decision` (`pending`, `approve`, `reject`), `it_head_decided_by`, `it_head_decided_at`, `it_head_comments`, `status`

### 3.4 Audit, Security & Configuration Aggregate (`audit.py`, `config.py`)
- `SystemAdminAuditLog`:
  - `timestamp`, `actor_username`, `action`, `status`, `target_user`, `target_role`, `ip_address`, `reason_or_context`, `metadata` (immutable)
- `SessionLog`:
  - `session_key`, `username`, `ip_address`, `login_at`, `last_activity_at`, `is_active`
- `SecurityAlert`:
  - `alert_type`, `severity`, `title`, `description`, `created_at`, `is_resolved`
- `AdminNotification`:
  - `recipient_username`, `title`, `message`, `category`, `channel`, `is_read`, `created_at`
- `SystemAdminConfig`:
  - `key` (CharField, unique=True), `value`, `description`, `is_system`, `updated_at`, `updated_by`

---

## 4. RBAC & Central Registry Specification

### 4.1 Module Definition
- **Code**: `systemadmin`
- **Label**: `System Administration`
- **Icon**: `FaShieldAlt`
- **Base Path**: `/systemadmin`
- **Nav Section**: `Administration`

### 4.2 Permissions Catalogue
1. `systemadmin.dashboard.view` — View monitoring dashboard and health metrics
2. `systemadmin.user.view` — View basic user directory and profiles
3. `systemadmin.user.create` — Create student, faculty, and staff accounts
4. `systemadmin.user.edit` — Update editable basic user profile information
5. `systemadmin.user.status` — Deactivate and reactivate basic user accounts
6. `systemadmin.user.bulk` — Execute batch CSV creation and bulk status changes
7. `systemadmin.role.view` — Inspect role definitions and assignment availability
8. `systemadmin.role.assign` — Assign additional roles to eligible users
9. `systemadmin.role.reassign` — Reassign roles to new holders with work handover
10. `systemadmin.role.revoke` — Revoke active and scheduled role assignments
11. `systemadmin.role.extend` — Extend validity of time-bound role assignments
12. `systemadmin.archive.view` — Search and inspect archived users and historical records
13. `systemadmin.archive.execute` — Execute user and historical dataset archival
14. `systemadmin.archive.restore` — Restore eligible archived users and historical data
15. `systemadmin.purge.request` — Initiate dual-authorization permanent purge requests
16. `systemadmin.purge.authorize` — Authorize or reject permanent purge requests as IT Head
17. `systemadmin.audit.view` — Inspect immutable administrative audit logs
18. `systemadmin.audit.report` — Generate and export tabular and graphical audit reports
19. `systemadmin.config.manage` — Configure permitted administrative parameters

### 4.3 Role Grants Mapping
- **Super Admin**: Holds all permissions except `systemadmin.purge.authorize` (enforcing dual-authorization separation of duties).
- **IT Head**: Holds `systemadmin.dashboard.view`, `systemadmin.archive.view`, `systemadmin.audit.view`, and `systemadmin.purge.authorize`.

---

## 5. REST API Architecture

Base URL: `/api/v1/systemadmin/`

| HTTP Method | Route | Permission Gate | Description |
|:---|:---|:---|:---|
| `GET` | `/dashboard/` | `systemadmin.dashboard.view` | Administrative dashboard metrics and health indicators |
| `GET` | `/users/` | `systemadmin.user.view` | Filterable list of basic user profiles |
| `POST` | `/users/` | `systemadmin.user.create` | Create individual basic user account |
| `GET` | `/users/{id}/` | `systemadmin.user.view` | Retrieve detailed basic user profile |
| `PUT` | `/users/{id}/` | `systemadmin.user.edit` | Update editable profile fields (rejects immutable ID) |
| `POST` | `/users/{id}/status/` | `systemadmin.user.status` | Deactivate or reactivate user account |
| `POST` | `/users/bulk/create/` | `systemadmin.user.bulk` | Process batch user creation (up to 1000 records) |
| `POST` | `/users/bulk/status/` | `systemadmin.user.bulk` | Process batch status modification |
| `GET` | `/roles/` | `systemadmin.role.view` | List role definitions and availability statistics |
| `GET` | `/roles/{id}/` | `systemadmin.role.view` | Retrieve detailed role definition and holder history |
| `GET` | `/assignments/` | `systemadmin.role.view` | List role assignments with active/scheduled filters |
| `POST` | `/assignments/create/` | `systemadmin.role.assign` | Assign role with conflict & singularity validation |
| `POST` | `/assignments/{id}/reassign/` | `systemadmin.role.reassign` | Reassign role to successor holder |
| `POST` | `/assignments/{id}/revoke/` | `systemadmin.role.revoke` | Revoke role (standard with notice or emergency) |
| `POST` | `/assignments/{id}/extend/` | `systemadmin.role.extend` | Extend expiration date for time-bound assignment |
| `GET` | `/archival/users/` | `systemadmin.archive.view` | List archived users and reversibility statuses |
| `POST` | `/archival/users/create/` | `systemadmin.archive.execute` | Archive eligible deactivated user |
| `POST` | `/archival/users/{id}/restore/` | `systemadmin.archive.restore` | Restore user within reversibility window |
| `GET` | `/archival/historical/` | `systemadmin.archive.view` | List archived historical datasets |
| `POST` | `/archival/historical/create/` | `systemadmin.archive.execute` | Archive historical data by category & date range |
| `POST` | `/archival/historical/{id}/restore/` | `systemadmin.archive.restore` | Restore historical dataset snapshot |
| `GET` | `/purge/requests/` | `systemadmin.archive.view` | List permanent purge requests |
| `POST` | `/purge/requests/create/` | `systemadmin.purge.request` | Submit permanent purge request for dual auth |
| `POST` | `/purge/requests/{id}/authorize/` | `systemadmin.purge.authorize` | IT Head approval or rejection of purge request |
| `GET` | `/audit/` | `systemadmin.audit.view` | Search and filter immutable audit trail |
| `GET` | `/audit/report/` | `systemadmin.audit.report` | Generate aggregated audit metrics and reports |
| `GET` | `/security/alerts/` | `systemadmin.dashboard.view` | Retrieve security alerts and lockouts |
| `GET` | `/notifications/` | `systemadmin.dashboard.view` | Retrieve system administrative notifications |
| `GET` | `/config/` | `systemadmin.config.manage` | List administrative parameters |
| `PUT` | `/config/{key}/` | `systemadmin.config.manage` | Update administrative parameter value |

---

## 6. Frontend Architecture & Client Routes

Mounted under `/systemadmin/*` in `client/src/modules/systemadmin/`:

- `/systemadmin/dashboard` — `DashboardPage.tsx` (`systemadmin.dashboard.view`)
- `/systemadmin/users` — `UsersPage.tsx` (`systemadmin.user.view`)
- `/systemadmin/users/:id` — `UserDetailPage.tsx` (`systemadmin.user.view`)
- `/systemadmin/roles` — `RolesPage.tsx` (`systemadmin.role.view`)
- `/systemadmin/assignments` — `RoleAssignmentsPage.tsx` (`systemadmin.role.assign`)
- `/systemadmin/archival` — `ArchivalPage.tsx` (`systemadmin.archive.view`)
- `/systemadmin/audit` — `AuditLogsPage.tsx` (`systemadmin.audit.view`)
- `/systemadmin/audit/reports` — `AuditReportsPage.tsx` (`systemadmin.audit.report`)
- `/systemadmin/config` — `ConfigurationPage.tsx` (`systemadmin.config.manage`)

---

## 7. Formal Approval Sign-off

- **Student 1 (Builder)**: Manda Srikanth Harsha (`24BCS142`) — Date: `2026-11-01`
- **Student 2 (Reviewer & Spec Tester)**: Katika Rohith (`24BCS117`) — Date: `2026-11-01`
- **Verdict**: Fully approved with zero open architectural gaps. Permission to proceed to backend implementation granted.
