class VHDomainError(Exception):
    """Base domain exception"""
    pass


class InvalidBookingStateError(VHDomainError):
    """Raised when an illegal state transition is attempted"""
    pass


class RoomNotAvailableError(VHDomainError):
    """Raised when a room is not available for requested dates"""
    pass


class UnauthorizedRoleError(VHDomainError):
    """Raised when an actor attempts an unauthorized action"""
    pass


class InvalidCancellationError(VHDomainError):
    """Raised on illegal cancellation attempts"""
    pass


class TariffNotFoundError(VHDomainError):
    """Raised when no active tariff matches category/room_type"""
    pass


class InventoryThresholdExceededError(VHDomainError):
    """Raised when inventory drops below threshold"""
    pass
