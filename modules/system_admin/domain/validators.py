"""Pure Python validation functions for modules.system_admin.

Enforces institutional identity rules, role occupancy constraints,
revocation rules, bulk size limits, and configuration boundary rules.
Free of external dependencies (strictly NO Django, DRF, or Celery).
Traceability: BR-SA-001..003, BR-SA-007..010, BR-SA-014, BR-SA-030, BR-SA-035.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional, Set, Tuple, Union, AbstractSet

from .dataclasses import UserCreationSpec
from .exceptions import (
    BulkLimitExceededError,
    ConfigurationBoundaryViolationError,
    DomainError,
    IdentityValidationError,
    IneligibleRoleUserTypeError,
    SingularRoleOccupiedError,
)

INSTITUTE_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.)*iiitdmj\.ac\.in$")
INSTITUTE_ID_REGEX = re.compile(r"^[A-Z0-9/_-]{3,20}$")

DEFAULT_PERMITTED_CONFIG_KEYS: frozenset[str] = frozenset({
    "password.min_length",
    "password.complexity_required",
    "password.rotation_days",
    "session.inactivity_timeout_minutes",
    "archival.min_deactivation_days",
    "archival.reversible_window_days",
    "archival.historical_retention_years",
    "role.expiry_reminder_lead_days",
    "role.previous_holder_audit_days",
    "notification.enable_sms_alerts",
    "bulk.max_records",
})


def validate_institute_id(institute_id: str) -> None:
    """BR-SA-001: Institute ID must be non-empty and match institutional pattern."""
    if not institute_id or not INSTITUTE_ID_REGEX.match(institute_id.strip()):
        raise IdentityValidationError("Invalid Institute ID format.")


def validate_institute_email(email: str) -> None:
    """BR-SA-002: Only valid institute email addresses allowed."""
    if not email or not INSTITUTE_EMAIL_REGEX.match(email.strip().lower()):
        raise IdentityValidationError("Email must be a valid '@iiitdmj.ac.in' address.")


def validate_user_type_required_data(spec: UserCreationSpec) -> None:
    """BR-SA-003: Student requires program/batch; Faculty/Staff requires employee_id/dept."""
    validate_institute_id(spec.institute_id)
    validate_institute_email(spec.institute_email)
    if not spec.name or not spec.name.strip():
        raise IdentityValidationError("Full name is required.")

    if spec.user_kind == "student":
        if not spec.programme or not spec.batch_year:
            raise IdentityValidationError("Student requires programme and batch year.")
    elif spec.user_kind in {"faculty", "staff"}:
        if not spec.department or not spec.employee_id:
            raise IdentityValidationError(f"{spec.user_kind.capitalize()} requires department and employee ID.")
    else:
        raise IdentityValidationError(f"Unknown user kind: {spec.user_kind}")


def validate_role_eligibility(role_code: str, user_kind: str, allowed_kinds: Tuple[str, ...]) -> None:
    """BR-SA-010: Validates user type eligibility for role."""
    if user_kind not in allowed_kinds:
        raise IneligibleRoleUserTypeError(role_code, user_kind, allowed_kinds)


def validate_singular_occupancy(
    role_code: str,
    scope: str,
    current_holder_id: Optional[int],
    new_user_id: int,
) -> None:
    """BR-SA-007: Singular role may have only one active holder per scope."""
    if current_holder_id is not None and current_holder_id != new_user_id:
        raise SingularRoleOccupiedError(role_code, scope, current_holder_id)


def validate_role_dating(
    start_date: date,
    is_time_bound: bool,
    end_date: Optional[date],
) -> None:
    """BR-SA-008: Start date mandatory; end date required if time-bound."""
    if not start_date:
        raise DomainError("Role assignment requires a start date.", code="missing_start_date")
    if is_time_bound:
        if not end_date:
            raise DomainError("Time-bound role requires an end date.", code="missing_end_date")
        if end_date <= start_date:
            raise DomainError("End date must be strictly after start date.", code="invalid_date_range")


def validate_revocation_notice(
    is_emergency: bool,
    notice_date: date,
    effective_date: date,
) -> None:
    """BR-SA-014: Standard revocation requires >= 1 day notice; emergency is immediate."""
    if not is_emergency:
        min_effective = notice_date + timedelta(days=1)
        if effective_date < min_effective:
            raise DomainError(
                "Standard role revocation requires at least 1 day advance notice.",
                code="insufficient_revocation_notice",
            )


def validate_bulk_size(records_count: int, max_limit: int = 1000) -> None:
    """BR-SA-030: Bulk operations limited to 1000 records."""
    if records_count <= 0:
        raise DomainError("Bulk operation cannot be empty.", code="bulk_empty")
    if records_count > max_limit:
        raise BulkLimitExceededError(records_count, max_limit)


def validate_configuration_key(param_key: str, permitted_keys: Union[Set[str], AbstractSet[str]]) -> None:
    """BR-SA-035: Configuration changes limited to permitted parameter whitelist."""
    if param_key not in permitted_keys:
        raise ConfigurationBoundaryViolationError(param_key)
