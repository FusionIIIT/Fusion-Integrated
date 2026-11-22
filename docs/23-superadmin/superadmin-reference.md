# Module 23: Super Admin (`superadmin`) — Technical Reference Manual

> **Module Code:** `superadmin` | **ID Prefix:** `SA-`
> **Primary Basis Workflow:** `BW-SA-08` (Archived User Reversibility Window Expiry)
> **Builder (Student 1):** Nikhil Jain (Roll: 24BCS170, GitHub: `nikhiljain10905`)
> **Tester/Reviewer (Student 2):** Paladugu Taraka Ram (Roll: 24BCS182, GitHub: `Thrawn-100`)

---

## 1. Module Overview & Architectural Principles

The Super Admin module serves as the central administrative governance backbone of the Fusion ERP platform. It manages institutional identity records, user account lifecycles, role assignment authorization, historical data archival, dual-authorized data purging, immutable compliance auditing, and system parameter configurations.

### Key Architectural Tenets
1. **Domain-Driven Layering (ADR-0010):**
   - `domain/`: Pure Python without Django, DRF, or Celery imports. Validations and state machine transitions execute in sub-milliseconds.
   - `models/`: Declarative Django ORM models with strict constraints. Plain integer `user_id` without cross-module foreign keys (ADR-0013).
   - `selectors/`: Pure read layer. Data scoping guarantees that out-of-scope records return `404 Not Found` rather than `403 Forbidden` to prevent resource enumeration.
   - `services/`: Pure write layer. All database mutations, transaction boundaries, state transitions, and audit logs originate here.
   - `api/`: Thin controllers. Authentication, closed-verb permissions (`HasModuleGrant`, `HasPermission`), step-up re-authentication (`RequiresStepUpAuth`), and OpenAPI schema definitions.
   - `contracts.py`: The single entry point for cross-module queries. All query getters take plural IDs and return dictionaries keyed by `user_id`.
   - `schedule.py` & `tasks.py`: Celery beat background workers for automated state transitions (BW-SA-08 reversibility expiry, role scheduling and expiration).

---

## 2. Declarative State Machines

### 2.1 User Account Lifecycle (`BW-SA-08`, `CW-SA-03`)
```
                  ┌──────────────┐
                  │    ACTIVE    │◄────────┐
                  └──────┬───────┘         │
                         │ (deactivate)    │
                         ▼                 │ (reactivate)
                  ┌──────────────┐         │
                  │ DEACTIVATED  ├─────────┘
                  └──────┬───────┘
                         │ (archive, min 30d)
                         ▼
             ┌─────────────────────────┐
             │   ARCHIVED_REVERSIBLE   │────────┐ (restore within 90d window)
             └───────────┬─────────────┘        │
                         │                      ▼
                         │ (expiry: 90d elapsed)│
                         ▼                      │
             ┌─────────────────────────┐        │
             │   ARCHIVED_PERMANENT    │        │
             └─────────────────────────┘        │
                         ▲                      │
                         └──────────────────────┘
```
- **States:** `ACTIVE`, `DEACTIVATED`, `ARCHIVED_REVERSIBLE`, `ARCHIVED_PERMANENT` (terminal).
- **Transitions:**
  - `ACTIVE -> DEACTIVATED`: Deactivation with recorded reason.
  - `DEACTIVATED -> ACTIVE`: Immediate reactivation.
  - `DEACTIVATED -> ARCHIVED_REVERSIBLE`: Archival after deactivation threshold. Reversibility window set (`now + 90 days`).
  - `ARCHIVED_REVERSIBLE -> ACTIVE`: Restoration permitted only while `now <= reversibility_expires_at`.
  - `ARCHIVED_REVERSIBLE -> ARCHIVED_PERMANENT`: Transitioned automatically by periodic Celery task or upon late restoration attempt (DEF-SA-01).

### 2.2 Role Assignment Lifecycle (`CW-SA-02`)
- **States:** `SCHEDULED`, `ACTIVE`, `EXTENDED`, `EXPIRED`, `REVOKED`
- **Transitions:**
  - `SCHEDULED -> ACTIVE`: Triggered when `valid_from <= now`.
  - `ACTIVE -> EXTENDED`: Extended validity date applied by Super Admin.
  - `ACTIVE / EXTENDED -> EXPIRED`: Triggered when `valid_to <= now`.
  - `SCHEDULED / ACTIVE / EXTENDED -> REVOKED`: Early emergency revocation or automatic cascade upon user deactivation.

### 2.3 Purge Request Dual-Authorization Lifecycle (`BW-SA-01`, `BW-SA-02`, `CW-SA-01`)
- **States:** `REQUESTED`, `AUTHORIZED`, `REJECTED`, `PURGED`
- **Rules:**
  - Requester (`Super Admin`) and Authorizer (`IT Head`) must be distinct users (Separation of Duties).
  - Permanent purge physically scrubs historical archive records only after statutory retention period expires.

---

## 3. RBAC & Closed-Verb Permissions

All permissions adhere strictly to closed verbs (`view`, `create`, `update`, `delete`, `approve`, `assign`, `revoke`, `export`, `restore`):

| Permission Code | Description | Role Grants |
|---|---|---|
| `superadmin.user.view` | View user accounts and profiles | Super Admin |
| `superadmin.user.create` | Create new basic user accounts | Super Admin |
| `superadmin.user.update` | Update user profiles and statuses | Super Admin |
| `superadmin.user.delete` | Deactivate user accounts | Super Admin |
| `superadmin.user.restore` | Reactivate or restore user accounts | Super Admin |
| `superadmin.user.import` | Bulk import user accounts from CSV | Super Admin |
| `superadmin.user.export` | Export user account directories | Super Admin |
| `superadmin.role.view` | Inspect role definitions and assignments | Super Admin |
| `superadmin.role.assign` | Assign or reassign roles to users | Super Admin |
| `superadmin.role.revoke` | Revoke held role assignments | Super Admin |
| `superadmin.role.update` | Extend validity of active role assignments | Super Admin |
| `superadmin.archive.view` | Search and inspect archived records | Super Admin |
| `superadmin.archive.create` | Archive deactivated users or historical data | Super Admin |
| `superadmin.archive.restore` | Restore reversible archived users or data | Super Admin |
| `superadmin.archive.export` | Export archive status reports | Super Admin |
| `superadmin.purge.create` | Request permanent data purge | Super Admin |
| `superadmin.purge.approve` | Authorize permanent data purge | IT Head, Director |
| `superadmin.audit_log.view` | Inspect security and audit event logs | Super Admin, IT Head, Director |
| `superadmin.audit_log.export` | Export compliance audit reports | Super Admin |
| `superadmin.system_config.view` | View system parameter configurations | Super Admin |
| `superadmin.system_config.update` | Update system parameter policies | Super Admin |

---

## 4. API Endpoint Reference

Base path: `/api/v1/superadmin/`

### 4.1 User Account Management
- `GET /users/`: List users with search, type, and status filters.
- `POST /users/`: Create a single user account.
- `GET /users/{user_id}/`: Retrieve user account details.
- `PATCH /users/{user_id}/`: Update editable user profile fields.
- `POST /users/{user_id}/deactivate/`: Deactivate account (`RequiresStepUpAuth`).
- `POST /users/{user_id}/reactivate/`: Reactivate account.
- `POST /users/{user_id}/archive/`: Move deactivated user to `ARCHIVED_REVERSIBLE` (`RequiresStepUpAuth`).
- `POST /users/{user_id}/restore/`: Restore archived user within reversibility window (`RequiresStepUpAuth`).
- `POST /users/bulk-create/`: Batch create user accounts from CSV (`RequiresStepUpAuth`).
- `POST /users/bulk-status/`: Batch update user activation status (`RequiresStepUpAuth`).
- `GET /users/export/`: Export user accounts directory.

### 4.2 Role Assignment Management
- `GET /roles/`: List role assignments with user, role name, and status filters.
- `POST /roles/`: Assign an additional role.
- `POST /roles/{assignment_id}/extend/`: Extend validity period of active role.
- `POST /roles/{assignment_id}/revoke/`: Early emergency revocation (`RequiresStepUpAuth`).
- `POST /roles/{assignment_id}/reassign/`: Reassign role with handover summary.

### 4.3 Historical Archive & Purge
- `GET /archive/`: List historical archives.
- `POST /archive/`: Archive historical dataset with backup reference.
- `POST /archive/{archive_id}/restore/`: Restore archived historical dataset (`RequiresStepUpAuth`).
- `GET /archive/export/`: Export archived datasets report.
- `GET /purge/requests/`: List purge authorization requests.
- `POST /purge/requests/`: Request permanent data purge.
- `POST /purge/requests/{request_id}/authorize/`: Dual-authorize or reject purge request (`RequiresStepUpAuth`, IT Head only).

### 4.4 Audit & System Configuration
- `GET /audit/`: List immutable audit logs.
- `GET /audit/export/`: Export compliance audit log report.
- `GET /config/`: List active system parameter policies.
- `POST /config/`: Create a new version of an effective-dated system parameter.
- `GET /dashboard/`: Real-time aggregated governance metrics.

---

## 5. External Contracts (`contracts.py`)

Other modules must interact with Super Admin **exclusively** through `modules.superadmin.contracts`:

1. `get_user_account_records(user_ids: Iterable[int]) -> dict[int, UserAccountInfo]`
   Returns basic user metadata, identity, and activation status for requested user IDs.
2. `get_active_role_assignments(user_ids: Iterable[int]) -> dict[int, list[RoleAssignmentInfo]]`
   Returns currently active additional roles held by requested user IDs.
3. `get_archived_user_statuses(user_ids: Iterable[int]) -> dict[int, ArchivedUserInfo]`
   Returns archival status and remaining reversibility window for requested user IDs.

---

## 6. Celery Beat Schedule

| Job Name | Task | Schedule | Queue |
|---|---|---|---|
| `superadmin.finalize-archived-user-reversibility-expiry` | `superadmin.finalize_archived_user_reversibility_expiry` | Hourly (`0 * * * *`) | `periodic` |
| `superadmin.activate-scheduled-roles` | `superadmin.activate_scheduled_roles` | Every 15 min (`*/15 * * * *`) | `periodic` |
| `superadmin.expire-time-bound-roles` | `superadmin.expire_time_bound_roles` | Every 15 min (`*/15 * * * *`) | `periodic` |

---

## 7. Defect Resolution Summary (`DEF-SA-01`)

- **Defect ID:** `DEF-SA-01`
- **Component:** `modules/superadmin/services/user_archive.py` (`restore_archived_user`)
- **Workflow:** `BW-SA-08` (Archived User Reversibility Window Expiry)
- **Problem Statement:** In the baseline implementation, when restoration was attempted on an account whose reversibility window had expired (`reversibility_expires_at < now`), the service raised `ConflictError` inside an atomic transaction. This rolled back the status update, leaving the user in `ARCHIVED_REVERSIBLE` instead of finalizing them as `ARCHIVED_PERMANENT`.
- **Resolution:** Updated `services/user_archive.py` to persist and commit `activation_status = ARCHIVED_PERMANENT` before raising the `ConflictError`. Verified across all 4 spec test suites (`FR-TEST-025`, `UC-TEST-019`, `BR-TEST-007`, `WF-TEST-008`).
