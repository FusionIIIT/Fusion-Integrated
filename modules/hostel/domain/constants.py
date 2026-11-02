"""Domain enumerations and constants for Hostel Management."""

from enum import StrEnum


class GenderPolicy(StrEnum):
    BOYS = "boys"
    GIRLS = "girls"
    COED = "coed"


class HostelRole(StrEnum):
    WARDEN = "warden"
    CARETAKER = "caretaker"


class AccommodationStatus(StrEnum):
    SUBMITTED = "submitted"
    ALLOTTED = "allotted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RoomType(StrEnum):
    SINGLE = "single"
    DOUBLE = "double"
    TRIPLE = "triple"
    GUEST = "guest"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    ON_LEAVE = "on_leave"


class LeaveType(StrEnum):
    HOME = "home"
    ACADEMIC = "academic"
    MEDICAL = "medical"
    EMERGENCY = "emergency"


class LeaveStatus(StrEnum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class ComplaintCategory(StrEnum):
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    CARPENTRY = "carpentry"
    CLEANLINESS = "cleanliness"
    INTERNET = "internet"
    DISCIPLINE = "discipline"
    OTHER = "other"


class ComplaintStatus(StrEnum):
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class GuestRoomStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ExtendedStayReason(StrEnum):
    INTERNSHIP = "internship"
    PROJECT = "project"
    ACADEMIC = "academic"
    SPORTS = "sports"
    OTHER = "other"


class ExtendedStayStatus(StrEnum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentComplianceStatus(StrEnum):
    PENDING = "pending"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WAIVED = "waived"


class FineType(StrEnum):
    DAMAGE = "damage"
    RULE_VIOLATION = "rule_violation"
    INDISCIPLINE = "indiscipline"
    NOISE = "noise"
    CLEANLINESS = "cleanliness"
    OTHER = "other"


class InventoryCategory(StrEnum):
    FURNITURE = "furniture"
    ELECTRICAL = "electrical"
    CLEANING = "cleaning"
    SPORTS = "sports"
    LINEN = "linen"
    OTHER = "other"


class InventoryCondition(StrEnum):
    GOOD = "good"
    FAIR = "fair"
    NEEDS_REPAIR = "needs_repair"


class StaffRole(StrEnum):
    CLEANING_STAFF = "cleaning_staff"
    ELECTRICIAN = "electrician"
    PLUMBER = "plumber"
    MESS_WORKER = "mess_worker"
    ATTENDANT = "attendant"
    SUPERVISOR = "supervisor"


class ShiftType(StrEnum):
    MORNING = "morning"
    EVENING = "evening"
    NIGHT = "night"
    GENERAL = "general"


class NoticeCategory(StrEnum):
    GENERAL = "general"
    MAINTENANCE = "maintenance"
    DISCIPLINE = "discipline"
    EVENT = "event"
    EMERGENCY = "emergency"
