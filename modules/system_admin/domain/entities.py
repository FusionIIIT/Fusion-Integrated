"""Pure Python domain entities and value objects for System Admin module.

Zero Django / DRF imports.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class BasicUserType(StrEnum):
    STUDENT = "student"
    FACULTY = "faculty"
    STAFF = "staff"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    ARCHIVED = "archived"


class RoleAssignmentStatus(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    REASSIGNED = "reassigned"


class PurgeRequestStatus(StrEnum):
    PENDING_IT_HEAD = "pending_it_head"
    APPROVED = "approved"
    REJECTED = "rejected"


class PendingTaskDisposition(StrEnum):
    TRANSFER = "transfer"
    CLOSE = "close"


@dataclass(frozen=True)
class BasicUserRecord:
    user_id: int
    institute_id: str
    user_type: BasicUserType
    email: str
    first_name: str
    last_name: str
    contact_number: str
    department: str
    programme: str = ""
    discipline: str = ""
    batch_year: int | None = None
    employee_id: str = ""
    date_of_joining: date | None = None
    expected_completion_date: date | None = None
    status: UserStatus = UserStatus.ACTIVE
    deactivated_at: datetime | None = None
    archived_at: datetime | None = None
    reversible_until: datetime | None = None
    is_permanently_archived: bool = False
    has_pending_transactions: bool = False


@dataclass(frozen=True)
class RoleDefinitionData:
    code: str
    name: str
    description: str
    module_association: str
    department_association: str = ""
    allowed_user_types: tuple[BasicUserType, ...] = (
        BasicUserType.FACULTY,
        BasicUserType.STAFF,
    )
    is_singular: bool = False
    default_validity_days: int | None = None
    permissions: tuple[str, ...] = ()
    conflict_role_codes: tuple[str, ...] = ()
    is_system_role: bool = False


@dataclass(frozen=True)
class RoleAssignmentRecord:
    assignment_id: int
    user_id: int
    role_code: str
    start_date: date
    end_date: date | None
    scope_type: str = "institute"  # institute, department, hostel, course
    scope_id: str = ""
    reason: str = ""
    status: RoleAssignmentStatus = RoleAssignmentStatus.SCHEDULED
    assigned_by_user_id: int = 0
    assigned_at: datetime | None = None
    effective_revoked_at: datetime | None = None
    revocation_reason: str = ""
    pending_task_disposition: PendingTaskDisposition | None = None
    previous_assignment_id: int | None = None
    previous_holder_audit_until: datetime | None = None


@dataclass(frozen=True)
class ArchivedRecordData:
    archive_id: int
    category: str
    identifier: str
    retention_until: date
    backup_reference: str
    archived_at: datetime
    archived_by_user_id: int
    is_purged: bool = False
    purge_status: PurgeRequestStatus | None = None


@dataclass(frozen=True)
class PurgeRequestData:
    request_id: int
    archive_id: int
    requested_by_user_id: int
    requested_at: datetime
    reason: str
    status: PurgeRequestStatus = PurgeRequestStatus.PENDING_IT_HEAD
    it_head_user_id: int | None = None
    authorized_at: datetime | None = None
    rejection_reason: str = ""


@dataclass(frozen=True)
class AuditEntryData:
    timestamp: datetime
    actor_user_id: int
    actor_username: str
    action: str
    target_type: str = ""
    target_id: str = ""
    ip_address: str = ""
    result: str = "success"  # success | failure
    reason: str = ""
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SystemConfigData:
    password_rotation_days: int = 90
    session_inactivity_timeout_minutes: int = 15
    deactivation_to_archive_days: int = 30
    reversible_archive_window_days: int = 180
    archive_retention_years: int = 7
    role_expiry_lead_days: int = 30
    previous_holder_audit_days: int = 30
    bulk_operation_limit: int = 1000
    failed_login_alert_threshold: int = 5
    enforce_ip_whitelist: bool = False
    ip_whitelist: tuple[str, ...] = ()
