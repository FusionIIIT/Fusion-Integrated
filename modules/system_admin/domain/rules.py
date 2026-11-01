"""Pure Python business rule validators for System Admin module.

Implements BR-SA-001 through BR-SA-035.
Zero Django / DRF imports.
"""
from datetime import date, datetime, timedelta
import re
from typing import Any, Sequence

from .entities import (
    BasicUserType,
    PendingTaskDisposition,
    UserStatus,
)
from .errors import (
    ActiveRoleInvalidError,
    ArchivedUserPermanentError,
    AuditLogArchivalProhibitedError,
    BulkLimitExceededError,
    CriticalOperationReauthRequiredError,
    DuplicateInstituteIdError,
    HistoricalDataArchivalIneligibleError,
    InstituteIdImmutableError,
    InvalidInstituteEmailError,
    InvalidNoticePeriodError,
    InvalidRoleDatesError,
    MissingUserTypeDataError,
    OperationalContentAccessForbiddenError,
    PermittedConfigBoundaryError,
    PurgeRetentionNotElapsedError,
    RoleConflictError,
    RoleIncompatibleUserTypeError,
    SingularRoleOccupancyError,
    SuperAdminSelfModificationForbiddenError,
    SystemAdminDomainError,
    UserArchivalIneligibleError,
)

INSTITUTE_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.)*iiitdmj\.ac\.in$", re.IGNORECASE
)
GENERAL_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# BR-SA-026: Prohibited operational resources
PROHIBITED_OPERATIONAL_RESOURCES = frozenset([
    "academic_grades",
    "course_grades",
    "transcripts",
    "financial_ledger",
    "fee_payments",
    "bank_transactions",
    "medical_records",
    "complaint_details",
    "disciplinary_submissions",
    "placement_applications",
    "student_resumes",
])

# BR-SA-035: Permitted system configuration parameters
PERMITTED_CONFIG_KEYS = frozenset([
    "password_rotation_days",
    "session_inactivity_timeout_minutes",
    "deactivation_to_archive_days",
    "reversible_archive_window_days",
    "archive_retention_years",
    "role_expiry_lead_days",
    "previous_holder_audit_days",
    "bulk_operation_limit",
    "failed_login_alert_threshold",
    "enforce_ip_whitelist",
    "ip_whitelist",
    "notification_channels",
])


# BR-SA-001: Institute ID Uniqueness and Immutability
def validate_institute_id_immutability(old_institute_id: str, new_institute_id: str) -> None:
    if old_institute_id != new_institute_id:
        raise InstituteIdImmutableError(
            f"Institute ID cannot be changed from '{old_institute_id}' to '{new_institute_id}'."
        )


def validate_institute_id_uniqueness(institute_id: str, existing_ids: set[str]) -> None:
    if not institute_id or not institute_id.strip():
        raise SystemAdminDomainError("Institute ID cannot be empty.")
    if institute_id.strip() in existing_ids:
        raise DuplicateInstituteIdError(f"Institute ID '{institute_id}' is already registered.")


# BR-SA-002: Institute Email Validation
def validate_institute_email(email: str, allow_subdomains: bool = True) -> None:
    if not email or not email.strip():
        raise InvalidInstituteEmailError("Institute email is required.")
    email_clean = email.strip()
    if not GENERAL_EMAIL_REGEX.match(email_clean):
        raise InvalidInstituteEmailError(f"Invalid email format: '{email}'.")
    if not INSTITUTE_EMAIL_REGEX.match(email_clean):
        raise InvalidInstituteEmailError(
            f"Email '{email}' must be a valid institute email ending with iiitdmj.ac.in."
        )


# BR-SA-003: User-Type Required Data
def validate_user_type_required_data(user_type: BasicUserType | str, data: dict[str, Any]) -> None:
    missing: list[str] = []
    # Common required fields
    for field in ["institute_id", "email", "first_name", "last_name"]:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)

    u_type = BasicUserType(user_type) if isinstance(user_type, str) else user_type

    if u_type == BasicUserType.STUDENT:
        for field in ["programme", "batch_year"]:
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(field)
    elif u_type in (BasicUserType.FACULTY, BasicUserType.STAFF):
        for field in ["department", "employee_id"]:
            val = data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(field)

    if missing:
        raise MissingUserTypeDataError(
            f"Missing required fields for {u_type.value}: {', '.join(missing)}.",
            missing_fields=missing,
        )


# BR-SA-004: User Archival Eligibility
def validate_user_archival_eligibility(
    status: UserStatus | str,
    deactivated_at: datetime | None,
    min_interval_days: int,
    has_pending_transactions: bool,
    current_time: datetime | None = None,
) -> None:
    user_status = UserStatus(status) if isinstance(status, str) else status
    if user_status != UserStatus.DEACTIVATED:
        raise UserArchivalIneligibleError(
            f"Only deactivated users may be archived (current status: {user_status.value})."
        )
    if has_pending_transactions:
        raise UserArchivalIneligibleError(
            "User has unresolved transactions or obligations and cannot be archived."
        )
    if not deactivated_at:
        raise UserArchivalIneligibleError("User has no recorded deactivation timestamp.")
    
    now = current_time or datetime.now()
    days_elapsed = (now - deactivated_at).total_seconds() / 86400.0
    if days_elapsed < min_interval_days:
        raise UserArchivalIneligibleError(
            f"User must remain deactivated for {min_interval_days} days before archival (elapsed: {int(days_elapsed)} days)."
        )


# BR-SA-005 / ISS-SA-004: Archived User Reversibility Window
def validate_archived_user_reversibility(
    archived_at: datetime | None,
    reversible_window_days: int,
    is_permanently_archived: bool,
    current_time: datetime | None = None,
) -> None:
    if is_permanently_archived:
        raise ArchivedUserPermanentError(
            "Account is permanently non-restorable under institutional policy decision ISS-SA-004."
        )
    if not archived_at:
        raise ArchivedUserPermanentError("Archival timestamp is missing.")
    now = current_time or datetime.now()
    days_elapsed = (now - archived_at).total_seconds() / 86400.0
    if days_elapsed > reversible_window_days:
        raise ArchivedUserPermanentError(
            f"Reversible window ({reversible_window_days} days) has expired (elapsed: {int(days_elapsed)} days). Restoration is permanently rejected."
        )


# BR-SA-007: Singular Role Occupancy
def validate_singular_role_occupancy(
    is_singular: bool,
    scope_key: str,
    active_holders_for_scope: Sequence[int],
    target_user_id: int,
) -> None:
    if not is_singular:
        return
    # If there is already an active holder who is NOT the target user
    other_holders = [uid for uid in active_holders_for_scope if uid != target_user_id]
    if other_holders:
        raise SingularRoleOccupancyError(
            f"Singular role already has an active holder (user {other_holders[0]}) for scope '{scope_key}'."
        )


# BR-SA-008: Role Assignment Dating
def validate_role_dates(start_date: date, end_date: date | None, is_time_bound: bool = True) -> None:
    if not start_date:
        raise InvalidRoleDatesError("Role assignment requires a valid start date.")
    if is_time_bound:
        if not end_date:
            raise InvalidRoleDatesError("Time-bound role assignment requires an end date.")
        if end_date <= start_date:
            raise InvalidRoleDatesError(
                f"Role end date ({end_date}) must be strictly after start date ({start_date})."
            )


# BR-SA-010: Role User-Type Eligibility
def validate_role_user_type_eligibility(
    allowed_types: Sequence[BasicUserType | str],
    user_type: BasicUserType | str,
) -> None:
    allowed_set = {
        BasicUserType(t) if isinstance(t, str) else t for t in allowed_types
    }
    u_type = BasicUserType(user_type) if isinstance(user_type, str) else user_type
    if u_type not in allowed_set:
        allowed_str = ", ".join(t.value for t in allowed_set)
        raise RoleIncompatibleUserTypeError(
            f"User type '{u_type.value}' is not eligible for this role (allowed: {allowed_str})."
        )


# BR-SA-011: Role Conflict Validation
def validate_role_conflicts(
    existing_role_codes: Sequence[str],
    candidate_conflict_codes: Sequence[str],
) -> None:
    existing_set = set(existing_role_codes)
    conflicts = existing_set.intersection(candidate_conflict_codes)
    if conflicts:
        raise RoleConflictError(
            f"Role assignment conflicts with existing assigned role(s): {', '.join(conflicts)}."
        )


# BR-SA-014: Role Revocation Handling
def validate_role_revocation(
    effective_date: date,
    is_emergency: bool,
    reason: str,
    pending_task_disposition: PendingTaskDisposition | str,
    today: date | None = None,
) -> None:
    if not reason or not reason.strip():
        raise SystemAdminDomainError("Mandatory reason required for role revocation.")
    current_date = today or date.today()
    if not is_emergency:
        # Standard revocation requires at least 1 day advance notice
        if effective_date <= current_date:
            raise InvalidNoticePeriodError(
                f"Standard revocation requires at least 1 day advance notice (effective: {effective_date}, today: {current_date})."
            )


# BR-SA-016: Role Extension Validation
def validate_role_extension(
    current_end_date: date | None,
    new_end_date: date,
    reason: str,
) -> None:
    if not reason or not reason.strip():
        raise SystemAdminDomainError("Reason is mandatory for role validity extension.")
    if not new_end_date:
        raise InvalidRoleDatesError("New end date is required.")
    if current_end_date and new_end_date <= current_end_date:
        raise InvalidRoleDatesError(
            f"New end date ({new_end_date}) must be later than current end date ({current_end_date})."
        )


# BR-SA-017 & BR-SA-025: Historical Data Archival Eligibility
def validate_historical_data_archival_eligibility(
    category: str,
    has_pending_actions: bool,
    is_audit_log: bool = False,
) -> None:
    if is_audit_log or category.lower() in ("audit", "audit_log", "super_admin_audit"):
        raise AuditLogArchivalProhibitedError(
            "Audit logs cannot be archived; permanent retention is required by BR-SA-025."
        )
    if has_pending_actions:
        raise HistoricalDataArchivalIneligibleError(
            f"Historical data category '{category}' has pending actions and cannot be archived."
        )


# BR-SA-021: Permanent Purge Eligibility
def validate_permanent_purge_eligibility(
    retention_until: date,
    current_date: date | None = None,
    is_audit_log: bool = False,
) -> None:
    if is_audit_log:
        raise AuditLogArchivalProhibitedError(
            "Audit logs cannot be purged; permanent retention is required by BR-SA-025."
        )
    today = current_date or date.today()
    if today <= retention_until:
        raise PurgeRetentionNotElapsedError(
            f"Retention period has not elapsed (retained until {retention_until}, current date {today})."
        )


# BR-SA-026: Super Admin Data Isolation Boundary
def validate_super_admin_data_isolation(resource_name: str) -> None:
    if resource_name.lower() in PROHIBITED_OPERATIONAL_RESOURCES:
        raise OperationalContentAccessForbiddenError(
            f"Access to operational resource '{resource_name}' is strictly forbidden for Super Admin."
        )


# BR-SA-027: Password Policy & Session Controls
def validate_strong_password(password: str) -> None:
    if len(password) < 12:
        raise SystemAdminDomainError("Password must be at least 12 characters long.")
    if not re.search(r"[A-Z]", password):
        raise SystemAdminDomainError("Password must include at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise SystemAdminDomainError("Password must include at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        raise SystemAdminDomainError("Password must include at least one digit.")
    if not re.search(r"[\W_]", password):
        raise SystemAdminDomainError("Password must include at least one special symbol.")


# BR-SA-028: No Self-Modification of Super Admin Status
def validate_no_self_super_admin_modification(
    actor_user_id: int,
    target_user_id: int,
    role_code: str,
) -> None:
    if role_code.lower() in ("super_admin", "sysadmin", "system_administrator"):
        raise SuperAdminSelfModificationForbiddenError(
            "Super Admin role assignment is external (IT team procedure) and cannot be modified inside the module."
        )
    if actor_user_id == target_user_id and "admin" in role_code.lower():
        raise SuperAdminSelfModificationForbiddenError(
            "Super Admin cannot self-assign or modify administrative roles on their own account."
        )


# BR-SA-029: Critical Operation Reauthentication
def validate_critical_operation_reauth(
    is_critical: bool,
    reauthenticated: bool,
    operation_name: str = "This operation",
) -> None:
    if is_critical and not reauthenticated:
        raise CriticalOperationReauthRequiredError(
            f"{operation_name} is designated critical and requires authenticated confirmation."
        )


# BR-SA-030: Bulk Operation Limit
def validate_bulk_operation_limit(count: int, limit: int = 1000) -> None:
    if count <= 0:
        raise SystemAdminDomainError("Bulk operation cannot be empty.")
    if count > limit:
        raise BulkLimitExceededError(
            f"Bulk operation contains {count} records, exceeding maximum limit of {limit}."
        )


# BR-SA-034: Active Role Selection
def validate_active_role_selection(
    assigned_active_role_codes: Sequence[str],
    selected_role_code: str,
) -> None:
    if selected_role_code not in assigned_active_role_codes:
        raise ActiveRoleInvalidError(
            f"Selected role '{selected_role_code}' is not currently active and assigned to the user."
        )


# BR-SA-035: Permitted System Configuration Boundary
def validate_permitted_system_configuration(config_keys: Sequence[str]) -> None:
    disallowed = [k for k in config_keys if k not in PERMITTED_CONFIG_KEYS]
    if disallowed:
        raise PermittedConfigBoundaryError(
            f"The following configuration keys are outside the permitted administrative boundary: {', '.join(disallowed)}."
        )
