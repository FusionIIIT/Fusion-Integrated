"""Pure Python domain errors (no Django/DRF dependencies)."""


class DomainError(Exception):
    def __init__(self, message: str, code: str = "domain_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class InsufficientBalanceError(DomainError):
    def __init__(self, message: str = "Insufficient leave balance."):
        super().__init__(message, code="insufficient_balance")


class InvalidDateRangeError(DomainError):
    def __init__(self, message: str = "End date cannot be earlier than start date."):
        super().__init__(message, code="invalid_date_range")


class OverlappingLeaveError(DomainError):
    def __init__(self, message: str = "Requested period overlaps with an existing leave request."):
        super().__init__(message, code="overlapping_leave")


class IneligibleSubstituteError(DomainError):
    def __init__(self, message: str = "Nominated substitute is ineligible."):
        super().__init__(message, code="ineligible_substitute")


class InvalidStateTransitionError(DomainError):
    def __init__(self, message: str = "Action cannot be performed on leave in this status."):
        super().__init__(message, code="invalid_state_transition")


class VacationCalendarMismatchError(DomainError):
    def __init__(
        self,
        message: str = (
            "Vacation Leave (VL) can only be availed during published academic vacation periods."
        ),
    ):
        super().__init__(message, code="vacation_mismatch")


class RestrictedHolidayMismatchError(DomainError):
    def __init__(
        self,
        message: str = ("Restricted Holiday (RH) must match a published restricted holiday date."),
    ):
        super().__init__(message, code="restricted_holiday_mismatch")
