from __future__ import annotations

import re

from modules.superadmin.domain.exceptions import (
    BulkLimitExceededError,
    ConfigurationBoundaryViolationError,
    DomainError,
    IdentityValidationError,
    SelfModificationForbiddenError,
)

INSTITUTE_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.)*iiitdmj\.ac\.in$")
INSTITUTE_ID_REGEX = re.compile(r"^[A-Z0-9/_-]{3,32}$")


def validate_institute_id(institute_id: str) -> None:
    # BR-SA-001: Institute ID format and non-empty check
    if not institute_id or not INSTITUTE_ID_REGEX.match(institute_id.strip()):
        raise IdentityValidationError("Invalid Institute ID format.")


def validate_institute_email(email: str) -> None:
    # BR-SA-002: Institutional email domain check
    if not email or not INSTITUTE_EMAIL_REGEX.match(email.strip().lower()):
        raise IdentityValidationError("Email must be a valid '@iiitdmj.ac.in' address.")


def validate_bulk_size(records_count: int, max_limit: int = 1000) -> None:
    # BR-SA-030: Bulk operations size limit check
    if records_count <= 0:
        raise DomainError("Bulk operation batch cannot be empty.", code="bulk_empty")
    if records_count > max_limit:
        raise BulkLimitExceededError(records_count, max_limit)


def validate_configuration_key(param_key: str, permitted_keys: frozenset[str]) -> None:
    # BR-SA-035: Permitted parameter whitelist check
    if param_key not in permitted_keys:
        raise ConfigurationBoundaryViolationError(param_key)


def validate_no_self_modification(actor_user_id: int, target_user_id: int) -> None:
    # BR-SA-028: Prevents self-modification of administrative status
    if actor_user_id == target_user_id:
        raise SelfModificationForbiddenError()
