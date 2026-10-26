"""Domain entities and constants for ELM."""
from enum import StrEnum


class LeaveCategory(StrEnum):
    CL = "CL"      # Casual Leave (8 days, lapses)
    RH = "RH"      # Restricted Holiday (2 days, lapses)
    SCL = "SCL"    # Special Casual Leave (15 days, lapses)
    EL = "EL"      # Earned Leave (30 days staff / converted from VL for faculty, carries forward)
    COL = "COL"    # Commuted Leave (20 days, medical, carries forward)
    VL = "VL"      # Vacation Leave (60 days faculty, converts to EL at 2:1 at year end)


class LeaveStatus(StrEnum):
    SUBMITTED = "submitted"
    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CANCELLED = "cancelled"


class SubstituteStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class StepDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"


class CountingMethod(StrEnum):
    CONTINUOUS = "continuous"        # EL, COL, VL: weekends and holidays count
    NON_CONTINUOUS = "non_continuous"  # CL, SCL, RH: working days only
