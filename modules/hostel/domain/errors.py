"""Hostel Management domain exceptions (pure Python, zero dependencies)."""


class HostelDomainError(Exception):
    """Base domain exception for Hostel Management."""


class CapacityExceededError(HostelDomainError):
    """Enforces BR-HM-010: room occupancy must not exceed defined capacity."""


class RoomNotAvailableError(HostelDomainError):
    """Raised when an operation requires an available room that cannot accept occupancy."""


class InvalidStateTransitionError(HostelDomainError):
    """Raised when an invalid state transition is attempted on a workflow entity."""


class MandatoryFieldMissingError(HostelDomainError):
    """Enforces BR-HM-025, BR-HM-015: mandatory fields required by business rules."""


class UnauthorizedHostelAccessError(HostelDomainError):
    """Enforces BR-HM-002, BR-HM-005, BR-HM-035: hostel or shift context boundary violations."""


class NoticePermissionError(HostelDomainError):
    """Enforces BR-HM-029: notices may only be published for assigned hostels."""


class ScopeBoundaryError(HostelDomainError):
    """Enforces BR-HM-016, BR-HM-028: actions outside HM scope boundaries."""
