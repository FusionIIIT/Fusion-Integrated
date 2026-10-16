from datetime import date
from decimal import Decimal

class ELMDomainError(Exception):
    """Base class for all ELM domain errors."""
    pass

class InvalidDateRangeError(ELMDomainError):
    """Error raised when the date range is invalid."""
    def __init__(self, start_date: date, end_date: date):
        self.start_date = start_date
        self.end_date = end_date
        super().__init__(f"Invalid date range: {start_date} to {end_date}")

class IneligibleCategoryError(ELMDomainError):
    """Error raised when the leave category is ineligible."""
    def __init__(self, category: str):
        self.category = category
        super().__init__(f"Category {category} is ineligible for leave.")

class InsufficientBalanceError(ELMDomainError):
    """Error raised when the leave balance is insufficient."""
    def __init__(self, balance: int | Decimal, required: int | Decimal):
        self.balance = balance
        self.required = required
        super().__init__(f"Insufficient leave balance: {balance} available, {required} required.")

class OverlappingLeaveError(ELMDomainError):
    """Error raised when the leave request overlaps with an existing leave request."""
    def __init__(self, request: object):
        self.request = request
        super().__init__(f"Leave request overlaps with existing request: {request}")

class InvalidWorkflowTransitionError(ELMDomainError):
    """Error raised when an invalid workflow transition is attempted."""
    def __init__(self, current_state: str, target_state: str):
        self.current_state = current_state
        self.target_state = target_state
        super().__init__(f"Invalid workflow transition: {current_state} -> {target_state}")
