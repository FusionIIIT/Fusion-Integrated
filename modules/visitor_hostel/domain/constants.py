from enum import Enum, unique

@unique
class VisitorCategory(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

@unique
class BillingResponsibility(str, Enum):
    VISITOR = "Visitor"
    INDENTER = "Indenter"
    INSTITUTE = "Institute"
    PROJECT = "Project"
    
    @staticmethod
    def normalize(value: str) -> 'BillingResponsibility':
        if value == 'Intender':
            return BillingResponsibility.INDENTER
        elif value == 'ProjectNo':
            return BillingResponsibility.PROJECT
        else:
            return BillingResponsibility(value)

@unique
class RoomType(str, Enum):
    SINGLE = "Single"
    DOUBLE = "Double"
    SUITE = "Suite"
    NON_SUITE = "Non-suite"

@unique
class BookingStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    FORWARDED = "FORWARDED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ROOM_ALLOTTED = "ROOM_ALLOTTED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    CANCELLED = "CANCELLED"

@unique
class BookingEvent(str, Enum):
    SUBMIT = "SUBMIT"
    CARETAKER_REJECT = "CARETAKER_REJECT"
    CARETAKER_FORWARD = "CARETAKER_FORWARD"
    INCHARGE_APPROVE = "INCHARGE_APPROVE"
    INCHARGE_REJECT = "INCHARGE_REJECT"
    ALLOT_ROOM = "ALLOT_ROOM"
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"
    REQUEST_CANCEL = "REQUEST_CANCEL"
    CONFIRM_CANCEL = "CONFIRM_CANCEL"

@unique
class VHRole(str, Enum):
    CARETAKER = "Caretaker"
    VH_INCHARGE = "VH In-Charge"

@unique
class StayExceptionType(str, Enum):
    NO_SHOW = "No-Show"
    OVERSTAY = "Overstay"
