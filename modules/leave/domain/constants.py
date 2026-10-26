"""Domain constants for Employee Leave Management (ELM).

Pure Python — no Django, DRF or Celery imports permitted.
"""
from decimal import Decimal
from enum import Enum


class LeaveCategory(str, Enum):
    CL = "CL"       # Casual Leave
    RH = "RH"       # Restricted Holiday
    SCL = "SCL"     # Special Casual Leave
    EL = "EL"       # Earned Leave
    COL = "COL"     # Commuted Leave
    VL = "VL"       # Vacation Leave


class HalfDayOption(str, Enum):
    NONE = "NONE"
    FIRST_HALF = "FIRST_HALF"
    SECOND_HALF = "SECOND_HALF"


class LeaveStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_SUBSTITUTE = "PENDING_SUBSTITUTE"
    SUBSTITUTE_DECLINED = "SUBSTITUTE_DECLINED"
    PENDING_UNIT_HEAD = "PENDING_UNIT_HEAD"
    PENDING_ESTABLISHMENT = "PENDING_ESTABLISHMENT"
    PENDING_SANCTION = "PENDING_SANCTION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    EXT_REQUESTED = "EXT_REQUESTED"
    RESUMED = "RESUMED"
    RESUMPTION_REVIEWED = "RESUMPTION_REVIEWED"


class SubstituteStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class UnitHeadDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RECOMMENDED = "RECOMMENDED"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


class SanctionDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ResumptionOutcome(str, Enum):
    NORMAL = "NORMAL"
    EARLY = "EARLY"
    LATE = "LATE"


#: Default annual policy rules per BR-EL-002..009
CATEGORY_POLICY = {
    LeaveCategory.CL: {
        "annual_entitlement": Decimal("8.0"),
        "carries_forward": False,
        "continuous_counting": False,
        "supports_half_day": True,
        "unit_head_is_final": True,
        "substitute_mandatory": False,
    },
    LeaveCategory.RH: {
        "annual_entitlement": Decimal("2.0"),
        "carries_forward": False,
        "continuous_counting": False,
        "supports_half_day": False,
        "unit_head_is_final": True,
        "substitute_mandatory": False,
    },
    LeaveCategory.SCL: {
        "annual_entitlement": Decimal("15.0"),
        "carries_forward": False,
        "continuous_counting": False,
        "supports_half_day": False,
        "unit_head_is_final": False,
        "substitute_mandatory": False,
    },
    LeaveCategory.EL: {
        "annual_entitlement": Decimal("30.0"),  # non-faculty default; faculty gets EL from VL conversion
        "carries_forward": True,
        "continuous_counting": True,
        "supports_half_day": False,
        "unit_head_is_final": False,
        "substitute_mandatory": True,
    },
    LeaveCategory.COL: {
        "annual_entitlement": Decimal("20.0"),
        "carries_forward": True,
        "continuous_counting": True,
        "supports_half_day": False,
        "unit_head_is_final": False,
        "substitute_mandatory": True,
    },
    LeaveCategory.VL: {
        "annual_entitlement": Decimal("60.0"),  # faculty only
        "carries_forward": False,
        "continuous_counting": True,
        "supports_half_day": False,
        "unit_head_is_final": False,
        "substitute_mandatory": True,
    },
}
