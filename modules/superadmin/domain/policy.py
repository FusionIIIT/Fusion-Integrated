"""Pure Python domain policies for Super Admin."""
from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date, datetime, timedelta

INSTITUTE_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@(iiitdmj\.ac\.in|[a-zA-Z0-9-]+\.iiitdmj\.ac\.in)$"
)
SINGULAR_ROLES = {"DEAN_ACADEMICS", "DEAN_STUDENTS", "HOD_CSE", "CONVENER_PLACEMENT"}


class DomainValidationError(Exception):
    """Raised when a business rule constraint is violated."""


def validate_institute_email(email: str) -> None:
    """Validate institute email per BR-SA-002."""
    if not email or not INSTITUTE_EMAIL_REGEX.match(email.strip().lower()):
        raise DomainValidationError(f"BR-SA-002: Invalid institute email '{email}'.")


def validate_archival_eligibility(
    status: str,
    deactivated_at: datetime | None,
    now: datetime,
    min_days: int = 30,
) -> None:
    """Verify eligibility for user archival per BR-SA-004."""
    if status != "DEACTIVATED":
        raise DomainValidationError(
            f"BR-SA-004: Only DEACTIVATED users can be archived (status: {status})."
        )
    if deactivated_at is None or (now - deactivated_at) < timedelta(days=min_days):
        raise DomainValidationError(
            f"BR-SA-004: Minimum deactivation interval ({min_days} days) not met."
        )


def calculate_reversible_window(archived_at: datetime, window_days: int = 90) -> datetime:
    """Calculate reversible expiry date per BR-SA-005."""
    return archived_at + timedelta(days=window_days)


def validate_archived_user_restoration(
    status: str,
    reversible_until: datetime | None,
    now: datetime,
) -> None:
    """Verify restoration eligibility per BR-SA-005."""
    if status == "ARCHIVED_PERMANENT":
        raise DomainValidationError("BR-SA-005: Account permanently non-restorable.")
    if status != "ARCHIVED_REVERSIBLE" or reversible_until is None or now > reversible_until:
        raise DomainValidationError("BR-SA-005: Reversible window expired.")


def validate_role_dating(start_date: date, end_date: date | None = None) -> None:
    """Validate role assignment dates per BR-SA-008."""
    if not start_date or (end_date and end_date < start_date):
        raise DomainValidationError("BR-SA-008: Invalid role dates.")


def validate_singular_role_occupancy(
    role_code: str,
    scope: str,
    active_scopes: Sequence[str],
) -> None:
    """Enforce singular role constraint per BR-SA-007."""
    if role_code in SINGULAR_ROLES and scope in active_scopes:
        raise DomainValidationError(f"BR-SA-007: Singular role '{role_code}' already active.")


def validate_role_revocation(reason: str) -> None:
    """Validate revocation reason per BR-SA-014."""
    if not reason or not reason.strip():
        raise DomainValidationError("BR-SA-014: Reason required for role revocation.")
