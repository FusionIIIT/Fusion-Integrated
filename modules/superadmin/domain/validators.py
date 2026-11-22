"""Domain validators for Super Admin."""

import re
from datetime import datetime

from modules.superadmin.domain.exceptions import DomainValidationError


def validate_institute_email(
    email: str, allowed_domains: tuple[str, ...] = ("iiitdmj.ac.in",)
) -> None:
    # BR-SA-002: Accept only valid institute email addresses.
    if not email or "@" not in email:
        raise DomainValidationError("A valid email address is required.")
    parts = email.strip().split("@")
    if len(parts) != 2:
        raise DomainValidationError("Invalid email format.")
    domain = parts[1].lower()
    if not any(domain == d or domain.endswith("." + d) for d in allowed_domains):
        raise DomainValidationError(
            f"Email domain '@{domain}' is not an authorized institute domain."
        )


def validate_institute_id(institute_id: str) -> None:
    # BR-SA-001: Validate non-empty format of institute identifier.
    if not institute_id or not institute_id.strip():
        raise DomainValidationError("Institute ID cannot be blank.")
    if not re.match(r"^[A-Za-z0-9_-]{3,32}$", institute_id.strip()):
        raise DomainValidationError("Institute ID must be 3-32 alphanumeric characters.")


def validate_user_type_data(user_type: str, department: str, program: str, batch: str) -> None:
    # BR-SA-003: User-type specific data requirements.
    user_type_upper = user_type.upper()
    if user_type_upper not in ("STUDENT", "FACULTY", "STAFF"):
        raise DomainValidationError(f"Unknown user type: {user_type}")
    if user_type_upper == "STUDENT":
        if not program or not program.strip():
            raise DomainValidationError("Students must have program information.")
        if not batch or not batch.strip():
            raise DomainValidationError("Students must have batch information.")
    elif user_type_upper in ("FACULTY", "STAFF"):
        if not department or not department.strip():
            raise DomainValidationError(
                f"{user_type_upper.capitalize()} must have department information."
            )


def validate_role_dates(valid_from: datetime, valid_to: datetime | None) -> None:
    # BR-SA-008: Role assignment validity dates.
    if valid_to and valid_to <= valid_from:
        raise DomainValidationError("Role validity end date must be strictly after start date.")


def validate_batch_size(record_count: int, max_limit: int = 500) -> None:
    # BR-SA-030: Bulk operation maximum batch size check.
    if record_count <= 0:
        raise DomainValidationError("Batch contains no records.")
    if record_count > max_limit:
        raise DomainValidationError(
            f"Batch size {record_count} exceeds maximum allowed limit of {max_limit}."
        )


def validate_user_id(user_id: int) -> None:
    if not isinstance(user_id, int) or user_id <= 0:
        raise DomainValidationError("user_id must be a positive integer.")


def validate_retention_period_days(days: int) -> None:
    if not isinstance(days, int) or days < 365:
        raise DomainValidationError("Retention period must be at least 365 days.")


validate_role_validity_dates = validate_role_dates
