"""Domain exceptions for Employee Leave Management."""


class ElmDomainError(Exception):
    """Base class for domain errors in ELM."""


class InvalidLeaveCategoryError(ElmDomainError):
    pass


class InsufficientBalanceError(ElmDomainError):
    pass


class OverlappingLeaveError(ElmDomainError):
    pass


class InvalidSubstituteError(ElmDomainError):
    pass


class InvalidDateRangeError(ElmDomainError):
    pass


class InvalidStateTransitionError(ElmDomainError):
    pass


class VacationPeriodMismatchError(ElmDomainError):
    pass


class RestrictedHolidayMismatchError(ElmDomainError):
    pass
