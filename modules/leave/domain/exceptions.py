"""Domain exceptions for Employee Leave Management.

Pure Python exceptions — never import core.api.exceptions or Django here.
"""


class LeaveDomainError(Exception):
    def __init__(self, message: str, code: str = "leave_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidStateTransitionError(LeaveDomainError):
    def __init__(self, message: str = "This action cannot be performed in the current state."):
        super().__init__(message, code="invalid_state_transition")


class InsufficientBalanceError(LeaveDomainError):
    def __init__(self, message: str = "Insufficient leave balance."):
        super().__init__(message, code="insufficient_balance")


class LeaveOverlapError(LeaveDomainError):
    def __init__(
        self, message: str = "Requested period overlaps with an existing leave or substitution."
    ):
        super().__init__(message, code="leave_overlap")


class InvalidSubstituteError(LeaveDomainError):
    def __init__(self, message: str = "Nominated substitute is not eligible."):
        super().__init__(message, code="invalid_substitute")


class PolicyViolationError(LeaveDomainError):
    def __init__(self, message: str = "Request violates leave policy."):
        super().__init__(message, code="policy_violation")


class UnauthorizedActionError(LeaveDomainError):
    def __init__(self, message: str = "You are not authorized to perform this transition."):
        super().__init__(message, code="unauthorized_action")
