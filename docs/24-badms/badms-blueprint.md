# Backup and Database Archive Management System (BADMS) — Module Blueprint (Revised)

**Module Code:** `badms`  
**Documentation Folder:** `docs/24-badms/`  
**Environment:** `module-only`  
**Specification Folder:** `/Users/trupesha/Desktop/drive-download-20261101T110138Z-1-001`  

This document constitutes the deliverable for Phase 2 of the BADMS module build, strictly following `docs/08-delivery/new-module-prompt.md` §3 and incorporating all required review revisions.

## Step 3.1 (a) — Traceability Table

One row per live Business Rule (`BR-BA-*`), Use Case (`BA-UC-*`), Workflow (`BW-BA-*`, `CW-BA-*`), Composite Functional Requirement (`CFR-BA-*`), and Atomic Functional Requirement (`AFR-BA-*`). Note that `AFR-BA-044` and `AFR-BA-050` do not exist in the specification registry (no retired IDs exist in the specification set).


| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| `BR-BA-001` | **Manual Backup Trigger Authorization**: Only a SysAdmin or Super Admin may trigger a manual backup. | `api / services` | Permission `badms.backup.manage`, service `trigger_manual_backup` | SysAdmin/Super Admin authorization |
| `BR-BA-002` | **Respective HoD Approval for Secure Archival**: A secure archival request may be decided only by the HoD of the requester's department. | `selectors / services` | Permission `badms.archival.approve`, service `decide_archival_request` | Scoped to requester department HoD |
| `BR-BA-003` | **IT Security Encryption Authority**: Only authorized IT Security Team members may configure encryption for Sensitive data. | `api / services` | Permission `badms.security.manage`, service `configure_sensitive_encryption` | IT Security authorization |
| `BR-BA-004` | **SysAdmin Authoritative Classification**: The authoritative secure-archival classification (Critical, Sensitive, Routine, Archival) is assigned by an authorized SysAdmin after HoD approval. | `selectors / services` | Permission `badms.archival.review`, service `classify_archival_request` | SysAdmin authoritative classification review |
| `BR-BA-005` | **Sensitive Restoration Approval**: Restoration of data classified Sensitive requires SysAdmin approval before restoration proceeds. | `selectors / services` | Permission `badms.restoration.approve`, service `approve_sensitive_restoration` | SysAdmin approval required for Sensitive data restoration |
| `BR-BA-006` | **Initial Data Classification and Default**: Uploaded data must carry an initial classification; if the user omits it, BADMS assigns Routine as the default. | `domain / services` | `domain/state_machine.py`, `services/archival.py::submit_archival_request` | Default Routine if omitted at upload |
| `BR-BA-007` | **Sensitive Data Encryption**: Data classified Sensitive must be encrypted using AES-256 both at rest and in transit. | `domain / services` | `domain/crypto.py`, `services/archival.py::configure_sensitive_encryption` | AES-256-GCM encryption at rest and in transit |
| `BR-BA-008` | **Retention by Classification**: Data must be retained according to institute-defined retention policy, with the applicable retention rules selected according to data classification. | `domain / models` | `domain/retention.py`, `RetentionPolicy` model, `services/archival.py` | Retention rules bound to authoritative classification; duration values configured by policy |
| `BR-BA-009` | **HoD Approval for Storage Extension**: A storage-extension request requires HoD approval. | `selectors / services` | Permission `badms.storage.approve`, service `decide_storage_extension` | HoD decision required; no generic admin |
| `BR-BA-010` | **HoD Department Scope**: A HoD may act only on requests and reports belonging to the HoD's own department. | `selectors / services` | `selectors/scoping.py::scope_for_user`, HoD department match filter | Department scope restriction (404 on cross-department) |
| `BR-BA-011` | **Local Schedule Overrides Global**: A valid local schedule for a dataset overrides the institution-wide global schedule; otherwise the global schedule applies. | `domain / services` | `domain/schedules.py::resolve_effective_schedule`, `services/backups.py` | Local schedule overrides global policy for dataset |
| `BR-BA-012` | **Schedule Parameter Validation**: A new or modified backup schedule must pass parameter and conflict validation before it is applied. | `domain / services` | `domain/schedules.py::validate_schedule_params`, `services/schedules.py` | Rejects conflicting / invalid parameters, cron syntax |
| `BR-BA-013` | **Scheduled Repository Reachability**: A scheduled automatic backup executes successfully only when the relevant scheduled repository is reachable. | `services / tasks` | `services/backups.py::execute_scheduled_backup` repository health check | Fails if repository endpoint unreachable |
| `BR-BA-014` | **Backup Failure Alert SLA**: When a backup is Failed, BADMS must alert the SysAdmin within five minutes. | `services / tasks` | `services/notifications.py::send_backup_failure_alert`, Celery beat | Alert SysAdmin within 5 minutes of failure |
| `BR-BA-015` | **Repeated Failure Escalation**: When three consecutive backup failures occur, BADMS must escalate the condition to the Director of IT. | `services / tasks` | `services/backups.py`, `services/notifications.py` | Escalate to Director of IT on 3 consecutive failures (test fixtures isolate fallback) |
| `BR-BA-016` | **Storage-Extension Usage Validation**: A storage-extension request must be validated against the user's current storage usage. | `domain / services` | `domain/storage.py`, `services/storage.py::submit_storage_extension` | Validation against current quota and usage |
| `BR-BA-017` | **Storage-Extension Decision Criteria**: The HoD reviews available storage infrastructure, departmental policies, and the user's justification when deciding a storage-extension request. | `selectors / services` | `services/storage.py::decide_storage_extension` | HoD evaluates infrastructure, policy, justification |
| `BR-BA-018` | **Special Archival Super Admin Authority**: A special archival request may originate offline from any authority, but only the Super Admin may perform the corresponding special archival operation within BADMS. | `api / services` | Permission `badms.archival.manage`, service `perform_special_archival` | Super Admin exclusive authority for special archival |
| `BR-BA-019` | **Super Admin Global Backup Authority**: Only the Super Admin holds the stated highest authority to define institution-wide global backup schedules and default backup policies. | `api / services` | Permission `badms.backup_policy.manage`, service `define_global_backup_schedule` | Super Admin authority for global backup policy |
| `BR-BA-020` | **Protected Information Access Scope**: Audit logs, request status, backup status, and reports shall be shown only to actors authorized for the requested scope; HoD access is limited to the HoD's department. | `selectors / api` | `selectors/scoping.py`, object-level ownership / dept filters | Protected information visibility scoping (returns 404) |
| `BR-BA-021` | **IT Security Security/RBAC Authority**: Only authorized IT Security Team members may manage RBAC permissions and configure/enforce security policies assigned to the IT Security role. | `IAM Platform / core` | IAM `Fusion_System_Administrator` central RBAC administration | RBAC is owned exclusively by IAM; BADMS delegates RBAC to IAM |
| `BA-UC-001` | **Trigger Manual Backup**: Create a point-in-time backup of the current platform/database state on demand. | `api / services` | POST `/api/v1/badms/backups/manual/`, `services/backups.py` | Trigger manual backup |
| `BA-UC-002` | **Submit Secure Archival Request**: Submit data and required metadata for secure archival. | `api / services` | POST `/api/v1/badms/archival-requests/`, `services/archival.py` | Submit secure archival request |
| `BA-UC-003` | **Decide Secure Archival Request**: Approve or reject a secure archival request from the HoD's own department. | `api / services` | POST `/api/v1/badms/archival-requests/{id}/decide/`, `services/archival.py` | Decide secure archival request (HoD) |
| `BA-UC-004` | **Classify Secure Archival Data**: Assign the authoritative classification that determines security and retention treatment for an approved secure-archival request. | `api / services` | POST `/api/v1/badms/archival-requests/{id}/classify/`, `services/archival.py` | Classify secure archival data (SysAdmin) |
| `BA-UC-005` | **Configure Sensitive-Data Encryption**: Configure required encryption and create an encrypted archive for Sensitive data. | `api / services` | POST `/api/v1/badms/archival-requests/{id}/configure-encryption/`, `services/archival.py` | Configure sensitive encryption (IT Security) |
| `BA-UC-006` | **Execute Scheduled Automatic Backup**: Execute the backup defined by the effective schedule without user intervention. | `tasks / services` | Celery beat task `evaluate_and_dispatch_due_backups`, `services/backups.py` | Execute scheduled automatic backup at arbitrary configured times |
| `BA-UC-007` | **Submit Storage-Extension Request**: Request additional storage when the user's quota is full. | `api / services` | POST `/api/v1/badms/storage-extensions/`, `services/storage.py` | Submit storage extension request |
| `BA-UC-008` | **Decide Storage-Extension Request**: Approve or reject a storage-extension request for the HoD's department. | `api / services` | POST `/api/v1/badms/storage-extensions/{id}/decide/`, `services/storage.py` | Decide storage extension request (HoD) |
| `BA-UC-009` | **Configure Local Backup Schedule**: Create or update dataset-specific/local automated backup schedules. | `api / services` | POST/PUT `/api/v1/badms/schedules/local/`, `services/schedules.py` | Configure local backup schedule (SysAdmin) |
| `BA-UC-010` | **Perform Special Archival Operation**: Perform and record special archival for extended storage of Sensitive research data after receiving an offline request from any authority. | `api / services` | POST `/api/v1/badms/archival-requests/special/`, `services/archival.py` | Perform special archival operation (Super Admin) |
| `BA-UC-011` | **Define Global Backup Schedules and Defaults**: Set institution-wide global backup schedules and default backup policies. | `api / services` | POST/PUT `/api/v1/badms/schedules/global/`, `services/schedules.py` | Define global backup schedules/defaults (Super Admin) |
| `BA-UC-012` | **View Audit Logs and Activity History**: Review audit logs and activity histories for operational monitoring. | `api / selectors` | GET `/api/v1/badms/audit-logs/`, `selectors/audit.py` | View audit logs and activity history (SysAdmin) |
| `BA-UC-013` | **Audit Data Activity and Review Security Reports**: Inspect activity/security records to detect unauthorized access and review security-related reports. | `api / selectors` | GET `/api/v1/badms/audit-logs/security/`, `selectors/audit.py` | Audit data activity & security reports (IT Security) |
| `BA-UC-014` | **View Backup History and Status**: View current backup status and backup history visible to the actor. | `api / selectors` | GET `/api/v1/badms/backups/`, `selectors/backups.py` | View backup history and status (Scoped) |
| `BA-UC-015` | **Track Request Status**: Track archival, storage-extension, and restoration request status and history. | `api / selectors` | GET `/api/v1/badms/archival-requests/`, `selectors/archival.py` | Track archival request status (User/Scoped) |
| `BA-UC-016` | **Request Data Restoration**: Request restoration of archived data. | `api / services` | POST `/api/v1/badms/restorations/`, `services/restoration.py` | Request data restoration (User/Scoped) |
| `BA-UC-017` | **Approve Sensitive Data Restoration**: Approve or reject restoration of data classified Sensitive. | `api / services` | POST `/api/v1/badms/restorations/{id}/approve/`, `services/restoration.py` | Approve sensitive restoration (SysAdmin) |
| `BA-UC-018` | **Execute Data Restoration**: Technically restore archived data after all required approvals/standard checks are satisfied. | `api / services` | POST `/api/v1/badms/restorations/{id}/execute/`, `services/restoration.py` | Execute data restoration (SysAdmin) |
| `BA-UC-019` | **Manage RBAC Permissions**: Manage user permissions through role-based access control. | `IAM Platform` | Central IAM Administration Console (`Fusion_System_Administrator`) | Fulfilled through central IAM administration; BADMS publishes permissions manifest without local RBAC tables |
| `BA-UC-020` | **Define and Enforce Security Policies**: Configure institution security policies governing encryption, access, and related security controls. | `api / services` | POST/PUT `/api/v1/badms/security-policies/`, `services/security_policies.py` | Define/enforce security policies (IT Security) |
| `BA-UC-021` | **View Department Data-Management Reports**: View operational reports relevant to the HoD's own department. | `api / selectors` | GET `/api/v1/badms/reports/department/`, `selectors/reports.py` | View department reports (HoD department scoped) |
| `BA-UC-022` | **Monitor Storage Thresholds**: Monitor user storage usage against applicable storage thresholds and maintain the threshold/full-quota condition used by storage management. | `tasks / services` | Celery beat task `monitor_storage_thresholds`, `services/storage.py` | Monitor storage thresholds against authoritative quota balances |
| `BA-UC-023` | **Record Audit Event**: Persist the required audit record whenever an auditable user, administrative, system, or security event occurs. | `services / models` | `services/audit.py::record_audit_event`, `AuditEvent` model | Record structured audit events |
| `BW-BA-01` | **Secure Archival - HoD Rejection**: Represent the finite path in which a user submits a secure archival request and the respective HoD rejects it. | `domain / services` | `domain/state_machine.py`, `services/archival.py::decide_archival_request` | HoD rejection terminal path |
| `BW-BA-02` | **Secure Archival - Approved, Non-Sensitive Classification**: Represent the approved path that reaches an authoritative non-Sensitive classification. | `domain / services` | `domain/state_machine.py`, `services/archival.py::classify_archival_request` | Approved, non-sensitive classification path |
| `BW-BA-03` | **Secure Archival - Approved, Sensitive Encryption**: Represent the approved Sensitive path through HoD review, SysAdmin classification, and IT Security encryption/archive creation. | `domain / services` | `domain/state_machine.py`, `services/archival.py::configure_sensitive_encryption` | Approved, sensitive encryption path |
| `BW-BA-04` | **Storage Extension - Rejected**: Represent a storage-extension request rejected by the respective HoD. | `domain / services` | `domain/state_machine.py`, `services/storage.py::decide_storage_extension` | Storage extension HoD rejection path |
| `BW-BA-05` | **Storage Extension - Approved**: Represent a storage-extension request approved by the respective HoD, ending in the recorded Approved state for this version. | `domain / services` | `domain/state_machine.py`, `services/storage.py::decide_storage_extension` | Storage extension HoD approval path |
| `BW-BA-06` | **Restoration - Non-Sensitive Standard Path**: Represent the standard non-Sensitive restoration path supported by the PS. | `domain / services` | `domain/state_machine.py`, `services/restoration.py::execute_restoration` | Non-sensitive standard restoration execution path |
| `BW-BA-07` | **Restoration - Sensitive SysAdmin Approval**: Represent the explicit PS rule that Sensitive restoration requires SysAdmin approval before technical restoration. | `domain / services` | `domain/state_machine.py`, `services/restoration.py::approve_restoration` | Sensitive restoration SysAdmin approval path |
| `CW-BA-01` | **Secure Archival Request Processing**: Integrate the materially different secure-archival outcomes: rejection, approved non-Sensitive classification, and approved Sensitive encryption/archive creation. | `domain / services` | `domain/state_machine.py::ARCHIVAL_TRANSITIONS`, `services/archival.py` | Composite secure archival request processing |
| `CW-BA-02` | **Storage-Extension Request Processing**: Integrate the approved and rejected storage-extension paths. | `domain / services` | `domain/state_machine.py::STORAGE_EXTENSION_TRANSITIONS`, `services/storage.py` | Composite storage extension request processing |
| `CW-BA-03` | **Data Restoration Processing**: Combine non-Sensitive and Sensitive restoration paths using the current-version SysAdmin approval path for Sensitive data. | `domain / services` | `domain/state_machine.py::RESTORATION_TRANSITIONS`, `services/restoration.py` | Composite data restoration processing |
| `CFR-BA-001` | **Manual Backup Management**: BADMS shall allow only authorized SysAdmin or Super Admin personnel to execute an on-demand backup, capture and store the current database state with timestamped outcome information, and handle backup failure notification. | `api / services / tasks` | `services/backups.py::trigger_manual_backup` | Manual backup trigger and status recording |
| `CFR-BA-002` | **Scheduled Automatic Backup Execution**: BADMS shall execute automatic backups at the effective scheduled time without user intervention, select eligible datasets, transfer them to recovery storage, verify integrity/consistency, record the outcome, and require the scheduled repository to be reachable. | `tasks / services` | `tasks.py::evaluate_and_dispatch_due_backups` | Automatic scheduled backup execution with integrity & reachability checks |
| `CFR-BA-003` | **Local Backup Schedule Management**: BADMS shall allow an authorized SysAdmin to view, create, and modify local/dataset backup schedules, validate schedule parameters/conflicts, apply only valid configurations, and log schedule changes. | `api / services / domain` | `services/schedules.py`, `domain/schedules.py` | Local backup schedule management and validation |
| `CFR-BA-004` | **Backup Status and History Visibility**: BADMS shall maintain backup status/history and allow users and authorized administrators to view the backup history and current status within their authorized scope. | `api / selectors` | `selectors/backups.py::list_backups` | Backup status and history visibility |
| `CFR-BA-005` | **Secure Archival Submission and Intake**: BADMS shall allow an authenticated user to submit a secure archival request with required metadata and initial classification, validate the submission and quota, default missing initial classification to Routine, set a successful request to Submitted, and route it to the requester's HoD. | `api / services / models` | `services/archival.py::submit_archival_request` | Secure archival submission and intake validation |
| `CFR-BA-006` | **Secure Archival HoD Review and Routing**: BADMS shall allow only the HoD of the requester's department to review and approve/reject a submitted secure archival request, record the decision, and route an approved request to SysAdmin for authoritative classification. | `api / services / selectors` | `services/archival.py::decide_archival_request` | HoD review, routing, and decision |
| `CFR-BA-007` | **Authoritative Archival Classification and Policy Routing**: BADMS shall allow SysAdmin to assign the authoritative archival classification, apply the corresponding security treatment, and route Sensitive requests to IT Security for encryption configuration. | `api / services` | `services/archival.py::classify_archival_request` | Authoritative archival classification and policy routing |
| `CFR-BA-008` | **Sensitive Data Encryption and Archive Creation**: BADMS shall allow IT Security to configure encryption for Sensitive data and shall create the encrypted archive using AES-256 at rest and in transit while recording the outcome. | `api / domain / services` | `domain/crypto.py`, `services/archival.py` | Sensitive data encryption configuration and creation |
| `CFR-BA-009` | **Secure Archival Tracking and Notifications**: BADMS shall allow users to track secure-archival request status/history and shall issue submission and decision notifications at the relevant stages. | `api / selectors` | `selectors/archival.py::get_archival_status` | Secure archival tracking and notification emission |
| `CFR-BA-010` | **Special Archival Operation**: When any authority makes a special archival request offline, BADMS shall allow only the Super Admin to perform the corresponding special archival operation for Sensitive research data and shall record its outcome and audit event. | `api / services` | `services/archival.py::perform_special_archival` | Special archival operation (Super Admin) |
| `CFR-BA-011` | **Data Restoration Management**: BADMS shall allow users to request and track archived-data restoration, require SysAdmin approval before Sensitive restoration, and support technical restoration through the standard path for non-Sensitive data and the approved path for Sensitive data. | `api / services / domain` | `services/restoration.py`, `domain/state_machine.py` | Data restoration management and approval |
| `CFR-BA-012` | **Storage Extension Request and Decision**: When storage quota is full, BADMS shall allow a user to submit a storage-extension request, validate current usage and infrastructure sufficiency, route the valid request to the user's HoD, and allow the HoD to review the stated decision criteria and record approval/rejection. | `api / services / selectors` | `services/storage.py`, `selectors/scoping.py` | Storage extension request and decision workflow |
| `CFR-BA-013` | **Storage Threshold Monitoring**: BADMS shall monitor user storage thresholds and maintain the threshold/full-quota condition needed to support storage-management decisions. | `tasks / services` | `tasks.py::monitor_storage_thresholds` | Storage threshold monitoring and status tracking |
| `CFR-BA-014` | **Global Backup Schedules and Defaults**: BADMS shall allow only the Super Admin to define institution-wide global backup schedules/default backup policies, apply the global schedule where no valid local override exists, and honor local-schedule precedence. | `api / services / domain` | `services/schedules.py`, `domain/schedules.py` | Global backup schedules and default policies |
| `CFR-BA-015` | **Retention by Data Classification**: BADMS shall enforce institute-defined retention rules according to the authoritative data classification without requiring classification-specific duration values in this version. | `domain / models` | `domain/retention.py`, `models/retention.py` | Retention duration and treatment by classification (no invented durations) |
| `CFR-BA-016` | **Backup Failure Notification and Escalation**: BADMS shall alert SysAdmin within five minutes when a backup fails, escalate after three consecutive failures to the Director of IT, and issue the required backup status/completion notifications. | `services / tasks` | `services/notifications.py`, `tasks.py` | Backup failure notification SLA and escalation to Director of IT |
| `CFR-BA-017` | **Storage-Extension Notifications**: BADMS shall notify the requester when a storage-extension request is submitted and when the HoD records approval or rejection. | `services / selectors` | `services/storage.py`, `services/notifications.py` | Storage extension notifications and intake routing |
| `CFR-BA-018` | **Audit Logging and Operational Reporting**: BADMS shall record audit events with required identifiers/outcomes and provide role-scoped audit, security, backup, and departmental operational visibility to authorized SysAdmin, IT Security, HoD, and other permitted administrators. | `services / selectors / models` | `models/audit.py`, `services/audit.py`, `selectors/audit.py` | Audit logging and operational reporting |
| `CFR-BA-019` | **RBAC, Security Policy, and Role Separation**: BADMS shall allow IT Security to manage RBAC and security policies while enforcing departmental scope and separation of HoD, SysAdmin, Super Admin, and IT Security responsibilities. | `registry / IAM / selectors` | `registry.py::ROLE_GRANTS`, IAM manifest, `selectors/scoping.py` | RBAC, security policy, and role separation without duplicate auth tables |
| `AFR-BA-001` | The system shall allow only a SysAdmin or Super Admin to trigger a manual backup. | `services / api` | `services/backups.py`, POST `/api/v1/badms/backups/manual/` | Manual backup execution and logging |
| `AFR-BA-002` | When a manual backup is triggered, the system shall collect the current timestamp and required backup artifacts. | `services / api` | `services/backups.py`, POST `/api/v1/badms/backups/manual/` | Manual backup execution and logging |
| `AFR-BA-003` | The system shall communicate with the database and save a current-state dump together with its timestamp. | `services / api` | `services/backups.py`, POST `/api/v1/badms/backups/manual/` | Manual backup execution and logging |
| `AFR-BA-004` | The system shall record and communicate the outcome of each backup as Success or Failure. | `services / api` | `services/backups.py`, POST `/api/v1/badms/backups/manual/` | Manual backup execution and logging |
| `AFR-BA-005` | If a backup cannot be created, the system shall mark the backup as Failed and alert the SysAdmin. | `services / api` | `services/backups.py`, POST `/api/v1/badms/backups/manual/` | Manual backup execution and logging |
| `AFR-BA-006` | The system shall perform automatic backups at scheduled times without requiring user intervention. | `tasks / services` | `tasks.py::evaluate_and_dispatch_due_backups`, `services/backups.py` | Automatic scheduled backup execution |
| `AFR-BA-007` | For an automatic backup, the system shall identify and read the datasets eligible under the applicable schedule. | `tasks / services` | `tasks.py::evaluate_and_dispatch_due_backups`, `services/backups.py` | Automatic scheduled backup execution |
| `AFR-BA-008` | The system shall transfer eligible data to backup recovery storage during an automatic backup. | `tasks / services` | `tasks.py::evaluate_and_dispatch_due_backups`, `services/backups.py` | Automatic scheduled backup execution |
| `AFR-BA-009` | The system shall verify backup integrity and consistency during automatic backup execution. | `tasks / services` | `tasks.py::evaluate_and_dispatch_due_backups`, `services/backups.py` | Automatic scheduled backup execution |
| `AFR-BA-010` | The system shall log the verified automatic backup with its timestamp and status. | `tasks / services` | `tasks.py::evaluate_and_dispatch_due_backups`, `services/backups.py` | Automatic scheduled backup execution |
| `AFR-BA-011` | The system shall execute a scheduled automatic backup only when the relevant repository is scheduled and reachable. | `tasks / services` | `tasks.py::evaluate_and_dispatch_due_backups`, `services/backups.py` | Automatic scheduled backup execution |
| `AFR-BA-012` | The system shall display the current backup schedules to an authorized SysAdmin. | `api / services / domain` | `services/schedules.py`, `domain/schedules.py` | Backup schedule configuration & validation |
| `AFR-BA-013` | The system shall allow a SysAdmin to create or modify a local backup schedule by specifying frequency, execution time, and data-classification filters. | `api / services / domain` | `services/schedules.py`, `domain/schedules.py` | Backup schedule configuration & validation |
| `AFR-BA-014` | The system shall validate schedule parameters and reject conflicting or otherwise invalid schedule configurations without applying them. | `api / services / domain` | `services/schedules.py`, `domain/schedules.py` | Backup schedule configuration & validation |
| `AFR-BA-015` | After successful validation, the system shall apply the new or updated local backup schedule. | `api / services / domain` | `services/schedules.py`, `domain/schedules.py` | Backup schedule configuration & validation |
| `AFR-BA-016` | The system shall log each backup-schedule configuration change. | `api / services / domain` | `services/schedules.py`, `domain/schedules.py` | Backup schedule configuration & validation |
| `AFR-BA-017` | The system shall maintain the current status and history of all backup operations. | `api / selectors` | `selectors/backups.py`, GET `/api/v1/badms/backups/` | Backup history and status tracking |
| `AFR-BA-018` | The system shall allow users and authorized administrators to view backup history and current backup status. | `api / selectors` | `selectors/backups.py`, GET `/api/v1/badms/backups/` | Backup history and status tracking |
| `AFR-BA-019` | The system shall allow an authenticated user to initiate a secure archival request. | `api / services / models` | `services/archival.py`, POST `/api/v1/badms/archival-requests/` | Secure archival submission and HoD routing |
| `AFR-BA-020` | A secure archival request shall capture file name, date, owners, file type, reason for secure archival, and the file attachment. | `api / services / models` | `services/archival.py`, POST `/api/v1/badms/archival-requests/` | Secure archival submission and HoD routing |
| `AFR-BA-021` | Before accepting a secure archival request, the system shall validate the entered information and storage quota; on validation failure it shall show errors and make no request-state change. | `api / services / models` | `services/archival.py`, POST `/api/v1/badms/archival-requests/` | Secure archival submission and HoD routing |
| `AFR-BA-022` | On successful submission, the system shall set the secure archival request status to Submitted. | `api / services / models` | `services/archival.py`, POST `/api/v1/badms/archival-requests/` | Secure archival submission and HoD routing |
| `AFR-BA-023` | The system shall route a submitted secure archival request to the HoD of the requester's department for review. | `api / services / models` | `services/archival.py`, POST `/api/v1/badms/archival-requests/` | Secure archival submission and HoD routing |
| `AFR-BA-024` | The system shall allow the routed HoD to review the request details, attachments, and policy context before deciding a secure archival request. | `api / services / selectors` | `services/archival.py::decide_archival_request` | HoD review and decision |
| `AFR-BA-025` | The system shall allow the HoD to approve or reject a secure archival request and shall record the decision. | `api / services / selectors` | `services/archival.py::decide_archival_request` | HoD review and decision |
| `AFR-BA-026` | Only the HoD of the requester's department shall be permitted to approve or reject that user's secure archival request. | `api / services / selectors` | `services/archival.py::decide_archival_request` | HoD review and decision |
| `AFR-BA-027` | After HoD approval, the system shall route the secure archival request to the SysAdmin for classification. | `api / services / selectors` | `services/archival.py::decide_archival_request` | HoD review and decision |
| `AFR-BA-028` | The system shall allow the SysAdmin to review an approved secure archival request and classify the data as Critical, Sensitive, Routine, or Archival. | `api / services` | `services/archival.py::classify_archival_request` | SysAdmin authoritative data classification review |
| `AFR-BA-029` | A user shall provide an initial classification for uploaded data; if no classification is supplied, the system shall assign Routine as the default classification. | `api / services / models` | `services/archival.py`, POST `/api/v1/badms/archival-requests/` | Secure archival submission and HoD routing |
| `AFR-BA-030` | The system shall apply security and retention rules according to the authoritative data classification. | `api / services` | `services/archival.py::classify_archival_request` | SysAdmin authoritative data classification review |
| `AFR-BA-031` | If the authoritative classification is Sensitive, the system shall route the request to the IT Security Team for encryption configuration. | `api / services` | `services/archival.py::classify_archival_request` | SysAdmin authoritative data classification review |
| `AFR-BA-032` | The system shall allow the IT Security Team to configure encryption for data classified as Sensitive. | `domain / services` | `domain/crypto.py`, `services/archival.py::configure_sensitive_encryption` | Sensitive data encryption configuration |
| `AFR-BA-033` | After encryption is configured for Sensitive data, the system shall create the encrypted archive and record the outcome. | `domain / services` | `domain/crypto.py`, `services/archival.py::configure_sensitive_encryption` | Sensitive data encryption configuration |
| `AFR-BA-034` | Data classified as Sensitive shall use AES-256 encryption both at rest and in transit. | `domain / services` | `domain/crypto.py`, `services/archival.py::configure_sensitive_encryption` | Sensitive data encryption configuration |
| `AFR-BA-035` | The system shall allow a user to track the status and history of a secure archival request throughout processing. | `api / selectors` | `selectors/archival.py`, `services/notifications.py` | Archival request status tracking and notifications |
| `AFR-BA-036` | The system shall send a submission confirmation and decision notifications for secure archival requests at relevant approval/rejection stages. | `api / selectors` | `selectors/archival.py`, `services/notifications.py` | Archival request status tracking and notifications |
| `AFR-BA-037` | The system shall allow the Super Admin to perform a special archival operation for extended storage of Sensitive research data when a request has been received offline from any authority. | `api / services` | `services/archival.py::perform_special_archival` | Special archival operation (Super Admin) |
| `AFR-BA-038` | Only the Super Admin shall be permitted to perform the special archival operation in BADMS. | `api / services` | `services/archival.py::perform_special_archival` | Special archival operation (Super Admin) |
| `AFR-BA-039` | After the Super Admin performs a special archival operation, the system shall record the operation outcome and corresponding audit event. | `api / services` | `services/archival.py::perform_special_archival` | Special archival operation (Super Admin) |
| `AFR-BA-040` | The system shall allow a user to request restoration of archived data. | `api / services / domain` | `services/restoration.py`, `domain/state_machine.py` | Data restoration request, approval, and execution |
| `AFR-BA-041` | A restoration request for data classified as Sensitive shall require SysAdmin approval before restoration proceeds. | `api / services / domain` | `services/restoration.py`, `domain/state_machine.py` | Data restoration request, approval, and execution |
| `AFR-BA-042` | The system shall support restoration of non-Sensitive archived data through the standard restoration procedure. | `api / services / domain` | `services/restoration.py`, `domain/state_machine.py` | Data restoration request, approval, and execution |
| `AFR-BA-043` | The system shall allow a user to track restoration-request status. | `api / services / domain` | `services/restoration.py`, `domain/state_machine.py` | Data restoration request, approval, and execution |
| `AFR-BA-045` | When the user's storage quota is full, the system shall allow the user to submit a storage-extension request. | `api / services / selectors` | `services/storage.py`, `selectors/scoping.py` | Storage extension submission and HoD decision |
| `AFR-BA-046` | The system shall validate a storage-extension request against the user's current storage usage. | `api / services / selectors` | `services/storage.py`, `selectors/scoping.py` | Storage extension submission and HoD decision |
| `AFR-BA-047` | The system shall route a valid storage-extension request to the user's HoD for review. | `api / services / selectors` | `services/storage.py`, `selectors/scoping.py` | Storage extension submission and HoD decision |
| `AFR-BA-048` | The system shall allow the HoD to review storage-extension request details, attachments, available storage infrastructure, departmental policy, and the user's justification. | `api / services / selectors` | `services/storage.py`, `selectors/scoping.py` | Storage extension submission and HoD decision |
| `AFR-BA-049` | The system shall allow the HoD to approve or reject a storage-extension request and shall record the decision. | `api / services / selectors` | `services/storage.py`, `selectors/scoping.py` | Storage extension submission and HoD decision |
| `AFR-BA-051` | The system shall monitor storage thresholds for all users. | `tasks / services` | `tasks.py::monitor_storage_thresholds` | Storage threshold monitoring and condition tracking |
| `AFR-BA-052` | The system shall validate requested storage against available infrastructure and shall detect when a requested extension exceeds available storage. | `api / services / selectors` | `services/storage.py`, `selectors/scoping.py` | Storage extension submission and HoD decision |
| `AFR-BA-053` | The system shall allow the Super Admin to define institution-wide global backup schedules and default backup policies. | `api / services / domain` | `services/schedules.py`, `domain/schedules.py` | Global backup schedules and default policy |
| `AFR-BA-054` | The system shall apply the global schedule to all relevant systems or datasets when no valid local override exists. | `api / services / domain` | `services/schedules.py`, `domain/schedules.py` | Global backup schedules and default policy |
| `AFR-BA-055` | A local backup schedule for a specific dataset shall override the institution-wide global schedule for that dataset. | `api / services / domain` | `services/schedules.py`, `domain/schedules.py` | Global backup schedules and default policy |
| `AFR-BA-056` | The system shall enforce institute-defined retention rules according to data classification. | `domain / models` | `domain/retention.py`, `models/retention.py` | Retention rules and treatment by classification (policy-governed) |
| `AFR-BA-057` | When a backup is marked Failed, the system shall send an alert to the SysAdmin within five minutes. | `services / tasks` | `services/notifications.py`, `services/backups.py` | Backup failure alert SLA and escalation |
| `AFR-BA-058` | The system shall escalate to the Director of IT when three consecutive backup failures occur. | `services / tasks` | `services/notifications.py`, `services/backups.py` | Backup failure alert SLA and escalation |
| `AFR-BA-059` | The system shall issue backup creation-status and completion notifications, including failure alerts to the SysAdmin. | `services / tasks` | `services/notifications.py`, `services/backups.py` | Backup failure alert SLA and escalation |
| `AFR-BA-060` | The system shall notify the requester when a storage-extension request is submitted and when the HoD approves or rejects it. | `services / selectors` | `services/notifications.py`, `services/storage.py` | Storage extension notification and tracking |
| `AFR-BA-061` | The system shall maintain audit logs for user actions, administrative actions, system events, and security events, including timestamps, actor identifiers, actions, and outcomes. | `models / services / selectors` | `models/audit.py`, `services/audit.py`, `selectors/audit.py` | Audit logging, activity review, and reports |
| `AFR-BA-062` | The system shall allow a SysAdmin to view audit logs and activity histories. | `models / services / selectors` | `models/audit.py`, `services/audit.py`, `selectors/audit.py` | Audit logging, activity review, and reports |
| `AFR-BA-063` | The system shall allow the IT Security Team to audit data-activity logs for unauthorized access and review security-related reports. | `models / services / selectors` | `models/audit.py`, `services/audit.py`, `selectors/audit.py` | Audit logging, activity review, and reports |
| `AFR-BA-064` | The system shall allow a HoD to view operational reports relevant to the HoD's own department. | `models / services / selectors` | `models/audit.py`, `services/audit.py`, `selectors/audit.py` | Audit logging, activity review, and reports |
| `AFR-BA-065` | The system shall provide operational visibility into backup operations to support monitoring and compliance verification. | `models / services / selectors` | `models/audit.py`, `services/audit.py`, `selectors/audit.py` | Audit logging, activity review, and reports |
| `AFR-BA-066` | The system shall allow the IT Security Team to manage user permissions through role-based access control (RBAC). | `registry / IAM / selectors` | `registry.py::ROLE_GRANTS`, IAM manifest, `selectors/scoping.py` | RBAC, role separation, and policy enforcement via IAM |
| `AFR-BA-067` | The system shall allow the IT Security Team to define and enforce security policies governing encryption, access, and security controls. | `registry / IAM / selectors` | `registry.py::ROLE_GRANTS`, IAM manifest, `selectors/scoping.py` | RBAC, role separation, and policy enforcement via IAM |
| `AFR-BA-068` | The system shall enforce role separation and departmental scope restrictions so that HoDs act only on requests from their departments and technical/security responsibilities remain assigned to the authorized roles. | `registry / IAM / selectors` | `registry.py::ROLE_GRANTS`, IAM manifest, `selectors/scoping.py` | RBAC, role separation, and policy enforcement via IAM |

## Step 3.2 (b) — Domain Model

Entities, fields, invariants, and database-level constraints. Every table uses `TimeStampedModel` from `core.db.mixins`. No cross-module foreign keys exist (`ops/checks/no_cross_module_fk.py`); all user references are plain integer `user_id` (`UserScopedModel`).

### 1. `BackupRecord` (`badms_backup_record`)
Records every manual, scheduled, and automatic backup run.
- `id`: BigAutoField (PK)
- `backup_type`: CharField(max_length=20, choices=[`manual`, `scheduled`])
- `dataset_name`: CharField(max_length=100) (e.g., `fusion_integrated`, `fusionlab_dump`)
- `status`: CharField(max_length=20, choices=[`pending`, `running`, `success`, `failure`])
- `started_at`: DateTimeField
- `completed_at`: DateTimeField(null=True, blank=True)
- `file_path`: CharField(max_length=500, blank=True)
- `file_size_bytes`: BigIntegerField(default=0)
- `checksum_sha256`: CharField(max_length=64, blank=True)
- `error_message`: TextField(blank=True)
- `triggered_by_user_id`: IntegerField(null=True, blank=True) (null for automatic/Celery)
- `consecutive_failure_count`: IntegerField(default=0)
- **Database Constraints:**
  - `CheckConstraint(check=Q(backup_type__in=['manual', 'scheduled']), name='chk_badms_backup_type')`
  - `CheckConstraint(check=Q(status__in=['pending', 'running', 'success', 'failure']), name='chk_badms_backup_status')`
  - `Index(fields=['status', '-created_at'], name='idx_badms_bkup_status_created')`
  - `Index(fields=['dataset_name', '-created_at'], name='idx_badms_bkup_ds_created')`

### 2. `BackupSchedule` (`badms_backup_schedule`)
Represents local or global backup schedules.
- `id`: BigAutoField (PK)
- `name`: CharField(max_length=150)
- `scope_type`: CharField(max_length=20, choices=[`global`, `local`])
- `dataset_name`: CharField(max_length=100)
- `cron_expression`: CharField(max_length=100) (e.g. `0 2 * * *`, `15 3 * * *`, `*/30 * * * *`)
- `data_classification_filter`: CharField(max_length=30, blank=True) (e.g. `Critical,Sensitive`)
- `is_active`: BooleanField(default=True)
- `created_by_user_id`: IntegerField()
- `version`: IntegerField(default=1)
- `effective_from`: DateTimeField()
- `effective_to`: DateTimeField(null=True, blank=True)
- `last_run_at`: DateTimeField(null=True, blank=True)
- `next_run_at`: DateTimeField(null=True, blank=True)
- **Database Constraints:**
  - `UniqueConstraint(fields=['dataset_name', 'scope_type', 'is_active'], condition=Q(is_active=True), name='uniq_badms_active_schedule_per_dataset')`
  - `CheckConstraint(check=Q(scope_type__in=['global', 'local']), name='chk_badms_sched_scope')`
  - `Index(fields=['is_active', 'next_run_at'], name='idx_badms_sched_active_next')`

### 3. `ArchivalRequest` (`badms_archival_request`)
Secure archival intake, HoD review, SysAdmin classification, and IT Security encryption.
- `id`: BigAutoField (PK)
- `requester_user_id`: IntegerField()
- `department`: CharField(max_length=100) (from requester IAM profile)
- `file_name`: CharField(max_length=255)
- `file_type`: CharField(max_length=50)
- `file_size_bytes`: BigIntegerField()
- `reason`: TextField()
- `file_storage_path`: CharField(max_length=500)
- `initial_classification`: CharField(max_length=20, default='Routine', choices=[`Routine`, `Sensitive`, `Critical`, `Archival`])
- `authoritative_classification`: CharField(max_length=20, null=True, blank=True, choices=[`Routine`, `Sensitive`, `Critical`, `Archival`])
- `status`: CharField(max_length=40, default='submitted', choices=[
    `submitted`, `rejected`, `hod_approved`, `classified_non_sensitive`,
    `classified_sensitive`, `sensitive_archive_encrypted`, `special_archived`
  ])
- `hod_reviewed_by_user_id`: IntegerField(null=True, blank=True)
- `hod_decision_at`: DateTimeField(null=True, blank=True)
- `hod_remarks`: TextField(blank=True)
- `sysadmin_classified_by_user_id`: IntegerField(null=True, blank=True)
- `classified_at`: DateTimeField(null=True, blank=True)
- `encryption_algorithm`: CharField(max_length=50, blank=True) (e.g. `AES-256-GCM`)
- `is_encrypted`: BooleanField(default=False)
- `encrypted_by_user_id`: IntegerField(null=True, blank=True)
- `encrypted_at`: DateTimeField(null=True, blank=True)
- `is_special_archival`: BooleanField(default=False)
- `retention_policy_ref`: CharField(max_length=100, blank=True) (dynamic link to institute-defined classification policy, no hardcoded years)
- **Database Constraints:**
  - `CheckConstraint(check=Q(status__in=['submitted', 'rejected', 'hod_approved', 'classified_non_sensitive', 'classified_sensitive', 'sensitive_archive_encrypted', 'special_archived']), name='chk_badms_arch_status')`
  - `Index(fields=['department', 'status'], name='idx_badms_arch_dept_status')`
  - `Index(fields=['requester_user_id', '-created_at'], name='idx_badms_arch_req_created')`

### 4. `UserStorageQuota` (`badms_user_storage_quota`)
Authoritative institute storage quota balances and usage ledgers per user.
- `id`: BigAutoField (PK)
- `user_id`: IntegerField(unique=True)
- `allocated_quota_bytes`: BigIntegerField(default=10737418240) (**Proposed 10 GB baseline, explicitly pending institute policy approval**; default value configurable via SecurityPolicy once approved by approver)
- `used_storage_bytes`: BigIntegerField(default=0)
- `is_full`: BooleanField(default=False)
- `last_calculated_at`: DateTimeField(auto_now=True)
- **Database Constraints:**
  - `CheckConstraint(check=Q(allocated_quota_bytes__gte=0), name='chk_badms_quota_alloc_pos')`
  - `CheckConstraint(check=Q(used_storage_bytes__gte=0), name='chk_badms_quota_used_pos')`
  - `Index(fields=['is_full'], name='idx_badms_quota_is_full')`

### 5. `StorageExtensionRequest` (`badms_storage_extension_request`)
Storage quota extension request and departmental HoD decision.
- `id`: BigAutoField (PK)
- `requester_user_id`: IntegerField()
- `department`: CharField(max_length=100)
- `current_usage_bytes`: BigIntegerField() (snapshot at request time)
- `current_quota_bytes`: BigIntegerField() (snapshot at request time)
- `requested_extension_bytes`: BigIntegerField()
- `justification`: TextField()
- `status`: CharField(max_length=20, default='submitted', choices=[`submitted`, `approved`, `rejected`])
- `hod_reviewed_by_user_id`: IntegerField(null=True, blank=True)
- `hod_decision_at`: DateTimeField(null=True, blank=True)
- `hod_remarks`: TextField(blank=True)
- **Database Constraints:**
  - `CheckConstraint(check=Q(status__in=['submitted', 'approved', 'rejected']), name='chk_badms_storext_status')`
  - `CheckConstraint(check=Q(requested_extension_bytes__gt=0), name='chk_badms_storext_req_pos')`
  - `Index(fields=['department', 'status'], name='idx_badms_storext_dept_st')`
  - `Index(fields=['requester_user_id', '-created_at'], name='idx_badms_storext_user_cr')`

### 6. `RestorationRequest` (`badms_restoration_request`)
Data restoration workflow for non-sensitive and sensitive archived datasets.
- `id`: BigAutoField (PK)
- `requester_user_id`: IntegerField()
- `department`: CharField(max_length=100)
- `archival_request_id`: BigIntegerField() (ID of dataset/archive)
- `classification`: CharField(max_length=20, choices=[`Routine`, `Sensitive`, `Critical`, `Archival`])
- `target_destination`: CharField(max_length=255)
- `status`: CharField(max_length=40, default='requested_standard', choices=[
    `requested_standard`, `sensitive_pending_approval`, `approved`, `rejected`, `restored`
  ])
- `approved_by_user_id`: IntegerField(null=True, blank=True)
- `approved_at`: DateTimeField(null=True, blank=True)
- `executed_by_user_id`: IntegerField(null=True, blank=True)
- `restored_at`: DateTimeField(null=True, blank=True)
- `error_message`: TextField(blank=True)
- **Database Constraints:**
  - `CheckConstraint(check=Q(status__in=['requested_standard', 'sensitive_pending_approval', 'approved', 'rejected', 'restored']), name='chk_badms_rest_status')`
  - `Index(fields=['status', '-created_at'], name='idx_badms_rest_st_cr')`

### 7. `AuditEvent` (`badms_audit_event`)
Append-only structured audit trail recording all BADMS security, operational, and administrative actions.
- `id`: BigAutoField (PK)
- `event_type`: CharField(max_length=60)
- `actor_user_id`: IntegerField()
- `actor_role`: CharField(max_length=50)
- `target_model`: CharField(max_length=50)
- `target_id`: BigIntegerField(null=True, blank=True)
- `department`: CharField(max_length=100, blank=True)
- `details`: JSONField(default=dict)
- `ip_address`: GenericIPAddressField(null=True, blank=True)
- `timestamp`: DateTimeField(auto_now_add=True)
- **Database Invariant / Constraint:**
  - Append-only: updates and deletes are forbidden at model and service level.
  - `Index(fields=['event_type', '-timestamp'], name='idx_badms_audit_type_time')`
  - `Index(fields=['actor_user_id', '-timestamp'], name='idx_badms_audit_actor_time')`
  - `Index(fields=['department', '-timestamp'], name='idx_badms_audit_dept_time')`

### 8. `SecurityPolicy` (`badms_security_policy`)
Effective-dated, append-only security policy configured by IT Security.
- `id`: BigAutoField (PK)
- `policy_key`: CharField(max_length=100) (e.g., `encryption_algorithm`, `retention_schedule`, `session_timeout_seconds`, `mfa_required`)
- `policy_value`: JSONField()
- `configured_by_user_id`: IntegerField()
- `effective_from`: DateTimeField()
- `effective_to`: DateTimeField(null=True, blank=True)
- `is_active`: BooleanField(default=True)
- **Database Constraints:**
  - `UniqueConstraint(fields=['policy_key', 'is_active'], condition=Q(is_active=True), name='uniq_badms_active_security_policy')`

## Step 3.3 (c) — State Machine

Declarative transition tables defined as pure Python data structures in `domain/state_machine.py`. Any transition not explicitly listed in the table is inexpressible and rejected with a domain error.

### 1. Secure Archival Workflow (`CW-BA-01`, `BW-BA-01`, `BW-BA-02`, `BW-BA-03`)
```python
ARCHIVAL_TRANSITIONS = {
    # (source_state, event, actor_role) -> (target_state, guard_fn)
    ("none", "submit", "user"): ("submitted", None),
    ("submitted", "reject", "hod"): ("rejected", "guard_hod_department_match"),
    ("submitted", "approve", "hod"): ("hod_approved", "guard_hod_department_match"),
    ("hod_approved", "classify_non_sensitive", "sysadmin"): ("classified_non_sensitive", "guard_classification_is_non_sensitive"),
    ("hod_approved", "classify_sensitive", "sysadmin"): ("classified_sensitive", "guard_classification_is_sensitive"),
    ("classified_sensitive", "encrypt_and_create", "it_security"): ("sensitive_archive_encrypted", "guard_aes_256_configured"),
    ("none", "special_archive", "super_admin"): ("special_archived", None),
}
```

### 2. Storage Extension Workflow (`CW-BA-02`, `BW-BA-04`, `BW-BA-05`)
```python
STORAGE_EXTENSION_TRANSITIONS = {
    # (source_state, event, actor_role) -> (target_state, guard_fn)
    ("none", "submit", "user"): ("submitted", "guard_storage_quota_full"),
    ("submitted", "reject", "hod"): ("rejected", "guard_hod_department_match"),
    ("submitted", "approve", "hod"): ("approved", "guard_hod_department_match"),
}
```

### 3. Data Restoration Workflow (`CW-BA-03`, `BW-BA-06`, `BW-BA-07`)
```python
RESTORATION_TRANSITIONS = {
    # (source_state, event, actor_role) -> (target_state, guard_fn)
    ("none", "request_non_sensitive", "user"): ("requested_standard", "guard_dataset_non_sensitive"),
    ("none", "request_sensitive", "user"): ("sensitive_pending_approval", "guard_dataset_sensitive"),
    ("sensitive_pending_approval", "reject", "sysadmin"): ("rejected", None),
    ("sensitive_pending_approval", "approve", "sysadmin"): ("approved", None),
    ("requested_standard", "execute", "sysadmin"): ("restored", "guard_destination_reachable"),
    ("approved", "execute", "sysadmin"): ("restored", "guard_destination_reachable"),
}
```

## Step 3.4 (d) — Permission List

The complete `registry.py` configuration. Verbs adhere strictly to the closed vocabulary in `docs/02-iam/rbac-model.md` (`view`, `create`, `update`, `delete`, `approve`, `publish`, `review`, `assign`, `revoke`, `export`, `import`, `restore`, `manage`). `classify` has been replaced with `review`, and `special` has been replaced with `manage`.

```python
MODULE = {
    "code": "badms",
    "name": "Backup and Database Archive Management System",
    "description": "Enterprise database backup schedules, secure archival intake, HoD review, SysAdmin classification, and restoration management.",
    "version": "1.0.0",
}

PERMISSIONS = [
    # Backups
    ("badms.backup.view", "View backup status, history, and schedules"),
    ("badms.backup.manage", "Trigger manual backups and configure local schedules"),
    ("badms.backup_policy.manage", "Define global backup schedules and default policies"),
    
    # Archival Requests
    ("badms.archival.view", "View secure archival requests and status"),
    ("badms.archival.create", "Submit secure archival requests"),
    ("badms.archival.approve", "Approve or reject archival requests within department"),
    ("badms.archival.review", "Review and assign authoritative data classification"),
    ("badms.archival.manage", "Execute special archival operations"),
    
    # Storage Extension
    ("badms.storage.view", "View storage extension requests and quota status"),
    ("badms.storage.create", "Submit storage extension requests"),
    ("badms.storage.approve", "Approve or reject storage extension requests within department"),
    
    # Restoration
    ("badms.restoration.view", "View data restoration requests and history"),
    ("badms.restoration.create", "Submit data restoration requests"),
    ("badms.restoration.approve", "Approve or reject sensitive data restoration requests"),
    ("badms.restoration.restore", "Execute technical data restoration"),
    
    # Security, Audits, & Reports
    ("badms.security.manage", "Configure encryption for sensitive archives and security policies"),
    ("badms.audit.view", "View system audit logs and data activity history"),
    ("badms.report.view", "View department data management and operational reports"),
]

SYSTEM_PERMISSIONS = [
    "badms.backup.auto_execute",
    "badms.storage.auto_monitor",
    "badms.failure.auto_escalate",
]

SCOPE_PERMISSIONS = []

# Baseline Kind Grants (Held by definition, no ERP designation needed)
_STUDENT = [
    "badms.archival.view",
    "badms.archival.create",
    "badms.storage.view",
    "badms.storage.create",
    "badms.restoration.view",
    "badms.restoration.create",
]

_FACULTY = _STUDENT
_STAFF = _STUDENT

# Department Head Grants (Mapped to catalogued office designations)
_HOD = [
    "badms.backup.view",
    "badms.archival.view",
    "badms.archival.create",
    "badms.archival.approve",
    "badms.storage.view",
    "badms.storage.create",
    "badms.storage.approve",
    "badms.restoration.view",
    "badms.restoration.create",
    "badms.report.view",
]

# System Administrator Grants (Catalogued office designation acadadmin / system role)
_SYSADMIN = [
    "badms.backup.view",
    "badms.backup.manage",
    "badms.archival.view",
    "badms.archival.review",
    "badms.storage.view",
    "badms.restoration.view",
    "badms.restoration.approve",
    "badms.restoration.restore",
    "badms.audit.view",
    "badms.report.view",
]

# Super Admin Grants (Catalogued highest office designation Director / Super Admin)
_SUPER_ADMIN = [
    "badms.backup.view",
    "badms.backup.manage",
    "badms.backup_policy.manage",
    "badms.archival.view",
    "badms.archival.manage",
    "badms.storage.view",
    "badms.restoration.view",
    "badms.audit.view",
    "badms.report.view",
]

# IT Security Grants
_IT_SECURITY = [
    "badms.archival.view",
    "badms.security.manage",
    "badms.audit.view",
    "badms.report.view",
]

# Real Designation Keys matching globals_designation and IAM Role Catalogue
ROLE_GRANTS = {
    # Basic kinds
    "student": _STUDENT,
    "faculty": _FACULTY,
    "staff": _STAFF,
    
    # Department Heads (Catalogued in IAM rbac.py)
    "HOD (CSE)": _HOD,
    "HOD (ECE)": _HOD,
    "HOD (ME)": _HOD,
    "HOD (Design)": _HOD,
    "HOD (NS)": _HOD,
    "HOD (Liberal Arts)": _HOD,
    "HOD": _HOD,  # Generic academic designation
    
    # System Administration
    "acadadmin": _SYSADMIN,
    "SysAdmin": _SYSADMIN,
    
    # Institution Leadership / Super Admin
    "Director": _SUPER_ADMIN,
    "Super Admin": _SUPER_ADMIN,
    
    # IT Security
    "IT Security": _IT_SECURITY,
}
```

## Step 3.5 (e) — Endpoint List

All endpoints are mounted under `/api/v1/badms/`. Every endpoint sits behind two gates: `HasModuleAccess('badms')` followed by `HasPermission('<permission_code>')`. Read scoping yields `404 Not Found` when accessing unauthorized rows.

| Method | Path | Required Permission | Description & Enforced Rule IDs | Returns |
|---|---|---|---|---|
| `POST` | `/api/v1/badms/backups/manual/` | `badms.backup.manage` | Trigger manual backup (`BR-BA-001`, `AFR-BA-001`..`005`, `BA-UC-001`) | `201 Created` (`BackupRecordSerializer`) |
| `GET` | `/api/v1/badms/backups/` | `badms.backup.view` | Scoped list of backup operations (`BR-BA-020`, `AFR-BA-017`..`018`, `BA-UC-014`) | `200 OK` (Paginated `BackupRecordSerializer`) |
| `GET` | `/api/v1/badms/backups/{id}/` | `badms.backup.view` | Scoped detail of backup operation (`BR-BA-020`, `AFR-BA-017`) | `200 OK` / `404` (`BackupRecordSerializer`) |
| `GET` | `/api/v1/badms/schedules/` | `badms.backup.view` | List active backup schedules (`AFR-BA-012`, `BA-UC-009`) | `200 OK` (`BackupScheduleSerializer`) |
| `POST` | `/api/v1/badms/schedules/local/` | `badms.backup.manage` | Create local backup schedule (`BR-BA-011`, `BR-BA-012`, `AFR-BA-013`..`016`) | `201 Created` (`BackupScheduleSerializer`) |
| `PUT` | `/api/v1/badms/schedules/local/{id}/` | `badms.backup.manage` | Update local backup schedule (`BR-BA-012`, `AFR-BA-015`) | `200 OK` (`BackupScheduleSerializer`) |
| `POST` | `/api/v1/badms/schedules/global/` | `badms.backup_policy.manage` | Define global backup schedule (`BR-BA-019`, `AFR-BA-053`..`055`, `BA-UC-011`) | `201 Created` (`BackupScheduleSerializer`) |
| `POST` | `/api/v1/badms/archival-requests/` | `badms.archival.create` | Submit secure archival request (`BR-BA-006`, `AFR-BA-019`..`023`, `BA-UC-002`) | `201 Created` (`ArchivalRequestSerializer`) |
| `GET` | `/api/v1/badms/archival-requests/` | `badms.archival.view` | Scoped list of archival requests (`BR-BA-020`, `AFR-BA-035`, `BA-UC-015`) | `200 OK` (Paginated `ArchivalRequestSerializer`) |
| `GET` | `/api/v1/badms/archival-requests/{id}/` | `badms.archival.view` | Scoped detail of archival request (`BR-BA-020`, `AFR-BA-035`) | `200 OK` / `404` (`ArchivalRequestSerializer`) |
| `POST` | `/api/v1/badms/archival-requests/{id}/decide/` | `badms.archival.approve` | HoD approve/reject archival request (`BR-BA-002`, `BR-BA-010`, `AFR-BA-024`..`027`) | `200 OK` (`ArchivalRequestSerializer`) |
| `POST` | `/api/v1/badms/archival-requests/{id}/classify/` | `badms.archival.review` | SysAdmin classify data (`BR-BA-004`, `BR-BA-008`, `AFR-BA-028`, `030`, `031`) | `200 OK` (`ArchivalRequestSerializer`) |
| `POST` | `/api/v1/badms/archival-requests/{id}/configure-encryption/` | `badms.security.manage` | IT Security configure encryption (`BR-BA-003`, `BR-BA-007`, `AFR-BA-032`..`034`) | `200 OK` (`ArchivalRequestSerializer`) |
| `POST` | `/api/v1/badms/archival-requests/special/` | `badms.archival.manage` | Super Admin special archival (`BR-BA-018`, `AFR-BA-037`..`039`, `BA-UC-010`) | `201 Created` (`ArchivalRequestSerializer`) |
| `POST` | `/api/v1/badms/storage-extensions/` | `badms.storage.create` | Submit storage extension (`BR-BA-016`, `AFR-BA-045`..`047`, `BA-UC-007`) | `201 Created` (`StorageExtensionSerializer`) |
| `GET` | `/api/v1/badms/storage-extensions/` | `badms.storage.view` | Scoped list of storage extensions (`BR-BA-020`, `AFR-BA-045`) | `200 OK` (Paginated `StorageExtensionSerializer`) |
| `POST` | `/api/v1/badms/storage-extensions/{id}/decide/` | `badms.storage.approve` | HoD approve/reject extension (`BR-BA-009`, `BR-BA-010`, `BR-BA-017`, `AFR-BA-048`..`049`) | `200 OK` (`StorageExtensionSerializer`) |
| `POST` | `/api/v1/badms/restorations/` | `badms.restoration.create` | Submit restoration request (`AFR-BA-040`, `BA-UC-016`) | `201 Created` (`RestorationRequestSerializer`) |
| `GET` | `/api/v1/badms/restorations/` | `badms.restoration.view` | Scoped list of restoration requests (`BR-BA-020`, `AFR-BA-040`) | `200 OK` (Paginated `RestorationRequestSerializer`) |
| `POST` | `/api/v1/badms/restorations/{id}/approve/` | `badms.restoration.approve` | SysAdmin approve sensitive restoration (`BR-BA-005`, `AFR-BA-041`, `BA-UC-017`) | `200 OK` (`RestorationRequestSerializer`) |
| `POST` | `/api/v1/badms/restorations/{id}/execute/` | `badms.restoration.restore` | SysAdmin execute data restoration (`AFR-BA-042`, `BA-UC-018`) | `200 OK` (`RestorationRequestSerializer`) |
| `GET` | `/api/v1/badms/audit-logs/` | `badms.audit.view` | Scoped view of audit events (`BR-BA-020`, `AFR-BA-061`..`063`, `BA-UC-012`, `013`) | `200 OK` (Paginated `AuditEventSerializer`) |
| `GET` | `/api/v1/badms/reports/department/` | `badms.report.view` | Scoped department operational report (`BR-BA-010`, `AFR-BA-064`..`065`, `BA-UC-021`) | `200 OK` (`DepartmentReportSerializer`) |
| `GET` | `/api/v1/badms/security-policies/` | `badms.security.manage` | List effective security policies (`BR-BA-021`, `AFR-BA-067`, `BA-UC-020`) | `200 OK` (`SecurityPolicySerializer`) |
| `POST` | `/api/v1/badms/security-policies/` | `badms.security.manage` | Create/update security policy (`BR-BA-021`, `AFR-BA-067`, `BA-UC-020`) | `201 Created` (`SecurityPolicySerializer`) |

### Client Routes and Guards (`client/src/modules/badms/routes.tsx`)
In accordance with `ops/checks/nav_matches_routes.py`, every client route has a corresponding nav item. Detail views open in drawers/modals on their respective list pages.
- `/badms/backups` — guarded by `badms.backup.view`.
- `/badms/schedules` — guarded by `badms.backup.view`.
- `/badms/archival-requests` — guarded by `badms.archival.view`.
- `/badms/storage-extensions` — guarded by `badms.storage.view`.
- `/badms/restorations` — guarded by `badms.restoration.view`.
- `/badms/audit-logs` — guarded by `badms.audit.view`.
- `/badms/reports` — guarded by `badms.report.view`.
- `/badms/security-policies` — guarded by `badms.security.manage`.

### Fusion-client Sidebar Entry
Ready-to-paste `Fusion-client` sidebar navigation definition:
```json
{
  "id": "badms",
  "label": "Backup & Database Archive Management System",
  "icon": "Database",
  "to": "/badms/backups",
  "section": "Administration"
}
```


### Fusion-client Integration Entry (`INTEGRATED_MODULES`)
For `Fusion-client/src/ui/nav/navigation.js` when running in `full-platform`:
```javascript
{
  id: 'badms',
  label: 'Backup & Archival',
  icon: 'Database',
  to: '/badms',
  section: 'Administration',
}
```

## Step 3.6 (f) — Contracts

Inter-module contracts exposed by `modules/badms/contracts.py`. All contract getters are **strictly plural** (`get_x(ids: Sequence[int])`) as mandated by `ops/checks/contracts_are_plural.py`.

```python
from typing import Sequence, Dict, Any

def get_backup_statuses(backup_ids: Sequence[int]) -> Dict[int, Dict[str, Any]]:
    """Return status and metadata for a sequence of backup record IDs."""
    ...

def get_archival_statuses(request_ids: Sequence[int]) -> Dict[int, Dict[str, Any]]:
    """Return archival request status, classification, and encryption status."""
    ...

def get_user_storage_quotas(user_ids: Sequence[int]) -> Dict[int, Dict[str, Any]]:
    """Return authoritative storage usage, allocated quota limit, and full-quota flag for users.
    
    Reads from UserStorageQuota. If a user record does not exist yet, initializes the baseline
    institute quota allocation (10 GB) and zero usage on demand, ensuring consistent plural lookup
    for all valid user IDs without depending on prior storage-extension requests.
    """
    ...
```

### Dependencies on IAM / External Modules
In accordance with ADR 0002 and `shared-kernel-reference.md`, BADMS never connects to `fusionlab` directly:
- User profile & department: retrieved via `iam_client.get_users(user_ids)`.
- Department HoD determination: retrieved via `iam_client.get_users` (checking designation `HOD` and department match).
- Active principal session: validated via session middleware.

## Step 3.7 (g) — Scheduled Work

Celery beat tasks registered in `modules/badms/schedule.py` and merged into `config/celery.py`:

| Task Name | Cadence | Purpose & Enforced Rules | Real-World Impact if Not Running |
|---|---|---|---|
| `badms.tasks.evaluate_and_dispatch_due_backups` | Every minute (`* * * * *`) | Evaluates all active local and global backup schedules (`BR-BA-011`, `BR-BA-012`, `BR-BA-013`, `AFR-BA-006`..`011`, `BA-UC-006`). **Scheduler Catch-Up & De-duplication Protocol:** In normal operation, evaluates `croniter` against `last_run_at` and current time. If scheduler downtime or delayed execution occurs (`now > next_run_at`), it executes exactly one immediate catch-up backup for the elapsed window, updates `last_run_at = now`, and recalculates `next_run_at` to the next future scheduled occurrence. Concurrency locking (`select_for_update` on the schedule record) guarantees no duplicate backup execution occurs. Strictly verifies repository reachability before backup and validates post-dump SHA-256 checksum integrity. | Automated backups fail to trigger or recover after scheduler downtime; institute data is not backed up according to policy. |
| `badms.tasks.monitor_storage_thresholds` | Every 6 hours (`0 */6 * * *`) | Evaluates user storage balances against allocated quotas and updates the authoritative `is_full` condition (`AFR-BA-051`, `BA-UC-022`). | Storage exhaustion goes undetected; users cannot submit valid storage extensions. |
| `badms.tasks.check_backup_failure_sla` | Every 1 minute (`* * * * *`) | Safety reconciliation poller complementing the **immediate event-driven failure alert**. When any backup fails in `services/backups.py`, `services/notifications.py::send_backup_failure_alert` is dispatched immediately in-band to notify the SysAdmin within seconds (meeting the 5-minute SLA of `BR-BA-014` regardless of task boundary timing). This Celery task runs every 1 minute as a safety net to catch any unnotified failed backups (`failed_at >= now - 5m` with `alert_sent=False`) and triggers escalation to Director of IT upon 3 consecutive failures (`BR-BA-015`, `AFR-BA-057`..`059`). | SysAdmin and IT leadership remain unaware of backup failures, violating institute disaster-recovery SLA. |
| `badms.tasks.purge_expired_archives` | Daily at 03:00 (`0 3 * * *`) | Evaluates archives against authorized institute retention policy (`BR-BA-008`, `AFR-BA-056`). **Safety & Policy Guard:** Does not perform unauthorized automatic physical file deletion. Archives exceeding retention duration are transitioned to status `retention_expired` and placed on an authorized purge review list; actual physical deletion executes only after explicit administrative authorization or when authorized automated purge is explicitly enabled by institute policy in `SecurityPolicy`. | Storage fills indefinitely with unreviewed stale archives, or unreviewed data could be prematurely lost without policy governance. |

## Step 3.8 (h) — Open Questions & Architectural Clarifications

1. **Resolution of BR-BA-015 Escalation Designation (IAM Verification Evidence):**
   - *Verification Evidence:* Strict codebase inspection of the central IAM service (`Fusion_System_Administrator/Backend/backend/iam/rbac.py::CATALOGUE` and `globals_designation`) reveals that:
     - The designation `Director` exists in the IAM catalogue (`("Director", "Director", IamRole.OFFICE, FACULTY_ONLY)`).
     - The string `Director of IT` **does not exist** anywhere in the IAM catalogue or existing ERP database fixtures.
     - `Director` and `Director of IT` are **not interchangeable**: `Director` is the head of the institute (faculty office), whereas `Director of IT` is the specific functional administrative officer specified in `BR-BA-015`.
   - *Resolution:*
     - BADMS routes escalation notifications to the exact role named in `BR-BA-015`: `Director of IT`.
     - In development and testing fixtures (`module-only`), `Director of IT` is provisioned via `manage.py assign_role` in `Fusion_System_Administrator`, or isolated to mock notification handlers in test fixtures.
     - For production deployment, adding `Director of IT` to the institute's ERP designation list is an external administrative requirement.

2. **Resolution of BA-UC-019 (Central IAM Administration):**
   - *Requirement:* `BA-UC-019` specifies managing user permissions through role-based access control.
   - *Platform Architecture Rule:* Per ADR 0002, `new-module-prompt.md` §3 Step 3.4, and `docs/02-iam/rbac-model.md`, RBAC is owned exclusively by the central IAM service (`Fusion_System_Administrator`). Modules must never create duplicate `Role`, `Permission`, `UserRole`, or `ModuleAccess` tables in `fusion_integrated`.
   - *Fulfillment:* BADMS fulfills `BA-UC-019` through the central IAM platform:
     - BADMS declares all its module permissions and role grants in `modules/badms/registry.py`.
     - Manifest generation (`make permissions`) compiles `registry/permissions.json`.
     - Seeding into IAM (`manage.py seed_iam_permissions`) populates `RolePermission` and `IamDesignationModule` in the IAM database.
     - Central IAM administrative endpoints and management commands manage user role assignments.
     - BADMS creates zero duplicate auth tables in its business schema.

3. **Authoritative Source of User Storage Quota & Proposed Baseline Allocation:**
   - *Resolution:* BADMS establishes `UserStorageQuota` as the dedicated aggregate for user quota balances and usage ledgers.
   - Contract getter `get_user_storage_quotas(user_ids)` queries this model directly. Quota tracking is completely decoupled from whether a user has ever submitted a `StorageExtensionRequest`.
   - **Status of 10 GB Baseline:** The 10 GB baseline is a proposed developer default and is **explicitly pending approval by the approver**. It is not an approved institute policy and will not be treated as a fixed specification requirement. The default allocation is configurable via `SecurityPolicy` once approved.

4. **Classification-Based Retention Policy (BR-BA-008, AFR-BA-056):**
   - *Resolution:* Removed the hardcoded `retention_years = 5`. BADMS models retention dynamically via `SecurityPolicy` (policy key `retention_schedule`) configured by institute policy makers, with retention rules selected strictly according to authoritative data classification (`Critical`, `Sensitive`, `Routine`, `Archival`).
   - Expired archives are marked for review/purge under policy governance and never deleted automatically without explicit policy authorization.

5. **Arbitrary Schedule Precision & Downtime Catch-Up (BR-BA-011, AFR-BA-006):**
   - *Resolution:* Scheduled backup evaluation cadence is configured to run every minute (`* * * * *`).
   - The task evaluates `cron_expression` against `last_run_at` and current time, guaranteeing that arbitrary valid configured times (e.g. `02:15`, `03:45`, `*/15 * * * *`) are dispatched on time while strictly enforcing repository reachability and post-dump SHA-256 integrity verification.
   - Concurrency locking and single catch-up execution prevent duplicate runs and handle scheduler recovery after downtime.

6. **Immediate Backup Failure Alert SLA (BR-BA-014):**
   - *Resolution:* When a backup fails, the failure notification is dispatched immediately in-band from `services/backups.py` via `services/notifications.py`, meeting the 5-minute alert SLA in seconds rather than relying on periodic Celery task boundary timing. A 1-minute Celery poller acts as an operational safety net.

7. **RBAC Permission Verbs Compliance:**
   - *Resolution:* All permission verbs comply with the closed vocabulary in `docs/02-iam/rbac-model.md`. `badms.archival.review`, `badms.archival.manage`, and `badms.restoration.restore` are used across all endpoints and declarations.

---

### Remaining Approval Decisions for Approver Sign-Off:
1. **Designation Provisioning in Dev Environment:**
   - Confirm provisioning of `"HOD"`, `"SysAdmin"`, `"Super Admin"`, `"IT Security"`, and `"Director of IT"` in `globals_designation` using `Fusion_System_Administrator`'s `manage.py assign_role`.
2. **Default Baseline Storage Quota Value:**
   - Formal sign-off on the proposed default baseline quota value (e.g., 10 GB) or specification of the institute's preferred default for uninitialized users.
3. **Automated vs. Manual Purge for Retention-Expired Archives:**
   - Confirm whether retention-expired archives should default to requiring manual administrative purge authorization, or whether automated deletion may be enabled via `SecurityPolicy`.
