"""Domain exceptions for Hostel Management."""


class HostelDomainError(Exception):
    """Base domain error for hostel operations."""
    def __init__(self, message: str, code: str = "hostel_domain_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class RoomCapacityExceededError(HostelDomainError):
    def __init__(self, room_number: str, capacity: int, current_occupancy: int):
        super().__init__(
            f"Room {room_number} capacity ({capacity}) exceeded. Current occupancy is {current_occupancy}.",
            code="room_capacity_exceeded"
        )


class InactiveHostelError(HostelDomainError):
    def __init__(self, hostel_name: str):
        super().__init__(
            f"Hostel {hostel_name} is inactive. Operations are restricted.",
            code="inactive_hostel"
        )


class UnauthorizedHostelAccessError(HostelDomainError):
    def __init__(self, user_id: int, hostel_id: int):
        super().__init__(
            f"User {user_id} is not authorized for operations in hostel {hostel_id}.",
            code="unauthorized_hostel_access"
        )


class InvalidStateTransitionError(HostelDomainError):
    def __init__(self, workflow: str, from_state: str, to_state: str):
        super().__init__(
            f"Invalid transition in {workflow}: cannot move from '{from_state}' to '{to_state}'.",
            code="invalid_state_transition"
        )


class DuplicateActiveAllotmentError(HostelDomainError):
    def __init__(self, student_user_id: int):
        super().__init__(
            f"Student {student_user_id} already has an active room allotment.",
            code="duplicate_active_allotment"
        )


class MandatoryFieldError(HostelDomainError):
    def __init__(self, field_name: str, rule: str):
        super().__init__(
            f"Field '{field_name}' is mandatory under rule {rule}.",
            code="mandatory_field_missing"
        )
