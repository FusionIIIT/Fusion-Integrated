"""Domain constants and enumerations for ELM."""
from enum import StrEnum


class LeaveType(StrEnum):
    CL = "CL"       # Casual Leave (8 days/year)
    RH = "RH"       # Restricted Holiday (2 days/year)
    SCL = "SCL"     # Special Casual Leave (up to 15 days/year)
    EL = "EL"       # Earned Leave (30 days/year)
    VL = "VL"       # Vacation Leave (60 days/year faculty)
    COL = "COL"     # Commuted / Medical Leave (20 days/year)


class HalfDayChoice(StrEnum):
    FULL = "FULL"
    FIRST_HALF = "FIRST_HALF"
    SECOND_HALF = "SECOND_HALF"


class ApplicationStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    RECOMMENDED = "RECOMMENDED"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# Default initial annual entitlements (BR-EL-002, 003, 004, 005, 006, 009)
DEFAULT_ENTITLEMENTS = {
    LeaveType.CL: 8.0,
    LeaveType.RH: 2.0,
    LeaveType.SCL: 15.0,
    LeaveType.EL: 30.0,
    LeaveType.VL: 60.0,
    LeaveType.COL: 20.0,
}

# Continuous counting applies to EL, COL, VL (BR-EL-011)
CONTINUOUS_COUNTING_LEAVES = {
    LeaveType.EL,
    LeaveType.COL,
    LeaveType.VL,
}

# Leaves finalized directly by Unit Head (BR-EL-016)
UNIT_HEAD_FINAL_LEAVES = {
    LeaveType.CL,
    LeaveType.RH,
}
