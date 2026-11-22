# System Administration (`superadmin`) Module Blueprint

- **Module Code:** `superadmin`
- **URL Segment:** `/api/v1/superadmin/`
- **Client Route Segment:** `/superadmin/`
- **Specification Source:** `system_admin_srs/` (Problem Statement v1.4, Requirement Registry v1.1, Use Case Specifications v1.1, Business Rule Specifications v1.1, Workflow Specifications v1.1, Traceability Matrix v1.1)
- **Document Version:** 1.0.0 (Phase 2 Deliverable)
- **Status:** Approved in writing (Phase 2 Gate: Student 1 Mokshith & Student 2 Banala Vasanthi Laxmi cross-sign-off, 2026-11-21 / 2026-11-22)

---

## Step 3.1 (a) — Traceability Table

This table maps every business rule (`BR-SA-001` through `BR-SA-035`), use case (`UC-SA-001` through `UC-SA-034`), workflow (`CW-SA-01` through `CW-SA-03`, `BW-SA-01` through `BW-SA-09`), and requirement issue (`ISS-SA-004`, `CFR-SA-001..023`, `AFR-SA-001..082`) to its layer and planned enforcement point.

In accordance with **ADR-0002**, **ADR-0014**, and the Phase 1 rulings, requirements that manage native identity accounts (`auth_user`), credentials, 2FA, session establishment, designation assignments, and active role switching are owned natively by **IAM / `Fusion_System_Administrator`**; they do not have tables in `fusion_integrated` and are explicitly documented as IAM boundary contracts and known gaps in Steps 3.6 and 3.8(h). The **Governance** bounded context (archival lifecycles, dual-authorization purge, effective-dated policy parameters, immutable compliance auditing, and scheduled Celery tasks) is built natively inside `modules/superadmin/`.

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| **BR-SA-001** | Institute identity uniqueness and immutability (Roll No / PF No) | IAM Boundary / Domain | `Fusion_System_Administrator` (ERP `auth_user`/`globals_extrainfo`) + `domain/validators.py` (`validate_institute_id`) | IAM-native identity state. In `superadmin`, validated in snapshot during user archival. |
| **BR-SA-002** | Valid institute email domain (`@iiitdmj.ac.in`) | IAM Boundary / Domain | `Fusion_System_Administrator` + `domain/validators.py` (`validate_institute_email`) | Enforced during account provisioning in IAM; validated on archival snapshot. |
| **BR-SA-003** | Required attributes per user type (Programme/Batch for Students; Dept/EmployeeID for Faculty/Staff) | IAM Boundary / Domain | `Fusion_System_Administrator` (ERP shadow models) + `domain/validators.py` | Enforced at ERP/IAM identity creation. |
| **BR-SA-004** | User archival eligibility: only deactivated accounts with zero pending transactions after elapsed deactivation interval | Domain / Services | `domain/archival_policy.py` (`assess_user_archival_eligibility`), `services/archival.py` | Core governance rule. Checks deactivation duration against effective policy. |
| **BR-SA-005** | Archived user reversible restoration window (configurable, default 30 days; ISS-SA-004) | Domain / Models / Schedule | `domain/archival_policy.py`, `models/archival.py` (`reversible_until`), `schedule.py` | Restorable by Super Admin strictly within window; Celery sweep finalizes permanent state. |
| **BR-SA-006** | Multiple concurrent roles support per user | IAM Boundary | `Fusion_System_Administrator` (`globals_holdsdesignation`) | Native to IAM multi-role session and JWT active role resolution. |
| **BR-SA-007** | Singular role occupancy (one active holder per scope) | IAM Boundary | `Fusion_System_Administrator` (`assign_role` command / IAM service) | Managed at designation assignment in IAM. |
| **BR-SA-008** | Role assignment dating (mandatory start date, mandatory end date if time-bound) | IAM Boundary | `Fusion_System_Administrator` (IAM role service) | Governs role assignment scheduling in IAM. |
| **BR-SA-009** | Automatic role activation and expiry on scheduled dates | IAM Boundary / Scheduled | `Fusion_System_Administrator` (IAM scheduler / Celery) | Evaluates effective date ranges in IAM. |
| **BR-SA-010** | Role user-type eligibility matrix (e.g. Dean requires Faculty) | IAM Boundary | `Fusion_System_Administrator` (`api/models/erp.py`) | Enforced when assigning designations in IAM. |
| **BR-SA-011** | Mutually conflicting roles validation (anti-collision) | IAM Boundary | `Fusion_System_Administrator` (IAM role service) | Evaluated before granting second designation in IAM. |
| **BR-SA-012** | Role reassignment workflow handover and task transfer | IAM Boundary / Services | `Fusion_System_Administrator` (`api/views/roles.py`) | Work item reassignment in operational modules. |
| **BR-SA-013** | Previous holder read-only audit access (default 90 days) | IAM Boundary | `Fusion_System_Administrator` (IAM permissions/scopes) | Scoped temporary grant in IAM. |
| **BR-SA-014** | Role revocation handling (standard notice >= 1 day vs immediate emergency) | IAM Boundary | `Fusion_System_Administrator` (IAM role service) | Revocation lifecycle in IAM. |
| **BR-SA-015** | Automatic role revocation upon user account deactivation | IAM Boundary | `Fusion_System_Administrator` (`deactivate_user` service) | Cascades role revocations upon ERP deactivation in IAM. |
| **BR-SA-016** | Role expiry reminder (lead time default 7 days) and extension | IAM Boundary / Scheduled | `Fusion_System_Administrator` (IAM notifications & schedule) | Scheduled notification in IAM. |
| **BR-SA-017** | Historical data archival eligibility (data category, closed academic session) | Domain / Services | `domain/archival_policy.py`, `services/historical_archive.py` | Verifies closed status before historical data archival. |
| **BR-SA-018** | Pre-archive backup creation and checksum verification | Services | `services/historical_archive.py` (`verify_archive_backup`) | Generates SHA-256 backup checksum before moving archive. |
| **BR-SA-019** | Archive data retention policy (immutable during statutory retention period) | Domain / Models | `domain/archival_policy.py`, `models/archival.py` (`retention_expires_at`) | Prevents premature purge requests before retention elapses. |
| **BR-SA-020** | Archived data access mode (strictly read-only) | Selectors / API | `selectors/archival.py`, `api/views/archival.py` | No modification endpoints exist for archived records. |
| **BR-SA-021** | Permanent purge eligibility (statutory retention fully elapsed) | Domain / Services | `domain/archival_policy.py` (`is_historical_data_purge_eligible`), `services/purge.py` | Rejects purge creation if `today < retention_expires_at`. |
| **BR-SA-022** | Dual authorization for permanent purge (Super Admin initiate + IT Head authorize) | Domain / Services / Models | `domain/state_machine.py` (`PurgeAuthorizationStateMachine`), `models/archival.py` (`PurgeRequest`) | Mandatory 2-person rule. Super Admin cannot self-approve. |
| **BR-SA-023** | Role change notification timing (< 1 hour of event) | Services / Outbox | `models/notifications.py` (`NotificationOutbox`), `services/notifications.py` | Transactional outbox pattern dispatches email notifications. |
| **BR-SA-024** | Security alert threshold (5 consecutive failed logins trigger alert) | IAM Boundary / Outbox | `Fusion_System_Administrator` (`backend/urls.py` throttle) + `services/notifications.py` | IAM rate-limiting triggers security alert outbox. |
| **BR-SA-025** | Immutable audit entry retention (tamper-proof, append-only, permanent) | Models / Services | `models/audit.py` (`SuperAdminAuditLog`), `services/audit.py` | Custom model `save()` and `delete()` reject modifications/deletions. |
| **BR-SA-026** | Super Admin data isolation (zero access to operational/academic content) | Architecture / Selectors | `selectors/scoping.py`, API views | Boundary guard: no ORM models or queries touch grades/finances/complaints. |
| **BR-SA-027** | Super Admin authentication, 2FA, single active session, and inactivity timeout | IAM Boundary / Shell | `Fusion_System_Administrator` (`/api/iam/v1/auth/login`, JWT expiration) | Managed by IAM session tokens and browser cookie policies. |
| **BR-SA-028** | Denial of self-modification of Super Admin privileges | Domain / IAM Boundary | `domain/validators.py` (`validate_no_self_modification`), `Fusion_System_Administrator` | Super Admin role managed externally via direct DB command by IT team. |
| **BR-SA-029** | Critical destructive operation re-authentication confirmation | API / Services | `api/serializers/purge.py`, `services/purge.py` | Requires explicit credential/token confirmation before purge execution. |
| **BR-SA-030** | Bulk operation transaction size limit (<= 1,000 records) | Domain / Services | `domain/validators.py` (`validate_bulk_size`), `services/bulk.py` | Enforces max batch chunk size on bulk requests. |
| **BR-SA-031** | Mandatory password rotation policy (e.g. 90/180 days) | IAM Boundary | `Fusion_System_Administrator` (IAM credential service) | IAM tracks `password_changed_at`. |
| **BR-SA-032** | Notification channel policy (Email primary, SMS/Portal secondary) | Services / Outbox | `models/notifications.py` (`channel=EMAIL`) | Outbox defaults to institutional email. |
| **BR-SA-033** | Comprehensive audit event coverage and schema standard | Models / Services | `models/audit.py`, `services/audit.py` | Captures timestamp, actor, action, target, IP, and context metadata. |
| **BR-SA-034** | Active role selection and strict permission enforcement | Architecture / IAM | `fusion_auth/principal.py`, `api/permissions.py` | Validates `request.principal.has_permission()` for active role. |
| **BR-SA-035** | Permitted system configuration boundary (governance parameters only) | Domain / Models / Services | `domain/validators.py` (`validate_configuration_key`), `models/config.py` | Whitelist restricts editable parameters to retention, timeout, bulk limits. |
| **UC-SA-001** | Create Basic User (Single) | IAM Boundary | `Fusion_System_Administrator` (`/api/users/add-staff/`, `/api/users/add-faculty/`) | Native to IAM console. |
| **UC-SA-002** | View User Profile | Directory / IAM | `modules/directory/contracts.py`, `IamClient.get_users()` | Uses existing Directory contracts. |
| **UC-SA-003** | Update User Profile | IAM Boundary | `Fusion_System_Administrator` (`api/views/users.py`) | Native to IAM / ERP portal. |
| **UC-SA-004** | Deactivate User | IAM Boundary | `Fusion_System_Administrator` (IAM `deactivate_user`) | ERP `is_active=False` in IAM. |
| **UC-SA-005** | Reactivate User | IAM Boundary | `Fusion_System_Administrator` (IAM `reactivate_user`) | ERP `is_active=True` in IAM. |
| **UC-SA-006** | Bulk Create Users (CSV upload <= 1000) | IAM Boundary | `Fusion_System_Administrator` (`/api/users/import/`) | IAM bulk import utility. |
| **UC-SA-007** | Bulk User Status Update | IAM Boundary | `Fusion_System_Administrator` (`api/views/batches.py`) | IAM batch management. |
| **UC-SA-008** | Assign Role (Immediate or Future-Dated) | IAM Boundary | `Fusion_System_Administrator` (`assign_role` command / API) | IAM role management. |
| **UC-SA-009** | Reassign Role (Handover) | IAM Boundary | `Fusion_System_Administrator` (`api/views/roles.py`) | IAM role reassignment. |
| **UC-SA-010** | Revoke Role (Standard or Emergency) | IAM Boundary | `Fusion_System_Administrator` (`assign_role --remove`) | IAM role revocation. |
| **UC-SA-011** | Extend Role Validity | IAM Boundary | `Fusion_System_Administrator` (IAM role service) | IAM time-bound role extension. |
| **UC-SA-012** | View Role Metadata and Availability | IAM Boundary | `Fusion_System_Administrator` (`/api/iam/v1/academics/directory`) | Directory / IAM query. |
| **UC-SA-013** | Switch Active Role | Shell / IAM Client | `fusion_auth/client.py` (`set_active_role`), `Fusion-client` shell | Managed via IAM `/api/iam/v1/me` and session token. |
| **UC-SA-014** | Access Module by Active Role | Core / Auth | `fusion_auth.permissions.RequirePermission` | Evaluates `request.principal.permissions`. |
| **UC-SA-015** | Archive Eligible Deactivated User | Services / Models | `services/archival.py` (`archive_user`), `models/archival.py` | Creates `ArchivedUserRecord`, sets `reversible_until` = now + 30 days. |
| **UC-SA-016** | Archive Historical Dataset (Academic session, logs) | Services / Models | `services/historical_archive.py`, `models/archival.py` | Verifies closed status, records backup checksum and retention date. |
| **UC-SA-017** | Search and View Archived Records | Selectors / API | `selectors/archival.py`, `api/views/archival.py` | Filterable read-only queries with pagination and field scoping. |
| **UC-SA-018** | Restore Archived User (Within Reversible Window) | Services / Domain | `services/archival.py` (`restore_archived_user`), `domain/archival_policy.py` | Restores account if `now <= reversible_until`; marks restored in DB. |
| **UC-SA-019** | Restore Archived Historical Dataset | Services / Models | `services/historical_archive.py` (`restore_historical_data`) | Restores dataset to operational storage; updates archive state. |
| **UC-SA-020** | Generate and Export Archive Report | Selectors / API | `selectors/archival.py` (`export_archive_report`), `api/views/archival.py` | CSV / JSON export of archived records metadata. |
| **UC-SA-021** | Export Archived Data for Cold/External Storage | Services / API | `services/historical_archive.py` (`export_for_external_storage`) | Produces signed data manifest for off-site cold tier. |
| **UC-SA-022** | Request Permanent Data Purge (Super Admin) | Services / Models | `services/purge.py` (`create_purge_request`), `models/archival.py` | Initiates dual-auth request; sets state to `pending_it_head`. |
| **UC-SA-023** | Authorize/Reject Permanent Data Purge (IT Head) | Services / Domain | `services/purge.py` (`decide_purge_request`), `domain/state_machine.py` | IT Head decision gate; triggers permanent purge or records rejection. |
| **UC-SA-024** | View Audit Log | Selectors / API | `selectors/audit.py`, `api/views/audit.py` | Paginated, filterable immutable log query with date/actor/action filters. |
| **UC-SA-025** | Generate Audit Compliance Report | Selectors / API | `selectors/audit.py` (`export_audit_report`), `api/views/audit.py` | Export audit trail for institutional compliance officers. |
| **UC-SA-026** | View Super Admin Dashboard Metrics | Selectors / API | `selectors/dashboard.py`, `api/views/dashboard.py` | Aggregates counts: active/archived users, pending purges, audit events. |
| **UC-SA-027** | Configure Permitted System Parameters | Services / Models | `services/config.py`, `models/config.py` (`SystemPolicyParameter`) | Effective-dated policy update; validates keys against whitelist. |
| **UC-SA-028** | Activate Scheduled Role Assignment (Cron/Beat) | IAM Boundary / Schedule | `Fusion_System_Administrator` (IAM Celery Beat) | Event-driven activation in IAM. |
| **UC-SA-029** | Expire Time-Bound Role (Cron/Beat) | IAM Boundary / Schedule | `Fusion_System_Administrator` (IAM Celery Beat) | Daily sweep for expiring designations in IAM. |
| **UC-SA-030** | Send Role-Expiry Reminder (Cron/Beat) | IAM Boundary / Schedule | `Fusion_System_Administrator` (IAM Celery Beat) | Periodic reminder sweep in IAM. |
| **UC-SA-031** | Finalize Archived User as Permanently Non-Restorable | Services / Schedule | `tasks.py` (`expire_reversibility_window_task`), `schedule.py` | Daily sweep: flags `finalized_permanent` when `now > reversible_until`. |
| **UC-SA-032** | Process Failed-Login Threshold Alert | IAM Boundary / Outbox | `Fusion_System_Administrator` + `services/notifications.py` | Emits security alert when consecutive failures >= 5. |
| **UC-SA-033** | Authenticate Super Admin and Establish Session | IAM Boundary | `Fusion_System_Administrator` (`/api/iam/v1/auth/login`) | IAM token exchange and MFA verification. |
| **UC-SA-034** | Terminate Inactive Super Admin Session | IAM Boundary / Shell | `Fusion_System_Administrator` (Token TTL) / Frontend idle timer | Revokes session token on inactivity timeout. |
| **CW-SA-01** | Permanent Data Purge Authorization Lifecycle | Domain / Services / Models | `domain/state_machine.py`, `services/purge.py` | Composite workflow: Initiate -> Dual-Auth Review -> Execution -> Audit. |
| **CW-SA-02** | Time-Bound Role Validity Lifecycle | IAM Boundary | `Fusion_System_Administrator` (IAM role service & schedule) | Scheduled -> Active -> Extended/Expired/Revoked. |
| **CW-SA-03** | Deactivated User Resolution and Archive Lifecycle | Domain / Services / Models | `domain/state_machine.py`, `services/archival.py` | Active -> Deactivated -> Archived Reversible -> Permanent/Restored. |
| **BW-SA-01** | Permanent Data Purge — Approved Path | Domain / Services | `services/purge.py` (`execute_purge`) | Dual authorization satisfied; physical record destruction + audit log. |
| **BW-SA-02** | Permanent Data Purge — Rejected Path | Domain / Services | `services/purge.py` (`reject_purge`) | IT Head rejects request; archive record restored to read-only status. |
| **BW-SA-03** | Immediate Role Assignment to Expiry | IAM Boundary | `Fusion_System_Administrator` | Start date <= today -> immediate activation. |
| **BW-SA-04** | Future-Dated Role Assignment to Expiry | IAM Boundary | `Fusion_System_Administrator` | Start date > today -> scheduled state. |
| **BW-SA-05** | Role Validity Extension | IAM Boundary | `Fusion_System_Administrator` | Extends end date of active time-bound role. |
| **BW-SA-06** | Deactivated User Reactivation | IAM Boundary | `Fusion_System_Administrator` | Reverses deactivation before archival initiation. |
| **BW-SA-07** | Archived User Restoration Within Reversible Window | Domain / Services | `services/archival.py` (`restore_archived_user`) | Successful restoration while `now <= reversible_until`. |
| **BW-SA-08** | Archived User Reversibility Window Expiry | Schedule / Tasks | `tasks.py` (`sweep_reversibility_expiry`), `schedule.py` | Celery beat transitions record to `finalized_permanent` (ISS-SA-004). |
| **BW-SA-09** | Historical Data Archive and Restore | Services / Models | `services/historical_archive.py` | Pre-archive backup -> read-only storage -> optional restore. |
| **ISS-SA-004**| 30-Day Reversible Archival Window Governance | Domain / Models / Schedule | `models/archival.py`, `domain/archival_policy.py`, `schedule.py` | 30-day default window before permanent non-restorable finalization. |
| **CFR-SA-001..023** | Complete Core Functional Requirements (001: Creation, 002: Immutability, 005: Roles, 010: Archival, 013: Purge, 017: Audit, 021: Security) | Architectural Layers | All layers as mapped above | Governs full specification compliance across IAM and Governance. |
| **AFR-SA-001..082** | Atomic Functional Requirements (Specific validation checks, form schemas, notification templates) | Application Layers | Domain validators, DRF serializers, service methods | Granular unit tests verify each atomic condition. |

---

## Step 3.2 (b) — Domain Model

All models in `modules/superadmin/models/` inherit from `core.db.mixins.TimeStampedModel` (`created_at`, `updated_at`). All person references use plain integer `user_id` attributes (`UserScopedModel` or explicit integer fields). Under no circumstances are foreign keys created pointing to `auth_user` or any external database.

### 1. Aggregate: Archival Governance (`models/archival.py`)

#### Entity: `ArchivedUserRecord`
Tracks institutional users placed into archival, snapshot metadata, reversible restoration deadlines, and permanent finalization status.
- `user_id` (`PositiveIntegerField`, primary key, `unique=True`, `db_index=True`): Plain integer ERP user ID.
- `institute_id` (`CharField(max_length=32, db_index=True)`): Immutable Institute ID (Roll No / PF No) captured at archival time.
- `username` (`CharField(max_length=150, db_index=True)`): Historical username snapshot.
- `email` (`EmailField()`): Institutional email snapshot.
- `user_kind` (`CharField(max_length=16)`): `'student'`, `'faculty'`, or `'staff'`.
- `status` (`CharField(max_length=24, db_index=True)`): Choices:
  - `reversible`: Account archived, within 30-day restoration window.
  - `restored`: Restored to operational state during the window.
  - `finalized_permanent`: Window expired; permanently non-restorable (ISS-SA-004).
- `archived_at` (`DateTimeField(db_index=True)`): Timestamp when archival occurred.
- `reversible_until` (`DateTimeField(db_index=True)`): Exact timestamp when reversibility expires (`archived_at + window`).
- `authorized_by` (`PositiveIntegerField()`): Plain integer `user_id` of the Super Admin who executed archival.
- `archival_reason` (`TextField()`): Mandatory justification.
- `restored_at` (`DateTimeField(null=True, blank=True)`): Timestamp of restoration.
- `restored_by` (`PositiveIntegerField(null=True, blank=True)`): Plain integer `user_id` of restoring admin.
- `restoration_reason` (`TextField(blank=True)`): Justification for account restoration.
- `finalized_permanent_at` (`DateTimeField(null=True, blank=True)`): Timestamp when Celery marked permanent finalization.
- `metadata_snapshot` (`JSONField(default=dict, blank=True)`): Serialized user profile, past role history, and department data.

*Database Constraints & Indexes:*
- `CheckConstraint(check=Q(reversible_until__gte=F("archived_at")), name="archived_user_reversible_deadline_valid")`
- `Index(fields=["status", "reversible_until"], name="archived_user_status_deadline_idx")`
- `Index(fields=["institute_id", "status"], name="archived_user_inst_status_idx")`

*Invariants:*
- `reversible_until` is immutable once set upon archival creation.
- Once status transitions to `finalized_permanent`, restoration is permanently prohibited (enforced in `domain/archival_policy.py`).

#### Entity: `HistoricalDataArchive`
Represents closed operational datasets moved to cold/archival storage.
- `id` (`BigAutoField`, primary key).
- `dataset_category` (`CharField(max_length=64, db_index=True)`): e.g. `'academic_session'`, `'attendance_logs'`, `'audit_logs'`.
- `title` (`CharField(max_length=200)`): Human-readable archive title.
- `date_range_start` (`DateField()`): Start date of data coverage.
- `date_range_end` (`DateField()`): End date of data coverage.
- `record_count` (`PositiveIntegerField()`): Total rows/records included.
- `backup_file_path` (`CharField(max_length=255)`): Path or URI to verified pre-archive backup file.
- `backup_checksum` (`CharField(max_length=64)`): SHA-256 cryptographic hash of backup file (BR-SA-018).
- `retention_expires_at` (`DateField(db_index=True)`): Date after which data is statutory eligible for purge (BR-SA-019, BR-SA-021).
- `is_restored` (`BooleanField(default=False)`).
- `restored_at` (`DateTimeField(null=True, blank=True)`).
- `is_purged` (`BooleanField(default=False, db_index=True)`).
- `archived_by` (`PositiveIntegerField()`): Super Admin `user_id`.
- `summary_metadata` (`JSONField(default=dict, blank=True)`).

*Database Constraints & Indexes:*
- `CheckConstraint(check=Q(date_range_end__gte=F("date_range_start")), name="hist_archive_date_range_valid")`
- `CheckConstraint(check=Q(retention_expires_at__gte=F("date_range_end")), name="hist_archive_retention_valid")`
- `Index(fields=["dataset_category", "is_purged"], name="hist_archive_cat_purged_idx")`

#### Entity: `PurgeRequest`
Encodes the dual-authorization permanent purge workflow (BR-SA-021, BR-SA-022, CW-SA-01).
- `id` (`BigAutoField`, primary key).
- `archive` (`ForeignKey(HistoricalDataArchive, on_delete=models.PROTECT, related_name="purge_requests")`).
- `status` (`CharField(max_length=24, db_index=True)`):
  - `pending_it_head`: Initiated by Super Admin; awaiting IT Head review.
  - `approved`: Authorized by IT Head; queued for physical execution.
  - `rejected`: Declined by IT Head.
  - `purged`: Physically destroyed; records expunged.
  - `expired`: IT Head did not act within approval TTL (72 hours).
- `requested_by` (`PositiveIntegerField()`): Super Admin `user_id` who initiated the request.
- `requested_at` (`DateTimeField(auto_now_add=True, db_index=True)`).
- `request_reason` (`TextField()`): Mandatory justification citing regulatory retention lapse.
- `it_head_id` (`PositiveIntegerField(null=True, blank=True)`): Plain integer `user_id` of IT Head.
- `it_head_decision_at` (`DateTimeField(null=True, blank=True)`).
- `it_head_comments` (`TextField(blank=True)`).
- `purged_at` (`DateTimeField(null=True, blank=True)`).
- `execution_summary` (`JSONField(default=dict, blank=True)`): Record counts destroyed and execution verification logs.

*Database Constraints & Indexes:*
- `CheckConstraint(check=~Q(requested_by=F("it_head_id")), name="purge_dual_auth_different_actors")`: Prevents self-authorization.
- `Index(fields=["status", "requested_at"], name="purge_req_status_req_idx")`

---

### 2. Aggregate: Effective-Dated System Governance Policy (`models/config.py`)

#### Entity: `SystemPolicyParameter`
Implements Step 2.8: administrative governance settings are **effective-dated and never edited in place**—they are superseded by appending a new version.
- `id` (`BigAutoField`, primary key).
- `key` (`CharField(max_length=64, db_index=True)`): Whitelisted parameter key (e.g. `archival.reversibility_window_days`, `purge.approval_ttl_hours`, `bulk.max_batch_size`).
- `value` (`CharField(max_length=255)`): Stored parameter value.
- `value_type` (`CharField(max_length=16)`): `'int'`, `'string'`, `'bool'`, `'json'`.
- `version` (`PositiveIntegerField(default=1)`): Incrementing version number.
- `effective_from` (`DateTimeField(default=timezone.now, db_index=True)`): When this policy version took effect.
- `effective_to` (`DateTimeField(null=True, blank=True, db_index=True)`): When superseded; `NULL` indicates the current active policy.
- `description` (`TextField(blank=True)`).
- `updated_by` (`PositiveIntegerField()`): Plain integer `user_id` of the modifying Super Admin.

*Database Constraints & Indexes:*
- `UniqueConstraint(fields=["key", "version"], name="policy_param_key_version_unique")`
- `CheckConstraint(check=Q(effective_to__isnull=True) | Q(effective_to__gt=F("effective_from")), name="policy_param_effective_dates_valid")`
- `Index(fields=["key", "effective_to"], name="policy_param_key_active_idx")`

*Invariants:*
- Existing rows are immutable; `save()` on an existing row without an explicit supersede workflow raises `DomainError`.
- If unseeded, selectors fall back to hardcoded platform safe defaults (e.g. `reversibility_window_days=30`, `bulk.max_batch_size=1000`) without raising a 500 error.

---

### 3. Aggregate: Immutable Compliance Audit Trail (`models/audit.py`)

#### Entity: `SuperAdminAuditLog`
CRITICAL COMPLIANCE RECORD: Retained permanently; strictly append-only; immutable at both database and ORM levels (BR-SA-025, BR-SA-033).
- `id` (`BigAutoField`, primary key).
- `timestamp` (`DateTimeField(auto_now_add=True, db_index=True)`): Immutable creation time.
- `actor_id` (`PositiveIntegerField(db_index=True)`): Plain integer `user_id`.
- `actor_username` (`CharField(max_length=150)`): Username at event time.
- `actor_role` (`CharField(max_length=64)`): Active designation during event (`super_admin` or `it_head`).
- `action` (`CharField(max_length=64, db_index=True)`): e.g. `archival.user.created`, `archival.user.restored`, `purge.requested`, `purge.authorized`, `policy.updated`.
- `target_id` (`CharField(max_length=64, blank=True, db_index=True)`): ID of target entity.
- `target_type` (`CharField(max_length=64, blank=True)`): e.g. `user`, `archive`, `purge_request`, `policy`.
- `result` (`CharField(max_length=16)`): `'SUCCESS'` or `'FAILURE'`.
- `ip_address` (`GenericIPAddressField(null=True, blank=True)`).
- `user_agent` (`CharField(max_length=255, blank=True)`).
- `reason` (`TextField(blank=True)`).
- `context_metadata` (`JSONField(default=dict, blank=True)`): State diffs, hash digests, batch IDs.

*Database Constraints & Indexes:*
- `Index(fields=["actor_id", "-timestamp"], name="audit_actor_time_idx")`
- `Index(fields=["action", "-timestamp"], name="audit_action_time_idx")`
- `Index(fields=["target_type", "target_id", "-timestamp"], name="audit_target_time_idx")`

*Immutability Enforcement:*
- `delete()` raises `PermissionError("Audit log entries are permanent and strictly immutable.")`.
- `save()` raises `PermissionError("Audit log entries cannot be modified.")` if `self.pk is not None`.

#### Entity: `UserActivityLog`
Read-only metadata tracking administrative dashboard and search activities.
- `id` (`BigAutoField`, primary key).
- `user_id` (`PositiveIntegerField(db_index=True)`).
- `activity_type` (`CharField(max_length=64, db_index=True)`).
- `timestamp` (`DateTimeField(auto_now_add=True, db_index=True)`).
- `ip_address` (`GenericIPAddressField(null=True, blank=True)`).
- `session_id` (`CharField(max_length=128, blank=True)`).
- `activity_metadata` (`JSONField(default=dict, blank=True)`).

---

### 4. Aggregate: Notification Outbox (`models/notifications.py`)

#### Entity: `NotificationOutbox`
Transactional outbox pattern guaranteeing at-least-once delivery of administrative notifications (BR-SA-023, BR-SA-032).
- `id` (`BigAutoField`, primary key).
- `recipient_id` (`PositiveIntegerField(db_index=True)`): Target user ID.
- `recipient_email` (`EmailField()`): Institutional email.
- `channel` (`CharField(max_length=16, default="email")`): `'email'`, `'sms'`, `'portal'`.
- `template_code` (`CharField(max_length=64)`): e.g. `user_archived`, `purge_approval_requested`, `purge_authorized`, `security_alert`.
- `subject` (`CharField(max_length=255)`).
- `body` (`TextField()`).
- `status` (`CharField(max_length=16, default="pending", db_index=True)`): `'pending'`, `'sent'`, `'failed'`.
- `scheduled_for` (`DateTimeField(default=timezone.now, db_index=True)`).
- `sent_at` (`DateTimeField(null=True, blank=True)`).
- `retry_count` (`PositiveSmallIntegerField(default=0)`).
- `error_message` (`TextField(blank=True)`).
- `context_data` (`JSONField(default=dict, blank=True)`).

*Database Constraints & Indexes:*
- `Index(fields=["status", "scheduled_for"], name="notif_outbox_status_sched_idx")`

---

## Step 3.3 (c) — State Machines

### 1. User Archival & Restoration Lifecycle (`CW-SA-03`, `BW-SA-07`, `BW-SA-08`, `ISS-SA-004`)

This state machine governs how a deactivated user account is archived, protected by a 30-day reversible restoration window, restored, or permanently finalized.

```
                  +---------------------------+
                  | DEACTIVATED (IAM State)   |
                  +---------------------------+
                                |
                                | [archive_user]
                                | Preconditions: deactivated >= 30 days, zero pending tx
                                v
                  +---------------------------+
                  |    ARCHIVED_REVERSIBLE    | <--------------------+
                  +---------------------------+                      |
                     /                     \                         |
 [restore_archived_user]                 [expire_reversibility_sweep]|
 Precondition: now <= deadline           Precondition: now > deadline| [re-deactivate &
 Actor: super_admin                      Actor: celery_beat          |  re-archive]
                   v                         v                       |
     +-------------------+         +---------------------+           |
     |     RESTORED      |         | FINALIZED_PERMANENT |           |
     +-------------------+         +---------------------+           |
               |                                                     |
               +-----------------------------------------------------+
```

#### Declarative Transition Table
```python
ARCHIVAL_TRANSITIONS = {
    # (current_state, event, actor) -> (next_state, validator_func)
    ("deactivated", "archive", "super_admin"): (
        "reversible",
        "validate_archival_eligibility",
    ),
    ("reversible", "restore", "super_admin"): (
        "restored",
        "validate_restoration_window_open",
    ),
    ("reversible", "expire_window", "system_scheduler"): (
        "finalized_permanent",
        "validate_restoration_window_expired",
    ),
}
```

*State Machine Invariants:*
- Any attempt to trigger `restore` on a user in `finalized_permanent` raises `ReversibilityExpiredError(DomainError)`.
- Illegal transitions are inexpressible and raise `InvalidStateTransitionError`.

---

### 2. Dual-Authorization Permanent Data Purge Workflow (`CW-SA-01`, `BW-SA-01`, `BW-SA-02`)

Governs the permanent destruction of historical archives. It enforces strict separation of duty between the initiating Super Admin and the authorizing IT Head.

```
           +-------------------------+
           |   HISTORICAL ARCHIVE    |
           |  (Retention Expired)    |
           +-------------------------+
                        |
                        | [request_purge]
                        | Preconditions: today >= retention_expires_at, verified backup
                        | Actor: super_admin
                        v
           +-------------------------+
           |     PENDING_IT_HEAD     |
           +-------------------------+
              /          |          \
             /           |           \
  [approve_purge]  [reject_purge]  [expire_ttl_sweep]
  Actor: it_head   Actor: it_head  Actor: celery_beat
         v               v               v
  +-------------+  +------------+  +-------------+
  |  APPROVED   |  |  REJECTED  |  |   EXPIRED   |
  +-------------+  +------------+  +-------------+
         |
         | [execute_purge]
         | Preconditions: status == APPROVED
         | Actor: system_task / super_admin
         v
  +-------------+
  |   PURGED    |
  +-------------+
```

#### Declarative Transition Table
```python
PURGE_TRANSITIONS = {
    # (current_state, event, actor) -> (next_state, validator_func)
    ("none", "request_purge", "super_admin"): (
        "pending_it_head",
        "validate_retention_period_elapsed",
    ),
    ("pending_it_head", "approve_purge", "it_head"): (
        "approved",
        "validate_dual_actor_distinct",
    ),
    ("pending_it_head", "reject_purge", "it_head"): (
        "rejected",
        "validate_dual_actor_distinct",
    ),
    ("pending_it_head", "expire_request", "system_scheduler"): (
        "expired",
        "validate_purge_ttl_exceeded",
    ),
    ("approved", "execute_purge", "super_admin"): (
        "purged",
        "validate_purge_execution_ready",
    ),
}
```

*Purge Invariants:*
- An initiating Super Admin attempting to approve their own request is refused at both domain validation (`validate_dual_actor_distinct`) and database check constraint (`purge_dual_auth_different_actors`).

---

## Step 3.4 (d) — Permission List

The exact content of `modules/superadmin/registry.py`:

```python
"""Registry specification for modules/superadmin.

Defines module metadata, permissions, system tasks, and role grants.
Roles are institute-wide designations matching globals_designation.
"""
from __future__ import annotations

MODULE = {
    "code": "superadmin",
    "label": "System Administration",
    "icon": "ShieldCheck",
    "default_route": "/superadmin/dashboard",
}

PERMISSIONS = (
    # Dashboard & Overview
    "superadmin.dashboard.view",
    # Archival Governance (Users & Datasets)
    "superadmin.archival.view",
    "superadmin.archival.add",
    "superadmin.archival.change",
    # Permanent Purge Dual-Auth Workflow
    "superadmin.purge.view",
    "superadmin.purge.add",
    "superadmin.purge.change",
    # Governance Policies & System Parameters
    "superadmin.policy.view",
    "superadmin.policy.change",
    # Immutable Compliance Audit Logs
    "superadmin.audit.view",
)

SYSTEM_PERMISSIONS = (
    # Scheduled sweeps executed by Celery Beat workers
    "superadmin.sweep_archival",
    "superadmin.sweep_purge",
    "superadmin.drain_outbox",
)

SCOPE_PERMISSIONS: dict[str, str] = {
    # Scoping is institute-wide; no fine-grained department-restricted permissions
}

ROLE_GRANTS = {
    "super_admin": (
        "superadmin.dashboard.view",
        "superadmin.archival.view",
        "superadmin.archival.add",
        "superadmin.archival.change",
        "superadmin.purge.view",
        "superadmin.purge.add",       # Can initiate purge requests
        "superadmin.policy.view",
        "superadmin.policy.change",
        "superadmin.audit.view",
    ),
    "it_head": (
        "superadmin.dashboard.view",
        "superadmin.archival.view",
        "superadmin.purge.view",
        "superadmin.purge.change",    # Can authorize / reject purge requests
        "superadmin.policy.view",
        "superadmin.audit.view",
    ),
}
```

### Architectural Separation
- `fusionlab` (ERP): Owns institute users and designations (`auth_user`, `globals_designation`).
- `fusion_system_db` (IAM): Owns credentials, sessions, module grants, and designation assignments.
- `fusion_integrated`: Owns `modules/superadmin/` business tables. Contains **zero auth tables**.

---

## Step 3.5 (e) — Endpoint List

All endpoints are mounted under `/api/v1/superadmin/`. Every endpoint sits behind two mandatory DRF permission classes:
1. `fusion_auth.permissions.RequireModule` (`superadmin`)
2. `fusion_auth.permissions.RequirePermission` (specific action permission)

| Method | Path | Gates (`RequireModule` + `RequirePermission`) | Returns | Enforces (Spec IDs) |
|---|---|---|---|---|
| `GET` | `/api/v1/superadmin/dashboard/` | `superadmin`, `superadmin.dashboard.view` | `DashboardSummaryDTO` | UC-SA-026 |
| `GET` | `/api/v1/superadmin/archival/users/` | `superadmin`, `superadmin.archival.view` | `Paginated[ArchivedUserDTO]` | UC-SA-017, BR-SA-020 |
| `POST` | `/api/v1/superadmin/archival/users/` | `superadmin`, `superadmin.archival.add` | `ArchivedUserDTO` (201) | UC-SA-015, BR-SA-004, BR-SA-005, ISS-SA-004 |
| `GET` | `/api/v1/superadmin/archival/users/{user_id}/` | `superadmin`, `superadmin.archival.view` | `ArchivedUserDetailDTO` | UC-SA-017 |
| `POST` | `/api/v1/superadmin/archival/users/{user_id}/restore/` | `superadmin`, `superadmin.archival.change` | `ArchivedUserDTO` (200) | UC-SA-018, BR-SA-005, BW-SA-07 |
| `GET` | `/api/v1/superadmin/archival/history/` | `superadmin`, `superadmin.archival.view` | `Paginated[HistoricalArchiveDTO]` | UC-SA-017, BR-SA-020 |
| `POST` | `/api/v1/superadmin/archival/history/` | `superadmin`, `superadmin.archival.add` | `HistoricalArchiveDTO` (201) | UC-SA-016, BR-SA-017, BR-SA-018, BR-SA-019 |
| `POST` | `/api/v1/superadmin/archival/history/{id}/restore/` | `superadmin`, `superadmin.archival.change` | `HistoricalArchiveDTO` (200) | UC-SA-019, BW-SA-09 |
| `GET` | `/api/v1/superadmin/purge/requests/` | `superadmin`, `superadmin.purge.view` | `Paginated[PurgeRequestDTO]` | UC-SA-022, UC-SA-023 |
| `POST` | `/api/v1/superadmin/purge/requests/` | `superadmin`, `superadmin.purge.add` | `PurgeRequestDTO` (201) | UC-SA-022, BR-SA-021, BR-SA-022, CW-SA-01 |
| `POST` | `/api/v1/superadmin/purge/requests/{id}/decision/` | `superadmin`, `superadmin.purge.change` | `PurgeRequestDTO` (200) | UC-SA-023, BR-SA-022, BW-SA-01, BW-SA-02 |
| `POST` | `/api/v1/superadmin/purge/requests/{id}/execute/` | `superadmin`, `superadmin.purge.add` | `PurgeExecutionResultDTO` (200) | UC-SA-023, BR-SA-029 |
| `GET` | `/api/v1/superadmin/policies/` | `superadmin`, `superadmin.policy.view` | `list[PolicyParameterDTO]` | UC-SA-027, BR-SA-035 |
| `POST` | `/api/v1/superadmin/policies/` | `superadmin`, `superadmin.policy.change` | `PolicyParameterDTO` (201) | UC-SA-027, BR-SA-035 |
| `GET` | `/api/v1/superadmin/audit/logs/` | `superadmin`, `superadmin.audit.view` | `Paginated[AuditLogDTO]` | UC-SA-024, BR-SA-025, BR-SA-033 |
| `GET` | `/api/v1/superadmin/audit/export/` | `superadmin`, `superadmin.audit.view` | CSV Stream / Download | UC-SA-025 |

### Client Routes & Guard Specifications

Every client route is rendered within `client/src/modules/superadmin/` and guarded via `RequirePermission`:

| Route Path | Component / Page | Required Permission | Description / Modal Flow |
|---|---|---|---|
| `/superadmin/dashboard` | `DashboardPage` | `superadmin.dashboard.view` | Metrics overview, counts, pending approvals badge. |
| `/superadmin/archival` | `ArchivalManagementPage` | `superadmin.archival.view` | List of archived users and datasets. Contains `ArchiveUserModal`, `RestoreUserModal`. |
| `/superadmin/purge` | `PurgeApprovalsPage` | `superadmin.purge.view` | Dual-auth purge requests. Contains `PurgeRequestModal` (Super Admin), `AuthorizePurgeModal` (IT Head). |
| `/superadmin/policy` | `PolicyConfigPage` | `superadmin.policy.view` | View and supersede effective-dated governance policies (`EditPolicyDrawer`). |
| `/superadmin/audit` | `AuditLogsPage` | `superadmin.audit.view` | Filterable compliance audit logs with `AuditDetailDrawer` and CSV export. |

### Hand-Maintained `Fusion-client` Navigation Entry

For integration into `Fusion-client/src/ui/nav/navigation.js` (`INTEGRATED_MODULES`):

```javascript
{
  id: "superadmin",
  label: "System Administration",
  icon: "ShieldCheck",
  to: "/superadmin",
  section: "administrative",
}
```

---

## Step 3.6 (f) — Contracts

### 1. Exposed Public Interface (`modules/superadmin/contracts.py`)

Other modules interact with `superadmin` strictly through plural signatures returning frozen DTOs:

```python
"""Public contract surface for modules/superadmin.

All getters are plural by design to prevent N+1 queries across module boundaries.
"""
from __future__ import annotations
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class ArchivedUserDTO:
    user_id: int
    institute_id: str
    username: str
    status: str
    archived_at: datetime
    reversible_until: datetime
    is_restorable: bool

@dataclass(frozen=True)
class PolicyParameterDTO:
    key: str
    value: Any
    value_type: str
    version: int
    effective_from: datetime

def get_archived_user_statuses(user_ids: Sequence[int]) -> dict[int, ArchivedUserDTO | None]:
    """Plural batch lookup of user archival statuses."""

def get_active_system_policies(keys: Sequence[str]) -> dict[str, PolicyParameterDTO]:
    """Plural batch lookup of current effective-dated governance policies."""

def get_purged_dataset_statuses(dataset_keys: Sequence[str]) -> dict[str, bool]:
    """Plural verification of whether datasets have been permanently purged."""
```

### 2. Upstream Dependencies & The `IamClient` Rule

- `fusion_auth.client.IamClient`:
  - `resolve_session(auth_token, cookies)` -> resolves active caller's identity and active role.
  - `get_users(user_ids: Sequence[int])` -> plural directory resolution of integer `user_id`s.
- `modules.directory.contracts`:
  - Plural employee and student directory resolution.

#### Strict Step 3.6 Compliance & IAM Boundary
**Zero new methods are added to `IamClient` or `FakeIam`.** All requirements from the SRS involving IAM-native state:
- User account creation, credentials, password reset, 2FA (`UC-SA-001`, `UC-SA-003`, `UC-SA-006`, `UC-SA-033`)
- Designation catalog definition, role assignments, time-bound tracking (`UC-SA-008..012`, `UC-SA-028..030`)
- Active role switching (`UC-SA-013`)
- Account deactivation/reactivation (`UC-SA-004`, `UC-SA-005`)

are native duties of `Fusion_System_Administrator` (IAM). They are documented below as formal IAM boundaries in Step 3.8(h) and are not duplicated as local auth tables in `fusion_integrated`.

---

## Step 3.7 (g) — Scheduled Work

Scheduled periodic tasks defined in `modules/superadmin/schedule.py` and registered in `config/celery.py`:

```python
BEAT_SCHEDULE = {
    "superadmin-expire-reversibility-window": {
        "task": "modules.superadmin.tasks.expire_reversibility_window_task",
        "schedule": 86400.0,  # Daily at midnight UTC
    },
    "superadmin-expire-purge-requests": {
        "task": "modules.superadmin.tasks.expire_pending_purge_requests_task",
        "schedule": 21600.0,  # Every 6 hours
    },
    "superadmin-drain-notification-outbox": {
        "task": "modules.superadmin.tasks.drain_notification_outbox_task",
        "schedule": 120.0,    # Every 2 minutes
    },
}

TASK_ROUTES = {
    "modules.superadmin.tasks.*": {"queue": "superadmin"},
}
```

### Operational Consequences of Scheduler Failure
1. **`expire_reversibility_window_task`:**
   - *Cadence:* Daily.
   - *Real-world impact if down:* Archived accounts whose 30-day reversible window has lapsed will remain in `reversible` status instead of transitioning to `finalized_permanent` (violating `ISS-SA-004`). Ineligible users could be erroneously restored after their legal window expired.
2. **`expire_pending_purge_requests_task`:**
   - *Cadence:* Every 6 hours.
   - *Real-world impact if down:* Stale dual-auth purge authorization tokens will remain actionable indefinitely, creating a severe security risk where an old approval request could be executed months later without refreshed authorization.
3. **`drain_notification_outbox_task`:**
   - *Cadence:* Every 2 minutes.
   - *Real-world impact if down:* Administrative notifications (archival alerts, purge dual-auth requests, security alerts) will accumulate in the outbox table and fail to be dispatched to recipients.

---

## Step 3.8 (h) — Open Questions & Known Gaps

The following architectural questions and known gaps are formally documented for administrative sign-off:

1. **Production ERP Designation Provisioning (`globals_designation`):**
   - *Issue:* The institute ERP database (`fusionlab` / `fusion-dev.dump`) currently does not contain the designations `"super_admin"` or `"it_head"` verbatim.
   - *Development Resolution:* Both roles are provisioned locally in development using `Fusion_System_Administrator`'s management command:
     `python manage.py assign_role --user <username> --designation "super_admin"`
     `python manage.py assign_role --user <username> --designation "it_head"`
   - *Open Item for Production:* The Registrar / Academic Office must formally create the designations `"super_admin"` and `"it_head"` in `globals_designation` in the production ERP.
2. **Effective-Dated Seed Policy Sign-Off:**
   - *Default Reversibility Window (ISS-SA-004 / UC-SA-015):* 30 calendar days.
   - *Purge Dual-Auth Approval TTL:* 72 hours.
   - *Bulk Operation Batch Size Limit (BR-SA-030):* 1,000 records.
   - *Open Item:* Confirmation from the institute IT Committee on these default parameters before initial database migration seeding.
3. **External IAM Boundaries & Known Gaps Inventory:**
   In compliance with ADR-0002 and Step 3.6, the following requirements from the SRS are native responsibilities of the IAM service (`Fusion_System_Administrator`) running on `fusion_system_db` and are not implemented inside `modules/superadmin/` in `Fusion-Integrated`:
   - `UC-SA-001`, `UC-SA-003`, `UC-SA-006`: Native user account lifecycle, credential generation, and bulk user import in `Fusion_System_Administrator/Backend/backend/api/views/users.py`.
   - `UC-SA-004`, `UC-SA-005`: Account deactivation/reactivation in `Fusion_System_Administrator`.
   - `UC-SA-008` to `UC-SA-012`, `UC-SA-028` to `UC-SA-030`: Role definition catalog, designation assignment, time-bound tracking, and role handover in `Fusion_System_Administrator/Backend/backend/api/views/roles.py`.
   - `UC-SA-013`: Active role switching in the `Fusion-client` shell communicating with `/api/iam/v1/me`.
   - `UC-SA-033`, `UC-SA-034`: Super Admin session establishment, 2FA, and inactivity timeouts in `Fusion_System_Administrator/Backend/backend/iam/views/auth.py`.
   - `BR-SA-001` to `BR-SA-003`, `BR-SA-006` to `BR-SA-016`, `BR-SA-027`, `BR-SA-028`, `BR-SA-031`, `BR-SA-034`: IAM-native state and enforcement.
