from __future__ import annotations


class DomainError(Exception):
    def __init__(self, message: str, code: str = "domain_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidStateTransitionError(DomainError):
    def __init__(self, from_state: str, action: str, target: str) -> None:
        super().__init__(
            f"Transition '{action}' is invalid from state '{from_state}' for target '{target}'. "
            "Verify the current status and choose an allowed action.",
            code="invalid_state_transition",
        )


class IdentityValidationError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Identity validation failed: {reason}. "
            "Check the principal identifier format and try again.",
            code="identity_invalid",
        )


class ImmutabilityViolationError(DomainError):
    def __init__(self, field_name: str) -> None:
        super().__init__(
            f"Field '{field_name}' is immutable once created. "
            "Create a new record instead of modifying immutable audit entries.",
            code="immutable_violation",
        )


class ArchivalIneligibleError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            f"User is not eligible for archival: {reason}. "
            "Resolve pending obligations or wait for eligibility before retrying.",
            code="archival_ineligible",
        )


class ReversibilityExpiredError(DomainError):
    def __init__(self, expired_at: str) -> None:
        super().__init__(
            f"Archived user reversibility period expired at {expired_at}. "
            "Create a new user profile if access must be re-granted.",
            code="reversibility_expired",
        )


class PurgeDualAuthRequiredError(DomainError):
    def __init__(self, missing_actor: str) -> None:
        super().__init__(
            "Permanent purge requires dual authorization. "
            f"Obtain authorization from {missing_actor} before executing purge.",
            code="purge_dual_auth_required",
        )


class SelfApprovalForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Initiating Super Admin cannot authorize their own purge request. "
            "Have an independent IT Head review and decide this request.",
            code="self_approval_forbidden",
        )


class SelfModificationForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Super Admin status cannot be self-assigned or modified (BR-SA-028). "
            "Contact the institutional IAM administrator to update administrative privileges.",
            code="self_modification_forbidden",
        )


class ConfigurationBoundaryViolationError(DomainError):
    def __init__(self, attempted_param: str) -> None:
        super().__init__(
            f"Parameter '{attempted_param}' is outside configuration boundary (BR-SA-035). "
            "Verify the parameter key against the supported governance parameter whitelist.",
            code="config_boundary_violation",
        )


class BulkLimitExceededError(DomainError):
    def __init__(self, count: int, max_limit: int = 1000) -> None:
        super().__init__(
            f"Bulk operation contains {count} records, exceeding limit of {max_limit} (BR-SA-030). "
            f"Split the dataset into smaller batches of at most {max_limit} records.",
            code="bulk_limit_exceeded",
        )
