"""Pure state machine implementing SPACS Basis and Composite Workflows. Pure Python."""

from dataclasses import dataclass
from .errors import InvalidTransitionError

# Application States (Scholarship & Renewal)
DRAFT = "draft"
SUBMITTED = "submitted"
UNDER_VERIFICATION = "under_verification"
CORRECTION_REQUIRED = "correction_required"
RESUBMITTED = "resubmitted"
VERIFIED = "verified"
VERIFICATION_CONCERN = "verification_concern"
UNDER_CONVENER_REVIEW = "under_convener_review"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

# Renewal-specific States
RENEWAL_SUBMITTED = "renewal_submitted"
RENEWAL_UNDER_VERIFICATION = "renewal_under_verification"
RENEWAL_VERIFIED = "renewal_verified"
RENEWAL_UNDER_DECISION = "renewal_under_decision"
RENEWED = "renewed"
RENEWAL_REJECTED = "renewal_rejected"

# Award Cycle States
AWARD_CYCLE_OPEN = "open"
CANDIDATE_POOL_PREPARED = "pool_prepared"
UNDER_COMMITTEE_EVALUATION = "under_committee_evaluation"
COMMITTEE_RESULT_RECORDED = "committee_result_recorded"
AWAITING_INSTITUTIONAL_APPROVAL = "awaiting_approval"
READY_FOR_PUBLICATION = "ready_for_publication"
PUBLISHED = "published"

TERMINAL_APPLICATION_STATES = {APPROVED, REJECTED, WITHDRAWN, RENEWED, RENEWAL_REJECTED}
WITHDRAWABLE_STATES = {SUBMITTED, UNDER_VERIFICATION, CORRECTION_REQUIRED, RESUBMITTED, VERIFIED}
EDITABLE_APPLICATION_STATES = {DRAFT, CORRECTION_REQUIRED}


@dataclass(frozen=True)
class Transition:
    source: str
    target: str
    action: str
    actor_role: str
    workflow_id: str


APPLICATION_TRANSITIONS = (
    # BW-SPACS-01: New Application - Successful Verification
    Transition(DRAFT, SUBMITTED, "submit", "student", "BW-SPACS-01"),
    Transition(SUBMITTED, UNDER_VERIFICATION, "open_verification", "spacs_assistant", "BW-SPACS-01"),
    Transition(UNDER_VERIFICATION, VERIFIED, "mark_verified", "spacs_assistant", "BW-SPACS-01"),

    # BW-SPACS-02: Correction and Resubmission
    Transition(UNDER_VERIFICATION, CORRECTION_REQUIRED, "request_correction", "spacs_assistant", "BW-SPACS-02"),
    Transition(CORRECTION_REQUIRED, RESUBMITTED, "resubmit", "student", "BW-SPACS-02"),
    Transition(RESUBMITTED, UNDER_VERIFICATION, "open_verification", "spacs_assistant", "BW-SPACS-02"),
    Transition(RESUBMITTED, VERIFIED, "mark_verified", "spacs_assistant", "BW-SPACS-02"),
    Transition(RESUBMITTED, CORRECTION_REQUIRED, "request_correction", "spacs_assistant", "BW-SPACS-02"),

    # Verification concern handling (AFR-SPACS-025)
    Transition(UNDER_VERIFICATION, VERIFICATION_CONCERN, "record_concern", "spacs_assistant", "BW-SPACS-04"),
    Transition(RESUBMITTED, VERIFICATION_CONCERN, "record_concern", "spacs_assistant", "BW-SPACS-04"),

    # BW-SPACS-03: Scholarship Approval
    Transition(VERIFIED, UNDER_CONVENER_REVIEW, "open_decision", "spacs_convener", "BW-SPACS-03"),
    Transition(UNDER_CONVENER_REVIEW, APPROVED, "approve", "spacs_convener", "BW-SPACS-03"),

    # BW-SPACS-04: Scholarship Rejection
    Transition(VERIFICATION_CONCERN, UNDER_CONVENER_REVIEW, "open_decision", "spacs_convener", "BW-SPACS-04"),
    Transition(UNDER_CONVENER_REVIEW, REJECTED, "reject", "spacs_convener", "BW-SPACS-04"),
    Transition(UNDER_CONVENER_REVIEW, CORRECTION_REQUIRED, "return_for_correction", "spacs_convener", "BW-SPACS-04"),

    # BW-SPACS-05: Cross-Cutting Withdrawal
    Transition(SUBMITTED, WITHDRAWN, "withdraw", "student", "BW-SPACS-05"),
    Transition(UNDER_VERIFICATION, WITHDRAWN, "withdraw", "student", "BW-SPACS-05"),
    Transition(CORRECTION_REQUIRED, WITHDRAWN, "withdraw", "student", "BW-SPACS-05"),
    Transition(RESUBMITTED, WITHDRAWN, "withdraw", "student", "BW-SPACS-05"),
    Transition(VERIFIED, WITHDRAWN, "withdraw", "student", "BW-SPACS-05"),

    # BW-SPACS-06: Renewal Submission & Verification
    Transition(DRAFT, RENEWAL_SUBMITTED, "submit_renewal", "student", "BW-SPACS-06"),
    Transition(RENEWAL_SUBMITTED, RENEWAL_UNDER_VERIFICATION, "open_renewal_verification", "spacs_assistant", "BW-SPACS-06"),
    Transition(RENEWAL_UNDER_VERIFICATION, RENEWAL_VERIFIED, "mark_renewal_verified", "spacs_assistant", "BW-SPACS-06"),
    Transition(RENEWAL_UNDER_VERIFICATION, CORRECTION_REQUIRED, "request_correction", "spacs_assistant", "BW-SPACS-02"),
    Transition(RESUBMITTED, RENEWAL_VERIFIED, "mark_renewal_verified", "spacs_assistant", "BW-SPACS-06"),

    # BW-SPACS-07: Renewal Approval
    Transition(RENEWAL_VERIFIED, RENEWAL_UNDER_DECISION, "open_renewal_decision", "spacs_convener", "BW-SPACS-07"),
    Transition(RENEWAL_UNDER_DECISION, RENEWED, "approve_renewal", "spacs_convener", "BW-SPACS-07"),

    # BW-SPACS-10: Renewal Rejection
    Transition(RENEWAL_VERIFIED, RENEWAL_UNDER_DECISION, "open_renewal_decision", "spacs_convener", "BW-SPACS-10"),
    Transition(RENEWAL_UNDER_DECISION, RENEWAL_REJECTED, "reject_renewal", "spacs_convener", "BW-SPACS-10"),
)

AWARD_TRANSITIONS = (
    # BW-SPACS-08: Award Candidate Preparation and Evaluation
    Transition(AWARD_CYCLE_OPEN, CANDIDATE_POOL_PREPARED, "prepare_pool", "spacs_convener", "BW-SPACS-08"),
    Transition(CANDIDATE_POOL_PREPARED, UNDER_COMMITTEE_EVALUATION, "begin_evaluation", "award_evaluation_committee", "BW-SPACS-08"),
    Transition(UNDER_COMMITTEE_EVALUATION, COMMITTEE_RESULT_RECORDED, "record_committee_result", "award_evaluation_committee", "BW-SPACS-08"),

    # BW-SPACS-09: Award Finalization - Approval Available
    Transition(COMMITTEE_RESULT_RECORDED, READY_FOR_PUBLICATION, "record_approved_outcome", "spacs_convener", "BW-SPACS-09"),
    Transition(READY_FOR_PUBLICATION, PUBLISHED, "publish_results", "spacs_convener", "BW-SPACS-09"),

    # BW-SPACS-11: Award Finalization - Approval Pending
    Transition(COMMITTEE_RESULT_RECORDED, AWAITING_INSTITUTIONAL_APPROVAL, "await_approval", "spacs_convener", "BW-SPACS-11"),
    Transition(AWAITING_INSTITUTIONAL_APPROVAL, READY_FOR_PUBLICATION, "record_approval_received", "spacs_convener", "BW-SPACS-11"),
)


def resolve_application_transition(source: str, action: str, actor_role: str | None = None) -> Transition:
    """Resolve a legal application transition or raise InvalidTransitionError."""
    for t in APPLICATION_TRANSITIONS:
        if t.source == source and t.action == action:
            if actor_role is not None and t.actor_role != actor_role:
                continue
            return t

    raise InvalidTransitionError(
        f"Action '{action}' by '{actor_role}' is not allowed from state '{source}'."
    )


def resolve_award_transition(source: str, action: str, actor_role: str | None = None) -> Transition:
    """Resolve a legal award transition or raise InvalidTransitionError."""
    for t in AWARD_TRANSITIONS:
        if t.source == source and t.action == action:
            if actor_role is not None and t.actor_role != actor_role:
                continue
            return t

    raise InvalidTransitionError(
        f"Award action '{action}' by '{actor_role}' is not allowed from state '{source}'."
    )


def is_application_transition_legal(source: str, target: str) -> bool:
    """Return True if a direct transition exists between source and target."""
    return any(t.source == source and t.target == target for t in APPLICATION_TRANSITIONS)


def is_award_transition_legal(source: str, target: str) -> bool:
    """Return True if a direct transition exists between source and target for awards."""
    return any(t.source == source and t.target == target for t in AWARD_TRANSITIONS)
