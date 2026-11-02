from enum import StrEnum


class HostelGender(StrEnum):
    BOYS = "boys"
    GIRLS = "girls"
    COED = "coed"


class RoleBindingType(StrEnum):
    WARDEN = "warden"
    CARETAKER = "caretaker"


class RoomStatus(StrEnum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    FULL = "full"
    MAINTENANCE = "maintenance"
    BLOCKED = "blocked"


class AccommodationRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    ALLOCATED = "allocated"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AllotmentStatus(StrEnum):
    ACTIVE = "active"
    VACATED = "vacated"
    TRANSFERRED = "transferred"


class RoomExchangeStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    ON_LEAVE = "on_leave"


class LeaveType(StrEnum):
    CASUAL = "casual"
    HOME = "home"
    MEDICAL = "medical"
    ACADEMIC = "academic"
    EMERGENCY = "emergency"


class LeaveStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ComplaintCategory(StrEnum):
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    CARPENTRY = "carpentry"
    CLEANLINESS = "cleanliness"
    INTERNET = "internet"
    DISCIPLINE = "discipline"
    MESS = "mess"
    OTHER = "other"


class ComplaintSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class ComplaintStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"
    REJECTED = "rejected"


class GuestRoomBookingStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class ExtendedStayReason(StrEnum):
    INTERNSHIP = "internship"
    PROJECT = "project"
    EXAM = "exam"
    MEDICAL = "medical"
    OTHER = "other"


class ExtendedStayStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ComplianceStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    WAIVED = "waived"


class FineStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    WAIVED = "waived"


class InventoryCategory(StrEnum):
    FURNITURE = "furniture"
    ELECTRICAL = "electrical"
    CLEANING = "cleaning"
    BEDDING = "bedding"
    APPLIANCE = "appliance"
    SPORTS = "sports"
    OTHER = "other"


class StaffRole(StrEnum):
    CLEANER = "cleaner"
    ELECTRICIAN = "electrician"
    PLUMBER = "plumber"
    SECURITY = "security"
    MESS_HELPER = "mess_helper"
    ATTENDANT = "attendant"


class StaffShift(StrEnum):
    MORNING = "morning"
    EVENING = "evening"
    NIGHT = "night"
    ROTATIONAL = "rotational"


class SecurityShiftType(StrEnum):
    MORNING = "morning"
    EVENING = "evening"
    NIGHT = "night"


class NoticeAudience(StrEnum):
    ALL = "all"
    STUDENTS = "students"
    CARETAKERS = "caretakers"
    WARDENS = "wardens"


class NotificationEventType(StrEnum):
    ALLOTMENT_UPDATED = "allotment_updated"
    ROOM_VACATED = "room_vacated"
    LEAVE_STATUS_CHANGED = "leave_status_changed"
    COMPLAINT_STATUS_CHANGED = "complaint_status_changed"
    COMPLAINT_ESCALATED = "complaint_escalated"
    GUEST_BOOKING_DECIDED = "guest_booking_decided"
    EXTENDED_STAY_DECIDED = "extended_stay_decided"
    FINE_ISSUED = "fine_issued"
    NOTICE_PUBLISHED = "notice_published"
