"""Domain constants and enumerations for ELM.

Pure Python — no Django imports allowed in domain/.
"""
from enum import StrEnum


class LeaveCategory(StrEnum):
    CL = "CL"      # Casual Leave
    RH = "RH"      # Restricted Holiday
    SCL = "SCL"    # Special Casual Leave
    EL = "EL"      # Earned Leave
    COL = "COL"    # Commuted Leave
    VL = "VL"      # Vacation Leave


class HalfDaySession(StrEnum):
    FIRST_HALF = "first_half"
    SECOND_HALF = "second_half"


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_SUBSTITUTE = "awaiting_substitute"
    APPLICANT_ACTION_REQUIRED = "applicant_action_required"
    AWAITING_UNIT_HEAD = "awaiting_unit_head"
    AWAITING_DIRECTOR = "awaiting_director"
    AWAITING_ESTABLISHMENT = "awaiting_establishment"
    AWAITING_FINAL_DECISION = "awaiting_final_decision"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    # Cancellation workflow states (CW-EL-02)
    CANCELLATION_PENDING_UNIT_HEAD = "cancellation_pending_unit_head"
    CANCELLATION_PENDING_ESTABLISHMENT = "cancellation_pending_establishment"
    CANCELLATION_PENDING_FINAL = "cancellation_pending_final"
    CANCELLED = "cancelled"


class ExtensionStatus(StrEnum):
    AWAITING_SUBSTITUTE = "awaiting_substitute"
    APPLICANT_ACTION_REQUIRED = "applicant_action_required"
    AWAITING_UNIT_HEAD = "awaiting_unit_head"
    AWAITING_ESTABLISHMENT = "awaiting_establishment"
    AWAITING_FINAL_DECISION = "awaiting_final_decision"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ResumptionStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    REVIEWED_NO_ADJUSTMENT = "reviewed_no_adjustment"
    REVIEWED_EARLY_ADJUSTED = "reviewed_early_adjusted"
    REVIEWED_LATE_ADJUSTED = "reviewed_late_adjusted"


class SubstituteStatus(StrEnum):
    NONE = "none"
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class RecommendationOutcome(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"


class CancellationOutcome(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"


class ExtensionOutcome(StrEnum):
    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"


class SanctionDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class HolidayType(StrEnum):
    CLOSED_HOLIDAY = "closed_holiday"
    RESTRICTED_HOLIDAY = "restricted_holiday"


class TransactionType(StrEnum):
    ANNUAL_CREDIT = "annual_credit"
    CARRY_FORWARD = "carry_forward"
    DEBIT_AVAIL = "debit_avail"
    RESTORE_CANCELLATION = "restore_cancellation"
    ADJUST_RESUMPTION_CREDIT = "adjust_resumption_credit"
    ADJUST_RESUMPTION_DEBIT = "adjust_resumption_debit"
    VL_CONVERSION_CREDIT = "vl_conversion_credit"
    VL_CONVERSION_LAPSE = "vl_conversion_lapse"
    YEAR_END_LAPSE = "year_end_lapse"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    OFFLINE_SANCTION_DEBIT = "offline_sanction_debit"


class TaskType(StrEnum):
    SUBSTITUTE_RESPONSE = "substitute_response"
    UNIT_HEAD_REVIEW = "unit_head_review"
    ESTABLISHMENT_ROUTING = "establishment_routing"
    FINAL_SANCTION = "final_sanction"
    DIRECTOR_SELF_SANCTION = "director_self_sanction"
    CANCELLATION_UNIT_HEAD = "cancellation_unit_head"
    CANCELLATION_ESTABLISHMENT = "cancellation_establishment"
    CANCELLATION_FINAL = "cancellation_final"
    EXTENSION_SUBSTITUTE = "extension_substitute"
    EXTENSION_UNIT_HEAD = "extension_unit_head"
    EXTENSION_ESTABLISHMENT = "extension_establishment"
    EXTENSION_FINAL = "extension_final"
    RESUMPTION_REVIEW = "resumption_review"


# Categories that require higher sanction beyond Unit Head (BR-EL-017)
HIGHER_SANCTION_CATEGORIES = frozenset({
    LeaveCategory.SCL,
    LeaveCategory.EL,
    LeaveCategory.COL,
    LeaveCategory.VL,
})

# Categories where intervening weekends and closed holidays count continuously (BR-EL-011)
CONTINUOUS_COUNTING_CATEGORIES = frozenset({
    LeaveCategory.EL,
    LeaveCategory.COL,
    LeaveCategory.VL,
})

# Categories that lapse at year end (BR-EL-002, BR-EL-003, BR-EL-004)
LAPSE_AT_YEAR_END_CATEGORIES = frozenset({
    LeaveCategory.CL,
    LeaveCategory.RH,
    LeaveCategory.SCL,
})
