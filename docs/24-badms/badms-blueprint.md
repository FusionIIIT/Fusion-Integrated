# BADMS Module Blueprint
**Module Name**: Backup, Archival and Data Management System (BADMS)  
**Module Code**: `badms`  
**Docs Identifier**: `24-badms`  
**Lead Builder (Student 1)**: Adepu Srinidh (`24BCS010`)  
**Reviewer & Spec Tester (Student 2)**: Ansh Prajapati (`24BCS029`)  
**Specification Baseline**: Problem Statement v1.2, CFR/AFR Registry v1.1, UCs v1.2, BRs v1.2, Workflows v1.1  
**Status**: APPROVED by Student 2  

---

## 1. Executive Summary & Scope

BADMS delivers institutional data protection, automated database backup scheduling, department-scoped secure archival pipelines, storage extension request governance, and controlled data restoration workflows for the Fusion ERP platform.

### Core Objectives
1. **Automated & Manual Backups**: Support full database and selective dataset dumps with automated rotation and backup failure alerting.
2. **Secure Multi-Stage Archival**: Enforce department-scoped HoD approvals, SysAdmin data classification (`Routine` vs `Sensitive`), IT Security AES-256 encryption, and 10–15 year retention constraints.
3. **Storage Extension Governance**: Permit quota extension requests strictly when storage usage reaches &ge; 80%, routed to departmental HoDs with automatic quota updates upon approval.
4. **Governed Restoration**: Instant direct execution for standard archives; mandatory SysAdmin authorization for sensitive archives before restoration execution.

---

## 2. Specification ID Traceability Matrix

### 2.1 Business Rules Traceability (`BR-BA-001` through `BR-BA-021`)
| Rule ID | Name / Summary | Architectural Enforcement Point |
|:---|:---|:---|
| `BR-BA-001` | SysAdmin Backup Authority | `domain.rules.validate_backup_initiation_role` |
| `BR-BA-002` | HoD Department Scoping | `domain.rules.validate_hod_department_scope` |
| `BR-BA-003` | IT Security Sensitive Encryption | `domain.rules.validate_encryption_dispatch` |
| `BR-BA-004` | SysAdmin Archival Classification | `domain.rules.validate_classification_role` |
| `BR-BA-005` | SysAdmin Restoration Approval | `domain.rules.validate_restoration_execution_authorization` |
| `BR-BA-006` | Default Routine Classification | `domain.workflows.ArchivalWorkflowEngine` |
| `BR-BA-007` | AES-256 Encryption Standard | `domain.rules.validate_encryption_algorithm` |
| `BR-BA-008` | 10–15 Year Retention Minimum | `domain.rules.calculate_retention_policy` |
| `BR-BA-009` | HoD Storage Extension Authority | `domain.rules.validate_hod_extension_scope` |
| `BR-BA-010` | Cross-Department Approval Ban | `services.badms_services.decide_secure_archival_hod` |
| `BR-BA-011` | Non-Sensitive Standard Restore | `domain.workflows.RestorationWorkflowEngine` |
| `BR-BA-012` | Unapproved Sensitive Block | `services.badms_services.execute_data_restoration` |
| `BR-BA-013` | Missing Archive Request Block | `services.badms_services.request_data_restoration` |
| `BR-BA-014` | SuperAdmin Special Archival | `domain.rules.validate_special_archival_role` |
| `BR-BA-015` | Backup Failure Alerting (3 strikes) | `domain.rules.check_consecutive_backup_failures` |
| `BR-BA-016` | Storage Usage &ge; 80% Threshold | `domain.rules.validate_storage_extension_submission` |
| `BR-BA-017` | Automatic Quota Adjustment | `services.badms_services.decide_storage_extension_hod` |
| `BR-BA-018` | Immutable Audit Logging | `models.AuditLogEntry` (append-only) |
| `BR-BA-019` | Department Scope Log Query | `selectors.badms_selectors.get_audit_logs_for_department` |
| `BR-BA-020` | Sensitive Activity Security Audit | `selectors.badms_selectors.get_security_audit_logs` |
| `BR-BA-021` | Request Owner Visibility | `selectors.badms_selectors.get_user_requests` |

### 2.2 Workflows Traceability
* **CW-BA-01**: Secure Archival Request Lifecycle (`BW-BA-01`, `BW-BA-02`, `BW-BA-03`)
* **CW-BA-02**: Storage Extension Governance (`BW-BA-04`, `BW-BA-05`)
* **CW-BA-03**: Data Restoration Lifecycle (`BW-BA-06`, `BW-BA-07`)

---

## 3. Architecture Contracts & Layering

The BADMS module follows the standard four-tier architecture enforced by `.importlinter`:
1. **`domain/`**: Pure Python business logic and state machine workflows. Zero framework imports (no Django, no DRF, no Celery).
2. **`models.py`**: Relational entity definitions extending standard Django models with strict field validation.
3. **`selectors/`**: Read-only database query functions returning models, QuerySets, or typed summaries.
4. **`services/`**: Atomic write operations, business workflow orchestration, and transaction management.
5. **`api/`**: Django REST Framework API views, serializers, and URL routing.
6. **`contracts.py`**: The official external interface for cross-module integration with Fusion ERP.

---

## 4. Data Models & Schemas

1. **`StorageQuota`**: User storage limits and current consumption (`user_id`, `department_id`, `quota_mb`, `used_storage_mb`).
2. **`BackupSchedule`**: Cron/interval backup scheduling (`name`, `frequency`, `scope`, `is_active`, `last_run`).
3. **`BackupRecord`**: Execution history and status (`job_id`, `status`, `file_path`, `checksum`, `created_at`).
4. **`ArchivalRequest`**: Archival lifecycle tracking (`user_id`, `department_id`, `file_name`, `status`, `classification`).
5. **`EncryptedArchive`**: Encryption metadata for sensitive archives (`request`, `algorithm`, `key_id`, `retention_years`).
6. **`StorageExtensionRequest`**: Quota expansion requests (`user_id`, `requested_mb`, `reason`, `status`, `hod_notes`).
7. **`RestorationRequest`**: Archive restoration requests (`user_id`, `archive_id`, `status`, `approved_by`).
8. **`AuditLogEntry`**: Append-only tamper-evident security log (`event_type`, `actor_id`, `payload`, `timestamp`).

---

## 5. Formal Approval by Student 2

I have reviewed this blueprint against the BADMS Problem Statement v1.2, Requirements Registry v1.1, Use Cases v1.2, Business Rules v1.2, and Workflow Specifications v1.1. The architecture, state machine transitions, role mappings, and requirement citations are fully aligned with the specifications.

* **Approved By**: Ansh Prajapati (`24BCS029`) — Student 2
* **Date**: 2026-11-16
* **Status**: **APPROVED (No Open Gaps)**
