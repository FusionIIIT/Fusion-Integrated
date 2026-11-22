"""Hostel Management domain enumerations (pure Python, zero dependencies)."""

from enum import StrEnum


class HostelGender(StrEnum):
    BOYS = "boys"
    GIRLS = "girls"
    COED = "coed"


class RoleBindingType(StrEnum):
    WARDEN = "warden"
    CARETAKER = "caretaker"


class ShiftType(StrEnum):
    MORNING = "morning"
    EVENING = "evening"
    NIGHT = "night"
    GENERAL = "general"


class RoomStatus(StrEnum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"
    INACTIVE = "inactive"


class RoomType(StrEnum):
    STANDARD = "standard"
    GUEST = "guest"


class AccommodationRequestStatus(StrEnum):
    SUBMITTED = "submitted"
    ALLOTTED = "allotted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AllotmentStatus(StrEnum):
    ACTIVE = "active"
    VACATED = "vacated"
    REALLOTTED = "reallotted"
    EXCHANGED = "exchanged"


class RoomExchangeStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    ON_LEAVE = "on_leave"
    LATE = "late"


class LeaveStatus(StrEnum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveType(StrEnum):
    HOME = "home"
    MEDICAL = "medical"
    ACADEMIC = "academic"
    EMERGENCY = "emergency"
    OTHER = "other"


class ComplaintStatus(StrEnum):
    SUBMITTED = "submitted"
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class ComplaintCategory(StrEnum):
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    CARPENTRY = "carpentry"
    CLEANLINESS = "cleanliness"
    WIFI_INTERNET = "wifi_internet"
    DISCIPLINE = "discipline"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"


class GuestRoomBookingStatus(StrEnum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExtendedStayStatus(StrEnum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExtendedStayCompliance(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    EXEMPT = "exempt"
    OVERDUE = "overdue"


class FineStatus(StrEnum):
    RECORDED = "recorded"
    PAID = "paid"
    WAIVED = "waived"


class InventoryCondition(StrEnum):
    WORKING = "working"
    DAMAGED = "damaged"
    REPAIR_NEEDED = "repair_needed"
    SCRAPPED = "scrapped"


class StaffDutyRole(StrEnum):
    CLEANING = "cleaning"
    MESS = "mess"
    MAINTENANCE = "maintenance"
    ATTENDANT = "attendant"
    OTHER = "other"


class SecurityShiftStatus(StrEnum):
    SCHEDULED = "scheduled"
    PRESENT = "present"
    ABSENT = "absent"
    RELIEVED = "relieved"


class NoticePriority(StrEnum):
    NORMAL = "normal"
    IMPORTANT = "important"
    URGENT = "urgent"


class NotificationEventType(StrEnum):
    ROOM_ALLOCATION = "room_allocation"
    LEAVE_STATUS = "leave_status"
    COMPLAINT_STATUS = "complaint_status"
    GUEST_ROOM_STATUS = "guest_room_status"
    EXTENDED_STAY_STATUS = "extended_stay_status"
    FINE_RECORDED = "fine_recorded"
    GENERAL = "general"
