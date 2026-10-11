"""Domain constants and enumerations for Employee Leave Management.

Pure Python — no framework imports (ADR-0013 / .importlinter).
"""

from enum import StrEnum


class LeaveCategory(StrEnum):
    CL = "CL"  # Casual Leave (BR-EL-002)
    RH = "RH"  # Restricted Holiday (BR-EL-003)
    SCL = "SCL"  # Special Casual Leave (BR-EL-004)
    EL = "EL"  # Earned Leave (BR-EL-005)
    COL = "COL"  # Commuted Leave (BR-EL-009)
    VL = "VL"  # Vacation Leave (BR-EL-006)


class HalfDay(StrEnum):
    NONE = "none"
    FIRST_HALF = "first_half"
    SECOND_HALF = "second_half"


class RequestStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_SUBSTITUTE_RESPONSE = "awaiting_substitute_response"
    APPLICANT_ACTION_REQUIRED = "applicant_action_required"
    AWAITING_UNIT_HEAD_REVIEW = "awaiting_unit_head_review"
    AWAITING_ESTABLISHMENT_ROUTING = "awaiting_establishment_routing"
    AWAITING_FINAL_SANCTION_DECISION = "awaiting_final_sanction_decision"
    AWAITING_DIRECTOR_SELF_SANCTION = "awaiting_director_self_sanction"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

    # Cancellation workflow states (CW-EL-02)
    CANCELLATION_PENDING_UNIT_HEAD = "cancellation_pending_unit_head"
    CANCELLATION_PENDING_ESTABLISHMENT = "cancellation_pending_establishment"
    CANCELLATION_PENDING_FINAL_DECISION = "cancellation_pending_final_decision"
    CANCELLED = "cancelled"

    # Extension workflow states (CW-EL-03)
    EXT_AWAITING_SUBSTITUTE = "ext_awaiting_substitute"
    EXT_APPLICANT_ACTION_REQUIRED = "ext_applicant_action_required"
    EXT_AWAITING_UNIT_HEAD = "ext_awaiting_unit_head"
    EXT_PENDING_ESTABLISHMENT = "ext_pending_establishment"
    EXT_PENDING_FINAL_DECISION = "ext_pending_final_decision"
    EXTENDED = "extended"
    EXTENSION_REJECTED = "extension_rejected"
    EXTENSION_WITHDRAWN = "extension_withdrawn"

    # Resumption workflow states (CW-EL-04)
    RESUMPTION_REVIEW_PENDING = "resumption_review_pending"
    RESUMPTION_REVIEWED_NORMAL = "resumption_reviewed_normal"
    RESUMPTION_REVIEWED_EARLY = "resumption_reviewed_early"
    RESUMPTION_REVIEWED_LATE = "resumption_reviewed_late"


class Event(StrEnum):
    SUBMIT = "submit"
    SUBSTITUTE_ACCEPT = "substitute_accept"
    SUBSTITUTE_DECLINE = "substitute_decline"
    NOMINATE_REPLACEMENT = "nominate_replacement"
    APPROVE = "approve"
    REJECT = "reject"
    RECOMMEND = "recommend"
    NOT_RECOMMEND = "not_recommend"
    ROUTE = "route"
    WITHDRAW = "withdraw"

    # Cancellation events
    REQUEST_CANCELLATION = "request_cancellation"
    APPROVE_CANCELLATION = "approve_cancellation"
    REJECT_CANCELLATION = "reject_cancellation"
    RECOMMEND_CANCELLATION = "recommend_cancellation"
    ROUTE_CANCELLATION = "route_cancellation"

    # Extension events
    REQUEST_EXTENSION = "request_extension"

    # Resumption events
    SUBMIT_RESUMPTION = "submit_resumption"
    REVIEW_NORMAL = "review_normal"
    REVIEW_EARLY = "review_early"
    REVIEW_LATE = "review_late"

    # Offline synchronization (audit trail only, not in state machine transitions)
    OFFLINE_RECORD = "offline_record"


class LedgerTransactionType(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"
    LAPSE = "lapse"
    CONVERSION = "conversion"
    RESTORATION = "restoration"
    ADJUSTMENT = "adjustment"


class SubstituteStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class UnitHeadRecommendation(StrEnum):
    NONE = "none"
    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"


class ResumptionType(StrEnum):
    NORMAL = "normal"
    EARLY = "early"
    LATE = "late"
