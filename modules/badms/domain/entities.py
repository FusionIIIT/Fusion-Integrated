"""Pure Python domain entities, enums, and data transfer objects for BADMS.

Zero external framework dependencies. This file may NOT import django, rest_framework, or celery.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DataClassification(StrEnum):
    CRITICAL = "critical"
    SENSITIVE = "sensitive"
    ROUTINE = "routine"
    ARCHIVAL = "archival"


class ArchivalStatus(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    HOD_APPROVED = "hod_approved"
    REJECTED = "rejected"
    CLASSIFIED_NON_SENSITIVE = "classified_non_sensitive"
    CLASSIFIED_SENSITIVE = "classified_sensitive"
    SENSITIVE_ARCHIVE_ENCRYPTED = "sensitive_archive_encrypted"


class StorageExtensionStatus(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class RestorationStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    REQUESTED_STANDARD = "requested_standard"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESTORED = "restored"


class BackupStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"


class BackupType(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class ScheduleScope(StrEnum):
    GLOBAL = "global"
    LOCAL = "local"


class ScheduleFrequency(StrEnum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ActorRole(StrEnum):
    USER = "user"
    HOD = "hod"
    SYSADMIN = "sysadmin"
    IT_SECURITY = "it_security"
    SUPER_ADMIN = "super_admin"
    SYSTEM = "system"


class EventSource(StrEnum):
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"
    SECURITY = "security"


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


@dataclass(frozen=True)
class ArchivalRequestDTO:
    id: int
    user_id: int
    department_id: int
    file_name: str
    file_type: str
    file_size_bytes: int
    owners: str
    reason: str
    attachment_path: str
    initial_classification: DataClassification
    status: ArchivalStatus
    authoritative_classification: DataClassification | None = None
    hod_id: int | None = None
    hod_rejection_reason: str = ""
    classified_by_id: int | None = None
    security_officer_id: int | None = None
    encryption_algorithm: str = ""
    encrypted_archive_path: str = ""


@dataclass(frozen=True)
class StorageExtensionDTO:
    id: int
    user_id: int
    department_id: int
    requested_bytes: int
    current_usage_bytes: int
    current_quota_bytes: int
    justification: str
    status: StorageExtensionStatus
    hod_id: int | None = None
    rejection_reason: str = ""


@dataclass(frozen=True)
class RestorationRequestDTO:
    id: int
    user_id: int
    archival_request_id: int
    classification: DataClassification
    reason: str
    target_destination: str
    status: RestorationStatus
    sysadmin_id: int | None = None
    rejection_reason: str = ""


@dataclass(frozen=True)
class BackupRecordDTO:
    id: int
    backup_type: BackupType
    status: BackupStatus
    dataset: str
    repository_path: str
    artifact_path: str = ""
    checksum: str = ""
    size_bytes: int = 0
    is_consistent: bool = True
    error_message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
