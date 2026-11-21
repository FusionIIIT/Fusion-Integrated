from __future__ import annotations


class DomainError(Exception):
    def __init__(self, message: str, code: str = "domain_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidStateTransitionError(DomainError):
    def __init__(self, from_state: str, action: str, target: str) -> None:
        super().__init__(
            f"Transition '{action}' is invalid from state '{from_state}' for target '{target}'.",
            code="invalid_state_transition",
        )


class IdentityValidationError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Identity validation failed: {reason}", code="identity_invalid")


class ImmutabilityViolationError(DomainError):
    def __init__(self, field_name: str) -> None:
        super().__init__(
            f"Field '{field_name}' is immutable once created.", code="immutable_violation"
        )


class ArchivalIneligibleError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"User is not eligible for archival: {reason}", code="archival_ineligible")


class ReversibilityExpiredError(DomainError):
    def __init__(self, expired_at: str) -> None:
        super().__init__(
            f"Archived user reversibility period expired at {expired_at}. "
            "Account is permanently non-restorable.",
            code="reversibility_expired",
        )


class PurgeDualAuthRequiredError(DomainError):
    def __init__(self, missing_actor: str) -> None:
        super().__init__(
            "Permanent purge requires dual authorization. "
            f"Missing authorization from: {missing_actor}.",
            code="purge_dual_auth_required",
        )


class SelfApprovalForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Initiating Super Admin cannot authorize their own purge request "
            "(dual authorization rule).",
            code="self_approval_forbidden",
        )


class SelfModificationForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Super Admin status cannot be self-assigned or modified (BR-SA-028).",
            code="self_modification_forbidden",
        )


class ConfigurationBoundaryViolationError(DomainError):
    def __init__(self, attempted_param: str) -> None:
        super().__init__(
            f"Parameter '{attempted_param}' is outside the Super Admin "
            "configuration boundary (BR-SA-035).",
            code="config_boundary_violation",
        )


class BulkLimitExceededError(DomainError):
    def __init__(self, count: int, max_limit: int = 1000) -> None:
        super().__init__(
            f"Bulk operation contains {count} records, which exceeds the limit "
            f"of {max_limit} (BR-SA-030).",
            code="bulk_limit_exceeded",
        )
