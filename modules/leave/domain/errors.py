"""Pure Python domain errors."""


class LeaveDomainError(Exception):
    def __init__(self, message: str, code: str = "leave_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class IneligibleCategoryError(LeaveDomainError):
    def __init__(self, message: str = "The requested leave category is not admissible."):
        super().__init__(message, code="ineligible_category")


class InsufficientBalanceError(LeaveDomainError):
    def __init__(self, message: str = "Insufficient leave balance."):
        super().__init__(message, code="insufficient_balance")


class OverlappingLeaveError(LeaveDomainError):
    def __init__(self, message: str = "The requested period overlaps with active leave."):
        super().__init__(message, code="overlapping_leave")


class IneligibleSubstituteError(LeaveDomainError):
    def __init__(self, message: str = "The nominated substitute is ineligible."):
        super().__init__(message, code="ineligible_substitute")


class InvalidLeaveTransitionError(LeaveDomainError):
    def __init__(self, message: str = "Illegal transition."):
        super().__init__(message, code="invalid_transition")


class LeavePolicyViolationError(LeaveDomainError):
    def __init__(self, message: str = "The request violates leave policy constraints."):
        super().__init__(message, code="policy_violation")
