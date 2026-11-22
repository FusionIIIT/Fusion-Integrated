"""Pure domain validation rules (BR-SA-001 through BR-SA-035)."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta

from modules.system_admin.domain.exceptions import (
    ArchivalReversibilityExpiredError,
    DomainValidationError,
    IneligibleUserTypeError,
    InvalidDateRangeError,
    InvalidEmailDomainError,
    ParameterOutOfBoundsError,
    RetentionNotElapsedError,
    SeparationOfDutiesConflictError,
    SingularRoleOccupancyError,
    UserNotEligibleForArchivalError,
)
from modules.system_admin.domain.models import UserIdentity

ALLOWED_INSTITUTE_DOMAINS = ("@iiitdmj.ac.in", "@fusion.edu")

# Role eligibility: which user types can hold which roles (BR-SA-010)
FACULTY_STAFF_ONLY_ROLES = {
    "dean_academics",
    "dean_students",
    "dean_rnd",
    "hod_cse",
    "hod_ece",
    "hod_me",
    "tpo",
    "warden",
    "finance_officer",
    "internal_auditor",
}

STUDENT_ONLY_ROLES = {
    "student_senator",
    "mess_convener",
    "placement_coordinator",
    "club_coordinator",
}

# Separation of Duties (SOD) Conflict Matrix (BR-SA-011)
SOD_CONFLICT_PAIRS = {
    frozenset(["internal_auditor", "finance_officer"]),
    frozenset(["dean_academics", "hod_cse"]),
    frozenset(["dean_academics", "hod_ece"]),
    frozenset(["dean_academics", "hod_me"]),
}


def validate_institute_id(institute_id: str) -> None:
    """Validate Institute ID format (BR-SA-001)."""
    if not institute_id or not institute_id.strip():
        raise DomainValidationError("Institute ID is mandatory and cannot be blank.")
    if len(institute_id.strip()) > 32:
        raise DomainValidationError("Institute ID exceeds maximum allowed length of 32.")


def validate_institute_email(email: str) -> None:
    """Validate that email belongs to institutional domain (BR-SA-002)."""
    if not email or "@" not in email:
        raise InvalidEmailDomainError("A valid email address is required.")
    email_clean = email.strip().lower()
    if not any(email_clean.endswith(dom) for dom in ALLOWED_INSTITUTE_DOMAINS):
        raise InvalidEmailDomainError(
            f"Email '{email}' is not an authorized institute email (must end with @iiitdmj.ac.in)."
        )


def validate_user_type_data(identity: UserIdentity) -> None:
    """Validate user type specific data constraints (BR-SA-003)."""
    user_type = identity.user_type.lower().strip()
    if user_type not in ("student", "faculty", "staff"):
        raise IneligibleUserTypeError(
            f"Invalid user type '{identity.user_type}'. Must be student, faculty, or staff."
        )

    if user_type == "student":
        if not identity.discipline or not identity.programme:
            raise DomainValidationError("Students must have valid programme and discipline.")
        if identity.batch_year is None:
            raise DomainValidationError("Students must have a valid batch year.")
        if identity.batch_year < 1990:
            raise DomainValidationError("Students must have a valid batch year.")

    if user_type in ("faculty", "staff") and not identity.department:
        raise DomainValidationError(f"{user_type.title()} must have a designated department.")


def validate_role_dates(
    start_date: date,
    end_date: date | None,
    is_time_bound: bool = True,
) -> None:
    """Validate role assignment dates (BR-SA-008)."""
    if not start_date:
        raise InvalidDateRangeError("Role assignment must have a valid start date.")

    if is_time_bound:
        if not end_date:
            raise InvalidDateRangeError("Time-bound role assignments require an explicit end date.")
        if end_date < start_date:
            raise InvalidDateRangeError(
                f"Role end date ({end_date}) cannot precede start date ({start_date})."
            )


def validate_singular_role_occupancy(
    role_code: str,
    is_singular: bool,
    current_active_holders: int,
) -> None:
    """Validate singular role occupancy (BR-SA-007)."""
    if is_singular and current_active_holders > 0:
        raise SingularRoleOccupancyError(
            f"Role '{role_code}' is marked singular and already has an active holder."
        )


def validate_user_type_role_eligibility(user_type: str, role_code: str) -> None:
    """Validate user type eligibility for a given role (BR-SA-010)."""
    ut = user_type.lower().strip()
    role = role_code.lower().strip()

    if ut == "student" and role in FACULTY_STAFF_ONLY_ROLES:
        raise IneligibleUserTypeError(
            f"User of type 'student' is ineligible for faculty/staff role '{role_code}'."
        )
    if ut in ("faculty", "staff") and role in STUDENT_ONLY_ROLES:
        raise IneligibleUserTypeError(
            f"User of type '{user_type}' is ineligible for student-only role '{role_code}'."
        )


def validate_sod_conflicts(new_role: str, active_roles: Sequence[str]) -> None:
    """Validate Separation of Duties (SOD) conflict matrix (BR-SA-011)."""
    new_r = new_role.lower().strip()
    for existing in active_roles:
        pair = frozenset([new_r, existing.lower().strip()])
        if pair in SOD_CONFLICT_PAIRS:
            raise SeparationOfDutiesConflictError(
                f"Conflicting roles: '{new_role}' cannot be held with '{existing}' (SOD policy)."
            )


def validate_archival_eligibility(
    status: str,
    deactivation_date: datetime | None,
    current_time: datetime,
    min_interval_days: int = 30,
    has_pending_transactions: bool = False,
) -> None:
    """Validate user archival eligibility (BR-SA-004)."""
    if status != "deactivated":
        raise UserNotEligibleForArchivalError(
            f"Only deactivated accounts may be archived. Current status: '{status}'."
        )

    if has_pending_transactions:
        raise UserNotEligibleForArchivalError(
            "User has unresolved pending workflow transactions blocking archival."
        )

    if deactivation_date:
        elapsed = (current_time - deactivation_date).days
        if elapsed < min_interval_days:
            raise UserNotEligibleForArchivalError(
                f"Minimum deactivation interval of {min_interval_days} days not met ({elapsed}d)."
            )


def validate_restoration_window(
    is_permanent: bool,
    archived_at: datetime,
    window_days: int,
    current_time: datetime,
) -> None:
    """Validate user restoration reversible window (BR-SA-005, ISS-SA-004)."""
    if is_permanent:
        raise ArchivalReversibilityExpiredError(
            "Account is permanently archived and non-restorable (ISS-SA-004)."
        )

    window_end = archived_at + timedelta(days=window_days)
    if current_time > window_end:
        raise ArchivalReversibilityExpiredError(
            f"Reversible archival period of {window_days} days expired on {window_end.date()}."
        )


def validate_purge_eligibility(
    archived_at: datetime,
    retention_years: int,
    current_time: datetime,
) -> None:
    """Validate permanent purge retention eligibility (BR-SA-021)."""
    min_purge_date = archived_at + timedelta(days=retention_years * 365)
    if current_time < min_purge_date:
        raise RetentionNotElapsedError(
            f"Archival retention period of {retention_years} years not elapsed "
            f"(eligible after {min_purge_date.date()})."
        )


def validate_system_parameters(params: dict) -> None:
    """Validate configuration parameters boundary and policy limits (BR-SA-030, BR-SA-035)."""
    forbidden_keywords = {"financial", "grade", "grading", "academic_calendar", "curriculum"}
    for key, val in params.items():
        if any(fk in key.lower() for fk in forbidden_keywords):
            raise ParameterOutOfBoundsError(
                f"Parameter '{key}' is outside Super Admin authority boundary (BR-SA-035)."
            )

        if key == "bulk_operation_limit" and (not isinstance(val, int) or val < 1 or val > 1000):
            raise ParameterOutOfBoundsError(
                "Bulk operation limit must be between 1 and 1000 (BR-SA-030)."
            )

        if key == "session_timeout_minutes" and (
            not isinstance(val, int) or val < 5 or val > 1440
        ):
            raise ParameterOutOfBoundsError("Session timeout must be between 5 and 1440 minutes.")

        if key == "archival_retention_years" and (
            not isinstance(val, int) or val < 1 or val > 50
        ):
            raise ParameterOutOfBoundsError(
                "Archival retention period must be between 1 and 50 years."
            )
