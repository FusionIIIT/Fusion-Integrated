"""Domain entities and enums for Leave Management."""

from enum import StrEnum


class LeaveCategory(StrEnum):
    CL = "CL"  # Casual Leave (8 days/yr, half days supported, lapses)
    RH = "RH"  # Restricted Holiday (2 days/yr, lapses)
    SCL = "SCL"  # Special Casual Leave (up to 15 days/yr, lapses)
    EL = "EL"  # Earned Leave (30 days/yr for staff, continuous counting, carries forward)
    COL = "COL"  # Commuted Leave (20 days/yr, carries forward)
    VL = "VL"  # Vacation Leave (60 days/yr for faculty, converts 2:1 to EL at year end)


class HalfDayType(StrEnum):
    FULL = "FULL"
    FIRST_HALF = "FIRST_HALF"
    SECOND_HALF = "SECOND_HALF"


class LeaveStatus(StrEnum):
    DRAFT = "DRAFT"
    AWAITING_SUBSTITUTE = "AWAITING_SUBSTITUTE"
    SUBSTITUTE_DECLINED = "SUBSTITUTE_DECLINED"
    AWAITING_UNIT_HEAD = "AWAITING_UNIT_HEAD"
    AWAITING_ESTABLISHMENT = "AWAITING_ESTABLISHMENT"
    AWAITING_SANCTION = "AWAITING_SANCTION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    AWAITING_CANCELLATION = "AWAITING_CANCELLATION"
    CANCELLED = "CANCELLED"


class SubstituteStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class ReviewDecision(StrEnum):
    RECOMMENDED = "RECOMMENDED"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ResumptionStatus(StrEnum):
    NONE = "NONE"
    SUBMITTED = "SUBMITTED"
    REVIEWED = "REVIEWED"
