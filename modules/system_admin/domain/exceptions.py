"""Pure Python domain exceptions for modules.system_admin.

Free of external dependencies (strictly NO Django, DRF, or Celery).
Traceability: CFR-SA-001..016, BR-SA-001..035, CW-SA-01..03, ISS-SA-004.
"""
from typing import Tuple


class DomainError(Exception):
    """Base domain exception with message and machine-readable code."""

    def __init__(self, message: str, code: str = "domain_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidStateTransitionError(DomainError):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_state: str, action: str, target: str) -> None:
        super().__init__(
            f"Transition '{action}' is invalid from state '{from_state}' for target '{target}'.",
            code="invalid_state_transition",
        )
        self.from_state = from_state
        self.action = action
        self.target = target


class IdentityValidationError(DomainError):
    """Raised when user identity validation fails."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Identity validation failed: {reason}", code="identity_invalid")
        self.reason = reason


class ImmutabilityViolationError(DomainError):
    """Raised when modification of an immutable field is attempted."""

    def __init__(self, field_name: str) -> None:
        super().__init__(f"Field '{field_name}' is immutable once created.", code="immutable_violation")
        self.field_name = field_name


class RoleConflictError(DomainError):
    """Raised when assigning a role conflicts with another active assignment."""

    def __init__(self, role_a: str, role_b: str, reason: str) -> None:
        super().__init__(
            f"Role assignment conflict between '{role_a}' and '{role_b}': {reason}",
            code="role_conflict",
        )
        self.role_a = role_a
        self.role_b = role_b
        self.reason = reason


class SingularRoleOccupiedError(DomainError):
    """Raised when assigning a singular role that is already held in the scope."""

    def __init__(self, role_code: str, scope: str, current_holder_id: int) -> None:
        super().__init__(
            f"Singular role '{role_code}' in scope '{scope}' is already held by user {current_holder_id}.",
            code="singular_role_occupied",
        )
        self.role_code = role_code
        self.scope = scope
        self.current_holder_id = current_holder_id


class IneligibleRoleUserTypeError(DomainError):
    """Raised when user kind cannot hold the requested role."""

    def __init__(self, role_code: str, user_kind: str, allowed_kinds: Tuple[str, ...]) -> None:
        super().__init__(
            f"User type '{user_kind}' cannot hold role '{role_code}'. Allowed types: {allowed_kinds}.",
            code="role_user_type_ineligible",
        )
        self.role_code = role_code
        self.user_kind = user_kind
        self.allowed_kinds = allowed_kinds


class ArchivalIneligibleError(DomainError):
    """Raised when a user is not eligible for archival."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"User is not eligible for archival: {reason}", code="archival_ineligible")
        self.reason = reason


class ReversibilityExpiredError(DomainError):
    """Raised when trying to restore an archived user whose reversibility window has expired."""

    def __init__(self, expired_at: str) -> None:
        super().__init__(
            f"Archived user reversibility period expired at {expired_at}. Account is permanently non-restorable (ISS-SA-004).",
            code="reversibility_expired",
        )
        self.expired_at = expired_at


class PurgeDualAuthRequiredError(DomainError):
    """Raised when permanent purge lacks required dual authorization."""

    def __init__(self, missing_actor: str) -> None:
        super().__init__(
            f"Permanent purge requires dual authorization. Missing authorization from: {missing_actor}.",
            code="purge_dual_auth_required",
        )
        self.missing_actor = missing_actor


class SelfModificationForbiddenError(DomainError):
    """Raised when a super admin attempts to self-assign or modify super admin privileges."""

    def __init__(self) -> None:
        super().__init__(
            "Super Admin status cannot be self-assigned or modified (BR-SA-028).",
            code="self_modification_forbidden",
        )


class ConfigurationBoundaryViolationError(DomainError):
    """Raised when attempting to modify a parameter outside the allowed whitelist."""

    def __init__(self, attempted_param: str) -> None:
        super().__init__(
            f"Parameter '{attempted_param}' is outside the Super Admin configuration boundary (BR-SA-035).",
            code="config_boundary_violation",
        )
        self.attempted_param = attempted_param


class BulkLimitExceededError(DomainError):
    """Raised when a bulk operation contains more records than the allowed limit."""

    def __init__(self, count: int, max_limit: int = 1000) -> None:
        super().__init__(
            f"Bulk operation contains {count} records, which exceeds the limit of {max_limit} (BR-SA-030).",
            code="bulk_limit_exceeded",
        )
        self.count = count
        self.max_limit = max_limit
