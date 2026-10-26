"""Domain constants for Employee Leave Management (ELM).

Pure Python constants: categories, statuses, workflows, roles.
"""
from enum import Enum


class LeaveCategory(str, Enum):
    CL = "CL"       # Casual Leave (8 days/yr, half-day supported, lapse)
    RH = "RH"       # Restricted Holiday (2 days/yr, published calendar, lapse)
    SCL = "SCL"     # Special Casual Leave (up to 15 days/yr, authority judgment, lapse)
    EL = "EL"       # Earned Leave (30 days/yr non-faculty, carries forward)
    COL = "COL"     # Commuted Leave (20 days/yr, medical/balance controlled, carries forward)
    VL = "VL"       # Vacation Leave (60 days faculty, calendar periods, 2:1 EL conversion at year end)


# Categories where intervening weekends and closed holidays count continuously (BR-EL-011)
CONTINUOUS_COUNT_CATEGORIES = {
    LeaveCategory.EL,
    LeaveCategory.COL,
    LeaveCategory.VL,
}

# Categories where unused balance carries forward at year end
CARRY_FORWARD_CATEGORIES = {
    LeaveCategory.EL,
    LeaveCategory.COL,
}

# Categories where unused balance lapses at year end
LAPSE_CATEGORIES = {
    LeaveCategory.CL,
    LeaveCategory.RH,
    LeaveCategory.SCL,
    LeaveCategory.VL,  # VL converts to EL, unconverted VL lapses
}

# Default annual entitlements per category
ANNUAL_ENTITLEMENTS = {
    LeaveCategory.CL: 8.0,
    LeaveCategory.RH: 2.0,
    LeaveCategory.SCL: 15.0,
    LeaveCategory.EL: 30.0,   # Non-faculty baseline
    LeaveCategory.COL: 20.0,
    LeaveCategory.VL: 60.0,   # Faculty baseline
}


class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    AWAITING_SUBSTITUTE = "AWAITING_SUBSTITUTE"
    APPLICANT_ACTION_REQUIRED = "APPLICANT_ACTION_REQUIRED"
    AWAITING_UNIT_HEAD = "AWAITING_UNIT_HEAD"
    AWAITING_ESTABLISHMENT = "AWAITING_ESTABLISHMENT"
    AWAITING_SANCTION = "AWAITING_SANCTION"
    AWAITING_DIRECTOR_SELF_SANCTION = "AWAITING_DIRECTOR_SELF_SANCTION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    CANCELLED = "CANCELLED"


# Active pending statuses (before final terminal decision)
PENDING_STATUSES = {
    ApplicationStatus.AWAITING_SUBSTITUTE,
    ApplicationStatus.APPLICANT_ACTION_REQUIRED,
    ApplicationStatus.AWAITING_UNIT_HEAD,
    ApplicationStatus.AWAITING_ESTABLISHMENT,
    ApplicationStatus.AWAITING_SANCTION,
    ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION,
}

# Terminal states
TERMINAL_STATUSES = {
    ApplicationStatus.APPROVED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
    ApplicationStatus.CANCELLED,
}

# Active statuses that count against overlap checks (BR-EL-012)
ACTIVE_OVERLAP_STATUSES = PENDING_STATUSES | {ApplicationStatus.APPROVED}


class SubstituteStatus(str, Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class Recommendation(str, Enum):
    NONE = "NONE"
    RECOMMENDED = "RECOMMENDED"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


class HalfDayPeriod(str, Enum):
    NONE = "NONE"
    FIRST_HALF = "FIRST_HALF"
    SECOND_HALF = "SECOND_HALF"


class ResumptionType(str, Enum):
    NORMAL = "NORMAL"
    EARLY = "EARLY"
    LATE = "LATE"


class CancellationStatus(str, Enum):
    PENDING_UNIT_HEAD = "PENDING_UNIT_HEAD"
    PENDING_ESTABLISHMENT = "PENDING_ESTABLISHMENT"
    PENDING_SANCTION = "PENDING_SANCTION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Role(str, Enum):
    EMPLOYEE = "Employee"
    UNIT_HEAD = "Unit Head"
    SUBSTITUTE = "Substitute"
    ESTABLISHMENT = "Deputy Registrar (Estt.)"
    DEAN = "Dean"
    REGISTRAR = "Registrar"
    DIRECTOR = "Director"
    LEAVE_ADMIN = "Leave Admin"
