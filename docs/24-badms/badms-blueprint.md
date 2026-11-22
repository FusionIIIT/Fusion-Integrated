# BADMS Architecture Blueprint: Backup and Database Archive Management System

---
module_name: Backup and Database Archive Management System (BADMS)
module_code: badms
pair_number: 24
specification_prefix: BA-
spec_folder_path: docs/24-badms/
status: PROPOSED (Awaiting Student 2 Written Approval)
date: 2026-11-23
author: Student 1 (The Builder)
---

## Executive Summary & Parameter Manifest

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **MODULE_NAME** | Backup and Database Archive Management System (BADMS) | Official title of the module |
| **module_code** | `badms` | Lowercase slug without underscores, directory under `modules/` |
| **NN** | `24` | Two-digit pair/module number |
| **ID_PREFIX** | `BA-` | Specification identifier prefix (`CFR-BA-`, `AFR-BA-`, `BA-UC-`, `BR-BA-`, `BW-BA-`, `CW-BA-`) |
| **SPEC_FOLDER_PATH** | `docs/24-badms/` | Dedicated specification and architecture repository folder |

---

## 1. Module Overview & Specification Scope

### 1.1 Context and Mission
The **Backup and Database Archive Management System (BADMS)** is a high-assurance platform module within **Fusion ERP (`Fusion-Integrated`)**. BADMS provides enterprise-grade data protection, lifecycle storage administration, and disaster-recovery capabilities for institute digital assets. Its scope encompasses:
1. **Automated & Manual Backup Orchestration:** Scheduled point-in-time database dumps, local/dataset vs. global schedule resolution, repository reachability verification, backup artifact integrity/consistency verification, failure alerts within 5 minutes, and 3-consecutive-failure escalation.
2. **Multi-Stage Secure Archival Workflow:** User submission with initial classification defaulting to `Routine`, departmental scoping and HoD review/decision, SysAdmin authoritative classification (`Critical`, `Sensitive`, `Routine`, `Archival`), and IT Security AES-256 encryption at rest and in transit for Sensitive research and institutional datasets.
3. **Storage Quota & Extension Management:** Dynamic threshold monitoring, user quota enforcement, full-quota condition validation, and HoD approval for storage extension based on infrastructure and departmental policy.
4. **Data Restoration Operations:** Regulated retrieval of archived datasets, mandatory SysAdmin pre-approval for Sensitive records, and SysAdmin technical restoration execution for both standard and approved sensitive data.
5. **Special Offline Archival Execution:** Direct Super Admin execution for special archival requests received offline from institutional authorities.
6. **Unified Security, RBAC & Audit Visibility:** Fine-grained role-based permissions, strict departmental boundaries for HoDs, role-scoped operational and security reports, and tamper-evident event-triggered audit logging.

### 1.2 Specification Traceability Coverage
This architecture blueprint maps 100% of the synchronized v1.2 specification baseline:
- **19 Consolidated Requirements (CFRs):** `CFR-BA-001` through `CFR-BA-019`
- **66 Atomic Requirements (AFRs):** `AFR-BA-001` through `AFR-BA-068` (excluding historical `AFR-BA-044` and `AFR-BA-050` which were explicitly obsoleted by the spec owner)
- **23 Use Cases (UCs):** `BA-UC-001` through `BA-UC-023`
- **21 Business Rules (BRs):** `BR-BA-001` through `BR-BA-021`
- **10 Workflows (WFs):**
  - **7 Basis Workflows:** `BW-BA-01` to `BW-BA-07`
  - **3 Composite Workflows:** `CW-BA-01`, `CW-BA-02`, `CW-BA-03`

### 1.3 Actors & Access Responsibilities
| Actor | Primary Responsibilities | Governing Specs & Rules |
| :--- | :--- | :--- |
| **User** (`student`, `faculty`, `staff`) | Submits secure archival requests; tracks archival, restoration, and storage extension requests; requests data restoration; requests storage extensions when quota is full; views permitted backup status. | `BA-UC-002`, `007`, `014`, `015`, `016`; `BR-BA-006`, `016` |
| **Department Head (HoD)** (`hod`) | Reviews, approves, or rejects secure archival and storage extension requests exclusively for users belonging to the HoD's department; views departmental operational reports. | `BA-UC-003`, `008`, `021`; `BR-BA-002`, `009`, `010`, `017` |
| **System Administrator (SysAdmin)** (`sysadmin`) | Triggers manual backups; manages local/dataset backup schedules; assigns authoritative classification to HoD-approved archival requests; reviews Sensitive restoration requests; executes technical restorations; views audit logs and operational history. | `BA-UC-001`, `004`, `009`, `012`, `014`, `017`, `018`; `BR-BA-001`, `004`, `005`, `011`, `012` |
| **IT Security Team** (`it_security`) | Configures AES-256 encryption for Sensitive archival datasets; creates encrypted archives; administers BADMS RBAC permissions; manages security policies; audits data-activity logs for unauthorized access. | `BA-UC-005`, `013`, `019`, `020`; `BR-BA-003`, `007`, `021` |
| **Super Admin** (`super_admin`) | Defines institution-wide global backup schedules and default backup policies (highest policy authority); triggers manual backups; executes special archival operations initiated offline. | `BA-UC-001`, `010`, `011`; `BR-BA-001`, `018`, `019` |
| **Director of IT** (`director_it`) | External escalation notification recipient when three consecutive backup failures occur. (Non-interactive role). | `BR-BA-015`, `AFR-BA-058` |
| **System** (Automated Service / Celery) | Executes scheduled backups; evaluates schedule precedence; verifies reachability; checks integrity; triggers failure alerts; monitors user storage quotas; records immutable audit events. | `BA-UC-006`, `022`, `023`; `BR-BA-013`, `014`, `015` |

### 1.4 Scope Boundaries & Explicit Exclusions (Discipline Rules)
In strict adherence to Section 5 of `01_BA_Problem_Statement`:
1. **ISS-BA-007 Clarification:** Special archival requests originate offline from external authorities. Only Super Admin executes the special archival operation within BADMS. No online requester or HoD approval workflow is introduced.
2. **No Research Supervisor Actor:** The Research Supervisor is excluded from this baseline.
3. **No Separate HoD Restoration Route:** Sensitive restoration follows SysAdmin review; non-Sensitive data proceeds via the standard SysAdmin technical restoration procedure.
4. **No Undefined Post-Approval S-POST Actions:** Storage extension lifecycle completes upon recorded HoD decision and user notification.
5. **No Automated Shortfall Remediation:** System flags and rejects requests exceeding infrastructure capacity; no automated hardware provisioning is modeled.
6. **No Explicit Classification-Specific Retention Durations:** Institute retention rules are bound by data classification categories without requiring hardcoded numeric year thresholds.

---

## 2. Pure Domain Model, Invariants & State Machine Enums

### 2.1 Purity Guarantee (`modules/badms/domain/`)
The domain layer is 100% pure Python. It contains **no imports** of `django`, `rest_framework`, `celery`, or any ORM/HTTP dependencies. All domain operations operate on immutable dataclasses, Enums, and pure functions. This enforces lightning-fast, DB-independent unit testing and ensures `.importlinter` compliance.

### 2.2 Domain Enums & Value Types (`modules/badms/domain/entities.py`)
```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime

class DataClassification(str, Enum):
    CRITICAL = "critical"
    SENSITIVE = "sensitive"
    ROUTINE = "routine"
    ARCHIVAL = "archival"

class ArchivalStatus(str, Enum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    HOD_APPROVED = "hod_approved"
    REJECTED = "rejected"
    CLASSIFIED_NON_SENSITIVE = "classified_non_sensitive"
    CLASSIFIED_SENSITIVE = "classified_sensitive"
    SENSITIVE_ARCHIVE_ENCRYPTED = "sensitive_archive_encrypted"

class StorageExtensionStatus(str, Enum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"

class RestorationStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    REQUESTED_STANDARD = "requested_standard"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESTORED = "restored"

class BackupStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"

class BackupType(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"

class ScheduleScope(str, Enum):
    GLOBAL = "global"
    LOCAL = "local"

class ScheduleFrequency(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class ActorRole(str, Enum):
    USER = "user"
    HOD = "hod"
    SYSADMIN = "sysadmin"
    IT_SECURITY = "it_security"
    SUPER_ADMIN = "super_admin"
    SYSTEM = "system"

class EventSource(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"
    SECURITY = "security"

class AuditOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
```

### 2.3 Pure Business Invariants & Rules (`modules/badms/domain/rules/`)

Each business rule from `04_BA_Business_Rule_Specifications` is mapped to an independent pure function:

1. **`BR-BA-001` (Manual Backup Authorization):**
   ```python
   def can_trigger_manual_backup(actor_role: ActorRole) -> bool:
       return actor_role in (ActorRole.SYSADMIN, ActorRole.SUPER_ADMIN)
   ```
2. **`BR-BA-002` & `BR-BA-010` (HoD Departmental Scoping):**
   ```python
   def can_hod_decide_request(hod_dept_id: int, request_dept_id: int, actor_role: ActorRole) -> bool:
       return actor_role == ActorRole.HOD and hod_dept_id == request_dept_id
   ```
3. **`BR-BA-003` & `BR-BA-007` (IT Security Encryption Authority & AES-256 Constraint):**
   ```python
   def can_configure_sensitive_encryption(actor_role: ActorRole, classification: DataClassification) -> bool:
       return actor_role == ActorRole.IT_SECURITY and classification == DataClassification.SENSITIVE
   ```
4. **`BR-BA-004` (SysAdmin Authoritative Classification):**
   ```python
   def can_assign_authoritative_classification(actor_role: ActorRole, current_status: ArchivalStatus) -> bool:
       return actor_role == ActorRole.SYSADMIN and current_status == ArchivalStatus.HOD_APPROVED
   ```
5. **`BR-BA-005` (Sensitive Restoration Approval):**
   ```python
   def requires_restoration_approval(classification: DataClassification) -> bool:
       return classification == DataClassification.SENSITIVE
   ```
6. **`BR-BA-006` (Initial Classification Default):**
   ```python
   def resolve_initial_classification(initial: Optional[DataClassification]) -> DataClassification:
       return initial if initial is not None else DataClassification.ROUTINE
   ```
7. **`BR-BA-009` (HoD Approval for Storage Extension):**
   ```python
   def can_decide_storage_extension(actor_role: ActorRole) -> bool:
       return actor_role == ActorRole.HOD
   ```
8. **`BR-BA-011` (Local Schedule Overrides Global):**
   ```python
   def resolve_effective_schedule(local_schedule: Optional[dict], global_schedule: Optional[dict]) -> Optional[dict]:
       if local_schedule and local_schedule.get("is_active", False):
           return local_schedule
       if global_schedule and global_schedule.get("is_active", False):
           return global_schedule
       return None
   ```
9. **`BR-BA-012` (Schedule Parameter & Conflict Validation):**
   ```python
   def validate_schedule_parameters(frequency: ScheduleFrequency, execution_time: str, dataset: str) -> Tuple[bool, str]:
       if not dataset or not dataset.strip():
           return False, "Target dataset cannot be empty."
       if not execution_time or len(execution_time) != 5 or execution_time[2] != ":":
           return False, "Execution time must be HH:MM format."
       return True, ""
   ```
10. **`BR-BA-013` (Scheduled Repository Reachability Constraint):**
    ```python
    def can_execute_automatic_backup(is_reachable: bool, schedule_active: bool) -> bool:
        return is_reachable and schedule_active
    ```
11. **`BR-BA-014` & `BR-BA-015` (Failure Alert SLA & Escalation):**
    ```python
    def evaluate_failure_escalation(consecutive_failures: int) -> Tuple[bool, bool]:
        # returns (alert_sysadmin, escalate_director_it)
        alert_sysadmin = True # every failure alerts SysAdmin within 5 min
        escalate_director_it = (consecutive_failures >= 3)
        return alert_sysadmin, escalate_director_it
    ```
12. **`BR-BA-016` & `BR-BA-017` (Storage Extension Validation & Decision):**
    ```python
    def validate_storage_extension_submission(current_usage_bytes: int, quota_bytes: int) -> bool:
        return current_usage_bytes >= quota_bytes # quota is full
    
    def validate_infrastructure_capacity(requested_bytes: int, available_infra_bytes: int) -> bool:
        return requested_bytes <= available_infra_bytes
    ```
13. **`BR-BA-018` & `BR-BA-019` (Super Admin Authority Separation):**
    ```python
    def can_perform_special_archival(actor_role: ActorRole) -> bool:
        return actor_role == ActorRole.SUPER_ADMIN

    def can_define_global_backup(actor_role: ActorRole) -> bool:
        return actor_role == ActorRole.SUPER_ADMIN
    ```
14. **`BR-BA-020` & `BR-BA-021` (Protected Information Scope & IT Security RBAC Authority):**
    ```python
    def can_view_protected_record(actor_role: ActorRole, actor_id: int, actor_dept_id: Optional[int],
                                  record_user_id: int, record_dept_id: Optional[int]) -> bool:
        if actor_role in (ActorRole.SYSADMIN, ActorRole.SUPER_ADMIN):
            return True
        if actor_role == ActorRole.IT_SECURITY:
            return True
        if actor_role == ActorRole.HOD:
            return actor_dept_id is not None and actor_dept_id == record_dept_id
        return actor_id == record_user_id
    ```

### 2.4 State Machine Specifications (`modules/badms/domain/state_machines/`)

#### 2.4.1 Secure Archival Request State Machine (`CW-BA-01`, `BW-BA-01..03`)
```
[NOT_SUBMITTED] ──submit (User)──► [SUBMITTED]
                                       │
        ┌──────────────HoD Decision────┴──────────────┐
        ▼                                             ▼
   [REJECTED] (Terminal)                        [HOD_APPROVED]
                                                      │
                       ┌─────────SysAdmin Classify────┴─────────┐
                       ▼                                        ▼
    [CLASSIFIED_NON_SENSITIVE] (Terminal)            [CLASSIFIED_SENSITIVE]
                                                                │
                                            IT Security Encrypt ▼
                                        [SENSITIVE_ARCHIVE_ENCRYPTED] (Terminal)
```
- **Declarative Edge Table:**
  | From State | To State | Trigger / Action | Actor | Guards |
  | :--- | :--- | :--- | :--- | :--- |
  | `NOT_SUBMITTED` | `SUBMITTED` | `submit_archival` | `USER` | `valid_metadata`, `quota_available` |
  | `SUBMITTED` | `REJECTED` | `hod_reject` | `HOD` | `same_department`, `has_rejection_reason` |
  | `SUBMITTED` | `HOD_APPROVED` | `hod_approve` | `HOD` | `same_department` |
  | `HOD_APPROVED` | `CLASSIFIED_NON_SENSITIVE` | `sysadmin_classify` | `SYSADMIN` | `classification_in_(routine, critical, archival)` |
  | `HOD_APPROVED` | `CLASSIFIED_SENSITIVE` | `sysadmin_classify` | `SYSADMIN` | `classification_is_sensitive` |
  | `CLASSIFIED_SENSITIVE` | `SENSITIVE_ARCHIVE_ENCRYPTED` | `it_sec_encrypt` | `IT_SECURITY` | `aes_256_configured` |

#### 2.4.2 Storage Extension Request State Machine (`CW-BA-02`, `BW-BA-04..05`)
```
[NOT_SUBMITTED] ──submit (User)──► [SUBMITTED] ──┬──approve (HoD)──► [APPROVED] (Terminal)
                                                 └──reject (HoD)───► [REJECTED] (Terminal)
```
- **Declarative Edge Table:**
  | From State | To State | Action | Actor | Guards |
  | :--- | :--- | :--- | :--- | :--- |
  | `NOT_SUBMITTED` | `SUBMITTED` | `submit_extension` | `USER` | `quota_is_full`, `infra_sufficient` |
  | `SUBMITTED` | `APPROVED` | `hod_approve` | `HOD` | `same_department` |
  | `SUBMITTED` | `REJECTED` | `hod_reject` | `HOD` | `same_department`, `has_rejection_reason` |

#### 2.4.3 Data Restoration Request State Machine (`CW-BA-03`, `BW-BA-06..07`)
```
                    ┌──Non-Sensitive──► [REQUESTED_STANDARD] ──SysAdmin Execute──┐
[NOT_REQUESTED] ────┤                                                            ├──► [RESTORED] (Terminal)
                    └──Sensitive──────► [PENDING_APPROVAL] ──Approve (SysAdmin)─► [APPROVED] ──SysAdmin Execute─┘
                                                │
                                                └──Reject (SysAdmin)──► [REJECTED] (Terminal)
```
- **Declarative Edge Table:**
  | From State | To State | Action | Actor | Guards |
  | :--- | :--- | :--- | :--- | :--- |
  | `NOT_REQUESTED` | `REQUESTED_STANDARD` | `request_restore` | `USER` | `archive_exists`, `non_sensitive` |
  | `NOT_REQUESTED` | `PENDING_APPROVAL` | `request_restore` | `USER` | `archive_exists`, `sensitive` |
  | `PENDING_APPROVAL` | `APPROVED` | `sysadmin_approve` | `SYSADMIN` | `sysadmin_authenticated` |
  | `PENDING_APPROVAL` | `REJECTED` | `sysadmin_reject` | `SYSADMIN` | `has_rejection_reason` |
  | `REQUESTED_STANDARD` | `RESTORED` | `sysadmin_execute` | `SYSADMIN` | `destination_valid` |
  | `APPROVED` | `RESTORED` | `sysadmin_execute` | `SYSADMIN` | `destination_valid` |

---

## 3. Database Schema & Constraints (`modules/badms/models.py`)

### 3.1 Platform Layering Rules & Database Integrity
1. **Zero Cross-Module ForeignKeys:** All institute entities are referenced strictly as plain indexed integer columns (`user_id = models.IntegerField(db_index=True)`, `department_id = models.IntegerField(db_index=True)`).
2. **Mixins:** All models inherit from `core.db.mixins.TimeStampedModel`. User-specific records inherit from `core.db.mixins.UserScopedModel`.
3. **Database Constraints:** Every model uses explicit database-level `CheckConstraint` and `UniqueConstraint` constructs.

### 3.2 Concrete Models

```python
from django.db import models
from django.db.models import Q
from core.db.mixins import TimeStampedModel, UserScopedModel

class BackupSchedule(TimeStampedModel):
    """Local and global automated backup configurations (CFR-BA-003, CFR-BA-014)."""
    name = models.CharField(max_length=120)
    scope = models.CharField(max_length=20, default="local") # "global" | "local"
    dataset = models.CharField(max_length=80) # dataset name or "all"
    frequency = models.CharField(max_length=20, default="daily") # "hourly", "daily", "weekly", "monthly"
    execution_time = models.CharField(max_length=5, default="02:00") # "HH:MM"
    classification_filter = models.CharField(max_length=30, default="ALL") # "ALL", "CRITICAL", etc.
    repository_path = models.CharField(max_length=255, default="/var/backups/fusion")
    is_active = models.BooleanField(default=True)
    created_by_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "badms_backup_schedule"
        constraints = [
            models.CheckConstraint(
                condition=Q(scope__in=["global", "local"]),
                name="badms_schedule_scope_valid"
            ),
            models.CheckConstraint(
                condition=Q(frequency__in=["hourly", "daily", "weekly", "monthly"]),
                name="badms_schedule_frequency_valid"
            ),
            models.UniqueConstraint(
                fields=["scope", "dataset"],
                name="badms_schedule_unique_scope_dataset"
            ),
        ]

class BackupRecord(TimeStampedModel):
    """Historical database dump and snapshot records (CFR-BA-001, CFR-BA-002, CFR-BA-004)."""
    schedule = models.ForeignKey(BackupSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name="executions")
    backup_type = models.CharField(max_length=20, default="automatic") # "manual" | "automatic"
    status = models.CharField(max_length=20, default="pending") # "pending", "in_progress", "success", "failure"
    trigger_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    dataset = models.CharField(max_length=80, default="all")
    repository_path = models.CharField(max_length=255)
    artifact_path = models.CharField(max_length=255, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    is_consistent = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_backup_record"
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["backup_type", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(backup_type__in=["manual", "automatic"]),
                name="badms_backup_type_valid"
            ),
            models.CheckConstraint(
                condition=Q(status__in=["pending", "in_progress", "success", "failure"]),
                name="badms_backup_status_valid"
            ),
        ]

class SystemState(TimeStampedModel):
    """Singleton/Key-value store for failure counts and system triggers (BR-BA-015)."""
    key = models.CharField(max_length=64, unique=True)
    value_int = models.IntegerField(default=0)
    value_str = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "badms_system_state"

class UserStorageQuota(TimeStampedModel, UserScopedModel):
    """Tracks per-user storage allocations and full-quota state (CFR-BA-013, BR-BA-016)."""
    department_id = models.IntegerField(db_index=True)
    used_bytes = models.BigIntegerField(default=0)
    quota_bytes = models.BigIntegerField(default=10737418240) # 10 GB default
    is_full = models.BooleanField(default=False)
    available_infra_bytes = models.BigIntegerField(default=1099511627776) # 1 TB pool

    class Meta:
        db_table = "badms_user_storage_quota"
        constraints = [
            models.CheckConstraint(
                condition=Q(used_bytes__gte=0),
                name="badms_storage_used_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(quota_bytes__gt=0),
                name="badms_storage_quota_positive"
            ),
            models.UniqueConstraint(
                fields=["user_id"],
                name="badms_user_quota_unique_user"
            ),
        ]

class ArchivalRequest(TimeStampedModel, UserScopedModel):
    """Secure Archival multi-stage entity (CFR-BA-005..008, CW-BA-01)."""
    department_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size_bytes = models.BigIntegerField(default=0)
    owners = models.CharField(max_length=255) # owner usernames or roll numbers
    reason = models.TextField()
    attachment_path = models.CharField(max_length=500)
    initial_classification = models.CharField(max_length=20, default="routine")
    authoritative_classification = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=35, default="submitted")
    
    # Decisions & Timestamps
    hod_id = models.IntegerField(null=True, blank=True, db_index=True)
    hod_decided_at = models.DateTimeField(null=True, blank=True)
    hod_rejection_reason = models.TextField(blank=True)
    
    classified_by_id = models.IntegerField(null=True, blank=True, db_index=True)
    classified_at = models.DateTimeField(null=True, blank=True)
    
    security_officer_id = models.IntegerField(null=True, blank=True, db_index=True)
    encryption_algorithm = models.CharField(max_length=50, blank=True) # AES-256
    encrypted_archive_path = models.CharField(max_length=500, blank=True)
    encryption_configured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_archival_request"
        indexes = [
            models.Index(fields=["department_id", "status"]),
            models.Index(fields=["user_id", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[
                    "submitted", "hod_approved", "rejected",
                    "classified_non_sensitive", "classified_sensitive",
                    "sensitive_archive_encrypted"
                ]),
                name="badms_archival_status_valid"
            ),
            models.CheckConstraint(
                condition=Q(initial_classification__in=["critical", "sensitive", "routine", "archival"]),
                name="badms_archival_initial_class_valid"
            ),
        ]

class SpecialArchivalRecord(TimeStampedModel):
    """Super Admin direct offline-initiated archival record (CFR-BA-010, BR-BA-018)."""
    dataset_name = models.CharField(max_length=150)
    source_authority = models.CharField(max_length=150) # Offline originator reference
    reason = models.TextField()
    classification = models.CharField(max_length=20, default="sensitive")
    archive_path = models.CharField(max_length=500)
    performed_by_id = models.IntegerField(db_index=True) # Super Admin user_id
    size_bytes = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=64)

    class Meta:
        db_table = "badms_special_archival_record"

class StorageExtensionRequest(TimeStampedModel, UserScopedModel):
    """User storage expansion request (CFR-BA-012, CW-BA-02)."""
    department_id = models.IntegerField(db_index=True)
    requested_bytes = models.BigIntegerField()
    current_usage_bytes = models.BigIntegerField()
    current_quota_bytes = models.BigIntegerField()
    justification = models.TextField()
    attachment_path = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, default="submitted")
    
    hod_id = models.IntegerField(null=True, blank=True, db_index=True)
    hod_decided_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "badms_storage_extension_request"
        indexes = [
            models.Index(fields=["department_id", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(requested_bytes__gt=0),
                name="badms_extension_bytes_positive"
            ),
            models.CheckConstraint(
                condition=Q(status__in=["submitted", "approved", "rejected"]),
                name="badms_extension_status_valid"
            ),
        ]

class RestorationRequest(TimeStampedModel, UserScopedModel):
    """Archived data restoration requests (CFR-BA-011, CW-BA-03)."""
    archival_request = models.ForeignKey(ArchivalRequest, on_delete=models.CASCADE, related_name="restorations")
    classification = models.CharField(max_length=20) # Snapshot from archival_request
    reason = models.TextField()
    target_destination = models.CharField(max_length=255)
    status = models.CharField(max_length=30, default="requested_standard")
    
    sysadmin_id = models.IntegerField(null=True, blank=True, db_index=True)
    sysadmin_decided_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_restoration_request"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[
                    "requested_standard", "pending_approval",
                    "approved", "rejected", "restored"
                ]),
                name="badms_restoration_status_valid"
            ),
        ]

class AuditLog(TimeStampedModel):
    """Tamper-evident audit trail (CFR-BA-018, BA-UC-023)."""
    actor_id = models.IntegerField(null=True, blank=True, db_index=True)
    actor_username = models.CharField(max_length=100, blank=True)
    actor_role = models.CharField(max_length=50, blank=True)
    event_source = models.CharField(max_length=30, default="user") # "user", "admin", "system", "security"
    action = models.CharField(max_length=120)
    resource_type = models.CharField(max_length=80)
    resource_id = models.CharField(max_length=80, blank=True)
    department_id = models.IntegerField(null=True, blank=True, db_index=True)
    outcome = models.CharField(max_length=20, default="success") # "success", "failure", "denied"
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.CharField(max_length=45, blank=True)

    class Meta:
        db_table = "badms_audit_log"
        indexes = [
            models.Index(fields=["event_source", "-created_at"]),
            models.Index(fields=["actor_id", "-created_at"]),
            models.Index(fields=["department_id", "-created_at"]),
        ]

class SecurityPolicy(TimeStampedModel):
    """IT Security configurable controls (CFR-BA-019, BA-UC-020)."""
    key = models.CharField(max_length=60, unique=True)
    policy_name = models.CharField(max_length=120)
    encryption_algorithm = models.CharField(max_length=40, default="AES-256")
    is_enforced = models.BooleanField(default=True)
    parameters = models.JSONField(default=dict, blank=True)
    updated_by_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "badms_security_policy"

class NotificationLog(TimeStampedModel):
    """Notification dispatch log (CFR-BA-016, CFR-BA-017, BR-BA-014, BR-BA-015)."""
    recipient_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_email = models.CharField(max_length=150, blank=True)
    recipient_role = models.CharField(max_length=50)
    notification_type = models.CharField(max_length=60)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "badms_notification_log"
```

---

## 4. Selectors & Services Architecture

### 4.1 Strict Layer Separation
- **`selectors/`:** Pure query functions. **Read-only**. Never mutate database records. Respects actor visibility and departmental boundaries.
- **`services/`:** Transaction boundaries (`@transaction.atomic`). Coordinates domain rule evaluations, state machine transitions, persistence, audit logging, and notification queueing. Services raise domain exceptions, not HTTP status codes.

### 4.2 Selectors Catalog (`modules/badms/selectors/`)

```python
# modules/badms/selectors/backups.py
def list_backups(*, status: Optional[str] = None, backup_type: Optional[str] = None, limit: int = 25) -> QuerySet[BackupRecord]: ...
def get_backup_by_id(backup_id: int) -> Optional[BackupRecord]: ...
def get_effective_schedule(dataset: str) -> Optional[BackupSchedule]: ...
def list_schedules(*, scope: Optional[str] = None) -> QuerySet[BackupSchedule]: ...

# modules/badms/selectors/archival.py
def list_user_archival_requests(user_id: int) -> QuerySet[ArchivalRequest]: ...
def list_department_archival_requests(department_id: int, status: Optional[str] = None) -> QuerySet[ArchivalRequest]: ...
def list_sysadmin_archival_queue() -> QuerySet[ArchivalRequest]: ...
def list_security_encryption_queue() -> QuerySet[ArchivalRequest]: ...
def get_archival_request_by_id(request_id: int) -> Optional[ArchivalRequest]: ...

# modules/badms/selectors/storage.py
def get_user_storage_quota(user_id: int) -> Optional[UserStorageQuota]: ...
def list_department_storage_extensions(department_id: int, status: Optional[str] = None) -> QuerySet[StorageExtensionRequest]: ...
def get_user_storage_extensions(user_id: int) -> QuerySet[StorageExtensionRequest]: ...
def get_storage_extension_by_id(extension_id: int) -> Optional[StorageExtensionRequest]: ...

# modules/badms/selectors/restorations.py
def list_user_restorations(user_id: int) -> QuerySet[RestorationRequest]: ...
def list_sysadmin_restoration_queue(status: Optional[str] = None) -> QuerySet[RestorationRequest]: ...
def get_restoration_request_by_id(restoration_id: int) -> Optional[RestorationRequest]: ...

# modules/badms/selectors/audit.py
def list_audit_logs(*, actor_id: Optional[int] = None, event_source: Optional[str] = None,
                    department_id: Optional[int] = None, limit: int = 50) -> QuerySet[AuditLog]: ...

# modules/badms/selectors/reports.py
def get_department_operational_stats(department_id: int) -> dict: ...
def get_security_audit_summary() -> dict: ...
def get_backup_compliance_summary() -> dict: ...
```

### 4.3 Services Catalog (`modules/badms/services/`)

```python
# modules/badms/services/backup_service.py
def trigger_manual_backup(*, actor_id: int, actor_role: str, dataset: str = "all") -> BackupRecord: ...
def execute_scheduled_backup(*, schedule_id: Optional[int] = None, dataset: str = "all") -> BackupRecord: ...
def verify_backup_integrity(*, backup_id: int) -> bool: ...
def handle_backup_failure(*, backup_id: int, error_message: str) -> None: ...

# modules/badms/services/schedule_service.py
def create_local_schedule(*, actor_id: int, name: str, dataset: str, frequency: str, execution_time: str, classification_filter: str) -> BackupSchedule: ...
def create_global_schedule(*, actor_id: int, name: str, frequency: str, execution_time: str) -> BackupSchedule: ...
def update_schedule(*, schedule_id: int, actor_id: int, actor_role: str, **fields) -> BackupSchedule: ...

# modules/badms/services/archival_service.py
def submit_archival_request(*, user_id: int, department_id: int, file_name: str, file_type: str, file_size_bytes: int,
                            attachment_path: str, reason: str, owners: str, initial_classification: Optional[str] = None) -> ArchivalRequest: ...
def decide_archival_request_hod(*, request_id: int, hod_id: int, hod_dept_id: int, approve: bool, rejection_reason: str = "") -> ArchivalRequest: ...
def classify_archival_request_sysadmin(*, request_id: int, sysadmin_id: int, authoritative_classification: str) -> ArchivalRequest: ...
def configure_sensitive_encryption(*, request_id: int, security_officer_id: int, encryption_algorithm: str = "AES-256") -> ArchivalRequest: ...
def execute_special_archival(*, super_admin_id: int, dataset_name: str, source_authority: str, reason: str, archive_path: str, size_bytes: int) -> SpecialArchivalRecord: ...

# modules/badms/services/storage_service.py
def submit_storage_extension(*, user_id: int, department_id: int, requested_bytes: int, justification: str, attachment_path: str = "") -> StorageExtensionRequest: ...
def decide_storage_extension_hod(*, request_id: int, hod_id: int, hod_dept_id: int, approve: bool, rejection_reason: str = "") -> StorageExtensionRequest: ...
def evaluate_user_storage_thresholds(*, user_id: int) -> bool: ...

# modules/badms/services/restoration_service.py
def submit_restoration_request(*, user_id: int, archival_request_id: int, target_destination: str, reason: str) -> RestorationRequest: ...
def decide_sensitive_restoration_sysadmin(*, restoration_id: int, sysadmin_id: int, approve: bool, rejection_reason: str = "") -> RestorationRequest: ...
def execute_technical_restoration(*, restoration_id: int, sysadmin_id: int) -> RestorationRequest: ...

# modules/badms/services/audit_service.py
def record_audit_event(*, actor_id: Optional[int], actor_username: str, actor_role: str, event_source: str,
                       action: str, resource_type: str, resource_id: str, outcome: str,
                       department_id: Optional[int] = None, details: Optional[dict] = None) -> AuditLog: ...

# modules/badms/services/notification_service.py
def queue_notification(*, recipient_id: Optional[int], recipient_role: str, recipient_email: str,
                       notification_type: str, subject: str, body: str) -> NotificationLog: ...
def dispatch_pending_notifications() -> int: ...
```

---

## 5. REST API Interface, Schema Contracts & RBAC Matrix

### 5.1 API Architectural Conventions
1. **Base Prefix:** `/api/v1/badms/`
2. **Naming:** Plural nouns, `snake_case` in request/response bodies, no trailing slash (`APPEND_SLASH = False`).
3. **Pagination:** DRF cursor pagination via `core.api.pagination`.
4. **Standard Envelope:**
   - Single resource success: Direct JSON unwrapped object.
   - Collection success: `{"results": [...], "next": "...", "previous": null}`.
   - Error response: `{"error": {"code": "...", "message": "...", "details": [...], "request_id": "..."}}`.
   - Status codes: `200` (OK), `201` (Created), `400` (Malformed), `403` (Forbidden), `404` (Not Found / Masked), `409` (State Conflict), `422` (Business Rule Refusal).

### 5.2 API Endpoints Matrix

| HTTP Method | Path | Required Permission | Description & Spec Ref |
| :--- | :--- | :--- | :--- |
| **POST** | `/backups/manual` | `badms.backup.trigger` | Trigger point-in-time manual backup (`BA-UC-001`, `BR-BA-001`) |
| **GET** | `/backups` | `badms.backup.view` | List historical backups with status (`BA-UC-014`, `CFR-BA-004`) |
| **GET** | `/backups/{id}` | `badms.backup.view` | Retrieve single backup details (`BA-UC-014`) |
| **GET** | `/schedules` | `badms.schedule.view` | List local and global backup schedules (`CFR-BA-003`, `BA-UC-009`) |
| **POST** | `/schedules` | `badms.schedule.manage` | Create local or global backup schedule (`BR-BA-012`, `BR-BA-019`) |
| **PATCH** | `/schedules/{id}` | `badms.schedule.manage` | Update existing backup schedule (`BA-UC-009`) |
| **POST** | `/archival-requests` | `badms.archival.submit` | Submit secure archival request (`BA-UC-002`, `BR-BA-006`) |
| **GET** | `/archival-requests` | `badms.archival.view` | List archival requests (scoped by user, HoD dept, or admin) |
| **GET** | `/archival-requests/{id}` | `badms.archival.view` | Detail of archival request with tracking history (`BA-UC-015`) |
| **POST** | `/archival-requests/{id}/hod-decision` | `badms.archival.hod_decide` | HoD approve or reject request (`BA-UC-003`, `BR-BA-002`, `BR-BA-010`) |
| **POST** | `/archival-requests/{id}/classify` | `badms.archival.classify` | SysAdmin assign authoritative classification (`BA-UC-004`, `BR-BA-004`) |
| **POST** | `/archival-requests/{id}/configure-encryption` | `badms.archival.encrypt` | IT Security configure AES-256 (`BA-UC-005`, `BR-BA-003`, `BR-BA-007`) |
| **POST** | `/special-archival` | `badms.special_archival.execute`| Super Admin direct special archival (`BA-UC-010`, `BR-BA-018`) |
| **GET** | `/storage/quota` | `badms.storage.view_self` | Retrieve authenticated user storage quota & threshold (`BA-UC-022`) |
| **POST** | `/storage/extensions` | `badms.storage.request_extension`| Submit storage extension request (`BA-UC-007`, `BR-BA-016`) |
| **GET** | `/storage/extensions` | `badms.storage.view` | List storage extension requests (user or HoD queue) |
| **POST** | `/storage/extensions/{id}/hod-decision` | `badms.storage.hod_decide` | HoD approve/reject extension (`BA-UC-008`, `BR-BA-009`, `BR-BA-017`) |
| **POST** | `/restorations` | `badms.restoration.request` | Submit restoration request for archive (`BA-UC-016`, `BR-BA-005`) |
| **GET** | `/restorations` | `badms.restoration.view` | List restorations (user requests or SysAdmin queue) |
| **POST** | `/restorations/{id}/sysadmin-decision` | `badms.restoration.approve`| SysAdmin approve/reject Sensitive restore (`BA-UC-017`, `BR-BA-005`) |
| **POST** | `/restorations/{id}/execute` | `badms.restoration.execute` | SysAdmin execute technical restoration (`BA-UC-018`) |
| **GET** | `/audit-logs` | `badms.audit.view` | Scoped audit logs (SysAdmin & IT Security) (`BA-UC-012`, `013`) |
| **GET** | `/reports/departmental` | `badms.report.departmental` | Departmental operational report (`BA-UC-021`, `BR-BA-010`) |
| **GET** | `/reports/security` | `badms.report.security` | IT Security audit and threat report (`BA-UC-013`, `BR-BA-021`) |
| **GET** | `/reports/compliance` | `badms.report.compliance` | Backup operational visibility and compliance report (`AFR-BA-065`) |
| **GET** | `/security/policies` | `badms.security.manage` | View IT security encryption & access policies (`BA-UC-020`) |
| **PATCH** | `/security/policies` | `badms.security.manage` | Configure IT security policies (`BA-UC-020`, `BR-BA-021`) |

### 5.3 Permissions & RBAC Seed Configuration (`modules/badms/registry.py`)

```python
MODULE = {
    "code": "badms",
    "label": "Backup & Database Archive",
    "icon": "FaDatabase",
    "base_path": "/badms",
    "nav_section": "System Administration",
    "sort_order": 45,
    "status": "active",
}

NAV_ITEMS = [
    # User items
    {"code": "badms.my_requests", "label": "My Requests", "icon": "FaFolderOpen",
     "to": "/badms/requests", "required_permission": "badms.archival.view", "sort_order": 10},
    {"code": "badms.archive_submit", "label": "Submit Archival", "icon": "FaCloudUploadAlt",
     "to": "/badms/archival/new", "required_permission": "badms.archival.submit", "sort_order": 20},
    {"code": "badms.my_quota", "label": "Storage Quota", "icon": "FaHdd",
     "to": "/badms/quota", "required_permission": "badms.storage.view_self", "sort_order": 30},
     
    # HoD items
    {"code": "badms.hod_queue", "label": "Department Approvals", "icon": "FaCheckCircle",
     "to": "/badms/hod/approvals", "required_permission": "badms.archival.hod_decide", "sort_order": 40},
    {"code": "badms.dept_reports", "label": "Department Reports", "icon": "FaChartPie",
     "to": "/badms/hod/reports", "required_permission": "badms.report.departmental", "sort_order": 50},

    # SysAdmin items
    {"code": "badms.backup_console", "label": "Backup Console", "icon": "FaServer",
     "to": "/badms/admin/backups", "required_permission": "badms.backup.view", "sort_order": 60},
    {"code": "badms.schedules", "label": "Backup Schedules", "icon": "FaCalendarAlt",
     "to": "/badms/admin/schedules", "required_permission": "badms.schedule.view", "sort_order": 70},
    {"code": "badms.classify_queue", "label": "Classification Queue", "icon": "FaTags",
     "to": "/badms/admin/classify", "required_permission": "badms.archival.classify", "sort_order": 80},
    {"code": "badms.restorations_console", "label": "Restorations", "icon": "FaTrashRestore",
     "to": "/badms/admin/restorations", "required_permission": "badms.restoration.approve", "sort_order": 90},
    {"code": "badms.audit_logs", "label": "Audit Logs", "icon": "FaShieldAlt",
     "to": "/badms/admin/audit", "required_permission": "badms.audit.view", "sort_order": 100},

    # IT Security items
    {"code": "badms.security_encryption", "label": "Sensitive Encryption", "icon": "FaLock",
     "to": "/badms/security/encryption", "required_permission": "badms.archival.encrypt", "sort_order": 110},
    {"code": "badms.security_policies", "label": "Security Policies", "icon": "FaKey",
     "to": "/badms/security/policies", "required_permission": "badms.security.manage", "sort_order": 120},
]

PERMISSIONS = [
    ("badms.backup.trigger", "Trigger on-demand manual database backups"),
    ("badms.backup.view", "View backup execution history and status"),
    ("badms.schedule.view", "View automated backup schedules"),
    ("badms.schedule.manage", "Create and modify local and global backup schedules"),
    ("badms.archival.submit", "Submit files and metadata for secure archival"),
    ("badms.archival.view", "View secure archival request status and history"),
    ("badms.archival.hod_decide", "Approve or reject departmental secure archival requests"),
    ("badms.archival.classify", "Assign authoritative data classification to archival requests"),
    ("badms.archival.encrypt", "Configure AES-256 encryption and build sensitive archives"),
    ("badms.special_archival.execute", "Execute offline-originated special archival operations"),
    ("badms.storage.view_self", "View own storage usage and quota allocation"),
    ("badms.storage.request_extension", "Request storage quota expansion when full"),
    ("badms.storage.view", "View storage extension requests"),
    ("badms.storage.hod_decide", "Approve or reject departmental storage extensions"),
    ("badms.restoration.request", "Request restoration of archived data"),
    ("badms.restoration.view", "View data restoration request history and status"),
    ("badms.restoration.approve", "Review and approve Sensitive data restoration requests"),
    ("badms.restoration.execute", "Execute technical restoration of archived data"),
    ("badms.audit.view", "View tamper-evident audit logs and activity histories"),
    ("badms.report.departmental", "View departmental data management operational reports"),
    ("badms.report.security", "View security audit reports and unauthorized access alerts"),
    ("badms.report.compliance", "View overall backup compliance and status reports"),
    ("badms.security.manage", "Manage BADMS RBAC permissions and security policies"),
]

SYSTEM_PERMISSIONS = [
    "badms.backup.execute_automatic",
    "badms.storage.monitor_thresholds",
]

# Role mapping definitions
_USER = [
    "badms.archival.submit",
    "badms.archival.view",
    "badms.storage.view_self",
    "badms.storage.request_extension",
    "badms.restoration.request",
    "badms.restoration.view",
    "badms.backup.view",
]

_HOD = [
    *_USER,
    "badms.archival.hod_decide",
    "badms.storage.hod_decide",
    "badms.storage.view",
    "badms.report.departmental",
]

_SYSADMIN = [
    *_USER,
    "badms.backup.trigger",
    "badms.backup.view",
    "badms.schedule.view",
    "badms.schedule.manage",
    "badms.archival.classify",
    "badms.restoration.approve",
    "badms.restoration.execute",
    "badms.audit.view",
    "badms.report.compliance",
]

_IT_SECURITY = [
    "badms.archival.encrypt",
    "badms.archival.view",
    "badms.audit.view",
    "badms.report.security",
    "badms.security.manage",
]

_SUPER_ADMIN = [
    *_SYSADMIN,
    "badms.special_archival.execute",
    "badms.security.manage",
]

ROLE_GRANTS = {
    "student": _USER,
    "faculty": _USER,
    "staff": _USER,
    "HOD (CSE)": _HOD,
    "HOD (ECE)": _HOD,
    "HOD (ME)": _HOD,
    "HOD (Design)": _HOD,
    "sysadmin": _SYSADMIN,
    "technical_officer": _SYSADMIN,
    "it_security_lead": _IT_SECURITY,
    "it_security_auditor": _IT_SECURITY,
    "Super Admin": _SUPER_ADMIN,
    "Director": _SUPER_ADMIN,
}
```

---

## 6. Inter-Module Contracts & System Integrations

### 6.1 Public Contract Surface (`modules/badms/contracts.py`)
To prevent N+1 queries and adhere strictly to `ops/checks/contracts_are_plural.py`, all contract functions take a sequence of IDs and return dictionary mappings:

```python
"""badms public surface. Strictly plural by signature."""
from __future__ import annotations
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional, List

@dataclass(frozen=True)
class UserStorageQuotaDTO:
    user_id: int
    used_bytes: int
    quota_bytes: int
    is_full: bool

@dataclass(frozen=True)
class UserArchivalSummaryDTO:
    user_id: int
    total_archived_files: int
    total_archived_bytes: int
    has_sensitive_data: bool

def get_user_storage_quotas(user_ids: Sequence[int]) -> dict[int, UserStorageQuotaDTO]:
    """Exposes current storage usage and quota states to external modules (e.g. Directory/Leave)."""
    ...

def get_user_archival_summaries(user_ids: Sequence[int]) -> dict[int, UserArchivalSummaryDTO]:
    """Exposes high-level archival metrics for administrative clearance or profile views."""
    ...
```

### 6.2 External Module Dependencies
- **`modules.directory.contracts.get_users(user_ids)`**: Used to retrieve user metadata (such as `department`, `display_name`, `email`) without cross-module joins or database foreign keys.

### 6.3 Celery Recurring Tasks (`modules/badms/schedule.py`)
Registered in `config/celery.py`:

```python
from celery.schedules import crontab

TASK_ROUTES = {
    "badms.execute_scheduled_backups": {"queue": "backups"},
    "badms.monitor_storage_thresholds": {"queue": "default"},
    "badms.drain_notification_queue": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # Automatic scheduled backup processor: runs every minute to match scheduled HH:MM triggers
    "badms.execute-scheduled-backups": {
        "task": "badms.execute_scheduled_backups",
        "schedule": 60.0,
        "options": {"expires": 50},
    },
    # Periodic storage quota sweep: refreshes full-quota status every 15 minutes
    "badms.monitor-storage-thresholds": {
        "task": "badms.monitor_storage_thresholds",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
    # Outbound notification delivery queue drainer: runs every 30 seconds
    "badms.drain-notifications": {
        "task": "badms.drain_notification_queue",
        "schedule": 30.0,
        "options": {"expires": 25},
    },
}
```

### 6.4 Boundary Linter Registration (`.importlinter`)
Addition of the BADMS layering contract and domain isolation rules:

```ini
[importlinter:contract:badms-layers]
name = Layering inside badms
type = layers
layers =
    modules.badms.api
    modules.badms.services
    modules.badms.selectors
    modules.badms.models
    modules.badms.domain
```
And inclusion of `modules.badms` in `modules-only-touch-contracts` and `modules.badms.domain` in `domain-is-pure-python`.

---

## 7. Frontend Security & Dashboard Design (`modules/badms/templates/badms/dashboard.html`)

### 7.1 Stored XSS Prevention Mandate
In strict compliance with Assignment Constraint #6:
- **Zero `.innerHTML` Usage:** No dynamic value retrieved from API responses or user input will ever be assigned to `.innerHTML` or `outerHTML`.
- **Safe DOM APIs:** All text nodes will be populated strictly via `element.textContent = data.value`.
- **Dynamic Element Generation:** All lists, tables, badges, and modals will be constructed via `document.createElement()`, `element.setAttribute()`, and `element.appendChild()`.

### 7.2 Multi-Role Tabbed Console
The dashboard provides a cohesive single-page interface with tabbed views conditionally rendered based on the active principal's permissions:
1. **My Requests Tab (All Users):** Submit new archival requests, request storage extension, request restoration, and track live status.
2. **HoD Approvals Tab (HoD Role):** Departmental approval queue for secure archival and storage extensions with one-click decision dialogs.
3. **Backup Operations Tab (SysAdmin Role):** On-demand backup trigger button, execution history table with status badges, and local schedule manager.
4. **Data Classification Tab (SysAdmin Role):** Queue of HoD-approved requests ready for authoritative classification (`Critical`, `Sensitive`, `Routine`, `Archival`).
5. **Restoration Queue Tab (SysAdmin Role):** Sensitive restoration approvals and execution action triggers.
6. **Security & Policies Tab (IT Security Role):** Sensitive archive encryption configuration, policy toggles, and audit report viewer.
7. **Global Schedules Tab (Super Admin Role):** Institution-wide backup schedule definitions and offline special archival triggering form.

---

## 8. Gap Analysis, Design Decisions & Assumptions

| # | Spec Item | Potential Ambiguity / Risk | Architectural Resolution | Specification Justification |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `AFR-BA-029` / `BR-BA-006` | Initial classification optionality | If `initial_classification` is omitted or empty on intake, system assigns `routine` by default. | Explicitly stated in `BR-BA-006` and `CFR-BA-005`. |
| 2 | `AFR-BA-037` / `BR-BA-018` | Origin of special archival requests | Modeled as an offline request. Only Super Admin has access to the `/special-archival` endpoint. No online multi-actor workflow is created. | Confirmed by Problem Statement Section 4 (Resolved Clarification `ISS-BA-007`). |
| 3 | `AFR-BA-041` / `BR-BA-005` | Restoration approval path | Sensitive restoration requires SysAdmin approval before execution. Non-Sensitive restoration proceeds directly to technical execution. | Problem Statement Section 3.5 & `BR-BA-005`. HoD restoration route is explicitly out of scope. |
| 4 | `BR-BA-011` / `AFR-BA-055` | Schedule resolution precedence | When an active local schedule exists for a dataset, it overrides the global schedule. If no local schedule exists, the global schedule is applied. | Explicitly stated in `BR-BA-011` and `CFR-BA-014`. |
| 5 | `BR-BA-014` & `BR-BA-015` | Backup failure alerts & escalation | Every failed backup generates an alert to SysAdmin within 5 minutes. If 3 consecutive failures occur, an escalation alert is dispatched to Director of IT. | Stated in `BR-BA-014` and `BR-BA-015`. Modeled via `SystemState` consecutive failure counter. |
| 6 | `BR-BA-016` / `AFR-BA-045` | Storage extension prerequisite | Submitting a storage extension requires `current_usage >= quota`. If the quota is not full, submission returns a 422 validation refusal. | Stated in `BR-BA-016` ("quota is full"). |
| 7 | `BR-BA-010` / `AFR-BA-026` | HoD Department Scoping | HoDs may only approve/reject requests where the requester's `department_id` matches the HoD's department. Mismatches return 404 (existence masked) or 403. | Adheres to ADR-0010, `BR-BA-010`, and platform API conventions. |
| 8 | Historical `FR-BA-044`, `FR-BA-050` | Missing atomic requirements | Excluded from the implementation per Section 1 of `02_BA_Requirement_Registry`. Numeric numbering skips 044 and 050 without impact. | Registry v1.1 notes that module owner explicitly excluded those obligations. |

---

## 9. Verification & Quality Gate Plan
Before submitting the module for review:
1. **Import Linter:** `wsl -e bash -c "cd /mnt/c/Users/Lenovo/Downloads/Fusion-Integrated && .venv/bin/lint-imports"` must report **Contracts: 5 kept, 0 broken**.
2. **Cross-Module Foreign Key Check:** `python ops/checks/no_cross_module_fk.py` must pass with 0 cross-module foreign keys.
3. **Contracts Plurality Check:** `python ops/checks/contracts_are_plural.py` must confirm all contract getters take sequences.
4. **Domain Unit Tests:** `pytest modules/badms/tests/test_rules.py` and `test_workflows.py` with 100% pass rate and >90% branch coverage on domain rules.
5. **Schema & Permissions Sync:** `make schema` and `make permissions` cleanly update the OpenAPI specs and permission manifests.

---

**END OF BLUEPRINT**
*(Phase 1 complete. Awaiting written approval before starting Phase 2).*
