"""Workflow state machine transitions for ELM.

Pure Python — no Django imports allowed in domain/.
Enforces:
- CW-EL-01: New Leave Processing and Pending Withdrawal
- CW-EL-02: Approved Leave Cancellation
- CW-EL-03: Ongoing Leave Extension
- CW-EL-04: Resumption Review
- BR-EL-016: Unit Head final scope for CL/RH
- BR-EL-017: Unit Head recommendation for higher-sanction leave
- BR-EL-018: Higher-sanction routing
- BR-EL-019: Authority resolution and optional Establishment step
- BR-EL-020: Director self-sanction
- BR-EL-022: Immediate withdrawal of pending request
- BR-EL-023: Cancellation of approved leave before start
- BR-EL-025: Extension of ongoing EL/COL/VL
- BR-EL-028: Normal, early, and late resumption outcome
"""
from __future__ import annotations

from datetime import date, timedelta

from modules.elm.domain.constants import (
    ApplicationStatus,
    ExtensionStatus,
    LeaveCategory,
    RecommendationOutcome,
    ResumptionStatus,
    SanctionDecision,
)

# Active pending states eligible for immediate withdrawal (BR-EL-022)
PENDING_APPLICATION_STATES = frozenset({
    ApplicationStatus.DRAFT,
    ApplicationStatus.AWAITING_SUBSTITUTE,
    ApplicationStatus.APPLICANT_ACTION_REQUIRED,
    ApplicationStatus.AWAITING_UNIT_HEAD,
    ApplicationStatus.AWAITING_DIRECTOR,
    ApplicationStatus.AWAITING_ESTABLISHMENT,
    ApplicationStatus.AWAITING_FINAL_DECISION,
})


def get_initial_submission_status(
    *,
    requires_substitute: bool,
    applicant_is_director: bool,
) -> ApplicationStatus:
    """CW-EL-01: Determine resulting status on initial submission."""
    if requires_substitute:
        return ApplicationStatus.AWAITING_SUBSTITUTE
    if applicant_is_director:
        # BR-EL-020: Director self-sanction bypasses normal Unit Head route
        return ApplicationStatus.AWAITING_DIRECTOR
    return ApplicationStatus.AWAITING_UNIT_HEAD


def transition_substitute_response(
    current_status: ApplicationStatus,
    accepted: bool,
    *,
    applicant_is_director: bool = False,
) -> ApplicationStatus:
    """CW-EL-01 / EL-UC-002: Substitute response transition."""
    if current_status != ApplicationStatus.AWAITING_SUBSTITUTE:
        raise ValueError(
            f"Cannot respond to substitute in state '{current_status.value}'. "
            f"Expected '{ApplicationStatus.AWAITING_SUBSTITUTE.value}'."
        )

    if accepted:
        if applicant_is_director:
            return ApplicationStatus.AWAITING_DIRECTOR
        return ApplicationStatus.AWAITING_UNIT_HEAD
    return ApplicationStatus.APPLICANT_ACTION_REQUIRED


def transition_substitute_replace(
    current_status: ApplicationStatus,
) -> ApplicationStatus:
    """CW-EL-01 / EL-UC-019: Nominate replacement substitute after decline."""
    if current_status != ApplicationStatus.APPLICANT_ACTION_REQUIRED:
        raise ValueError(
            f"Cannot replace substitute in state '{current_status.value}'. "
            f"Expected '{ApplicationStatus.APPLICANT_ACTION_REQUIRED.value}'."
        )
    return ApplicationStatus.AWAITING_SUBSTITUTE


def transition_unit_head_review(
    current_status: ApplicationStatus,
    category: str | LeaveCategory,
    outcome: str | RecommendationOutcome | SanctionDecision,
    *,
    requires_establishment: bool = True,
) -> ApplicationStatus:
    """CW-EL-01 / EL-UC-003: Review leave request at Unit Head."""
    if current_status != ApplicationStatus.AWAITING_UNIT_HEAD:
        raise ValueError(
            f"Cannot review at Unit Head in state '{current_status.value}'."
        )

    cat = LeaveCategory(category) if isinstance(category, str) else category

    # BR-EL-016: For CL and RH, Unit Head is final approve/reject authority
    if cat in (LeaveCategory.CL, LeaveCategory.RH):
        if outcome in (SanctionDecision.APPROVE, "approve"):
            return ApplicationStatus.APPROVED
        if outcome in (SanctionDecision.REJECT, "reject"):
            return ApplicationStatus.REJECTED
        raise ValueError(f"For CL/RH, Unit Head must Approve or Reject. Received '{outcome}'.")

    # BR-EL-017: For SCL, EL, COL, VL, Unit Head records Recommended or Not Recommended.
    # Both outcomes continue through the configured higher-sanction hierarchy!
    if outcome not in (
        RecommendationOutcome.RECOMMENDED,
        RecommendationOutcome.NOT_RECOMMENDED,
        "recommended",
        "not_recommended",
    ):
        raise ValueError(
            f"For higher-sanction leave ({cat.value}), Unit Head must record "
            f"Recommended or Not Recommended. Received '{outcome}'."
        )

    if requires_establishment:
        return ApplicationStatus.AWAITING_ESTABLISHMENT
    return ApplicationStatus.AWAITING_FINAL_DECISION


def transition_establishment_routing(
    current_status: ApplicationStatus,
) -> ApplicationStatus:
    """CW-EL-01 / EL-UC-004: Forward higher-sanction request from Establishment."""
    if current_status != ApplicationStatus.AWAITING_ESTABLISHMENT:
        raise ValueError(
            f"Cannot forward from Establishment in state '{current_status.value}'."
        )
    return ApplicationStatus.AWAITING_FINAL_DECISION


def transition_final_sanction(
    current_status: ApplicationStatus,
    decision: str | SanctionDecision,
) -> ApplicationStatus:
    """CW-EL-01 / EL-UC-005: Final sanction decision by competent authority."""
    valid_states = (
        ApplicationStatus.AWAITING_FINAL_DECISION,
        ApplicationStatus.AWAITING_DIRECTOR,
    )
    if current_status not in valid_states:
        raise ValueError(
            f"Cannot make final sanction decision in state '{current_status.value}'."
        )

    dec = SanctionDecision(decision) if isinstance(decision, str) else decision
    if dec == SanctionDecision.APPROVE:
        return ApplicationStatus.APPROVED
    if dec == SanctionDecision.REJECT:
        return ApplicationStatus.REJECTED
    raise ValueError(f"Invalid sanction decision '{decision}'. Expected APPROVE or REJECT.")


def transition_withdrawal(
    current_status: ApplicationStatus,
) -> ApplicationStatus:
    """CW-EL-01 / EL-UC-007: Immediate withdrawal before final approval.

    BR-EL-022 / CFR-EL-018: A pending request may be withdrawn at any time before
    final approval. Withdrawal is immediate and terminates approval processing.
    """
    if current_status not in PENDING_APPLICATION_STATES:
        raise ValueError(
            f"Cannot withdraw request in state '{current_status.value}'. "
            f"Withdrawal is only permitted before final approval."
        )
    return ApplicationStatus.WITHDRAWN


# --- CW-EL-02: Approved Leave Cancellation ---

def transition_cancellation_request(
    current_status: ApplicationStatus,
    start_date: date,
    current_date: date | None = None,
    *,
    today: date | None = None,
) -> ApplicationStatus:
    """CW-EL-02 / EL-UC-008: Request pre-start cancellation of approved leave.

    BR-EL-023 / CFR-EL-019: Approved leave may be cancelled only before its start date.
    """
    effective_date = today or current_date
    if effective_date is None:
        raise ValueError("current_date or today must be provided.")

    if current_status != ApplicationStatus.APPROVED:
        raise ValueError(
            f"Cancellation can only be requested for APPROVED leave. "
            f"Current state is '{current_status.value}'."
        )
    if effective_date >= start_date:
        raise ValueError(
            f"Cannot cancel leave on or after start date ({start_date}). "
            f"Cancellation is only permitted before start date. "
            f"Current date is {effective_date}. Use extension or resumption instead."
        )
    return ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD


def transition_cancellation_unit_head(
    current_status: ApplicationStatus,
    category: str | LeaveCategory,
    outcome: str,
    *,
    requires_establishment: bool = True,
) -> ApplicationStatus:
    """CW-EL-02 / EL-UC-003: Review cancellation at Unit Head."""
    if current_status != ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD:
        raise ValueError(
            f"Cannot review cancellation at Unit Head in state '{current_status.value}'."
        )

    cat = LeaveCategory(category) if isinstance(category, str) else category

    # CL/RH cancellation is final at Unit Head
    if cat in (LeaveCategory.CL, LeaveCategory.RH):
        if outcome in (SanctionDecision.APPROVE, "approve"):
            return ApplicationStatus.CANCELLED
        if outcome in (SanctionDecision.REJECT, "reject"):
            return ApplicationStatus.APPROVED  # Preserves original approval
        raise ValueError(f"For CL/RH, must Approve or Reject cancellation. Received '{outcome}'.")

    # Higher sanction cancellation
    if outcome not in ("recommended", "not_recommended"):
        raise ValueError(
            f"For higher sanction cancellation, Unit Head must record recommended "
            f"or not_recommended. Received '{outcome}'."
        )

    if requires_establishment:
        return ApplicationStatus.CANCELLATION_PENDING_ESTABLISHMENT
    return ApplicationStatus.CANCELLATION_PENDING_FINAL


def transition_cancellation_establishment(
    current_status: ApplicationStatus,
) -> ApplicationStatus:
    """CW-EL-02 / EL-UC-004: Forward cancellation at Establishment."""
    if current_status != ApplicationStatus.CANCELLATION_PENDING_ESTABLISHMENT:
        raise ValueError(
            f"Cannot forward cancellation in state '{current_status.value}'."
        )
    return ApplicationStatus.CANCELLATION_PENDING_FINAL


def transition_cancellation_final(
    current_status: ApplicationStatus,
    decision: str | SanctionDecision,
) -> ApplicationStatus:
    """CW-EL-02 / EL-UC-005: Final decision on cancellation request."""
    if current_status != ApplicationStatus.CANCELLATION_PENDING_FINAL:
        raise ValueError(
            f"Cannot make final cancellation decision in state '{current_status.value}'."
        )

    dec = SanctionDecision(decision) if isinstance(decision, str) else decision
    if dec == SanctionDecision.APPROVE:
        return ApplicationStatus.CANCELLED
    if dec == SanctionDecision.REJECT:
        return ApplicationStatus.APPROVED  # Original approval preserved
    raise ValueError(f"Invalid cancellation decision '{decision}'.")


# --- CW-EL-03: Ongoing Leave Extension ---

def transition_extension_unit_head(
    current_status: ExtensionStatus,
    outcome: str,
    *,
    requires_establishment: bool = True,
) -> ExtensionStatus:
    """CW-EL-03 / EL-UC-003: Review extension at Unit Head."""
    if current_status != ExtensionStatus.AWAITING_UNIT_HEAD:
        raise ValueError(f"Cannot review extension in state '{current_status.value}'.")

    if outcome not in ("recommended", "not_recommended"):
        raise ValueError("Unit Head must record recommended or not_recommended for extension.")

    if requires_establishment:
        return ExtensionStatus.AWAITING_ESTABLISHMENT
    return ExtensionStatus.AWAITING_FINAL_DECISION


def transition_extension_final(
    current_status: ExtensionStatus,
    decision: str | SanctionDecision,
) -> ExtensionStatus:
    """CW-EL-03 / EL-UC-005: Final decision on extension."""
    if current_status != ExtensionStatus.AWAITING_FINAL_DECISION:
        raise ValueError(f"Cannot make final extension decision in state '{current_status.value}'.")

    dec = SanctionDecision(decision) if isinstance(decision, str) else decision
    if dec == SanctionDecision.APPROVE:
        return ExtensionStatus.APPROVED
    if dec == SanctionDecision.REJECT:
        return ExtensionStatus.REJECTED
    raise ValueError(f"Invalid extension decision '{decision}'.")


# --- CW-EL-04: Resumption Review ---

def determine_resumption_outcome(
    approved_end_date: date,
    actual_resumption_date: date,
) -> tuple[str, ResumptionStatus]:
    """CW-EL-04 / EL-UC-011: Determine resumption type and resulting status.

    BR-EL-028 / CFR-EL-021:
    - Normal (actual == approved end date): No leave period or balance adjustment.
    - Early (actual < approved end date): Balance credited/restored for unused days.
    - Late (actual > approved end date): Balance debited for extra days.
    """
    if actual_resumption_date in (approved_end_date, approved_end_date + timedelta(days=1)):
        return "normal", ResumptionStatus.REVIEWED_NO_ADJUSTMENT
    if actual_resumption_date < approved_end_date:
        return "early", ResumptionStatus.REVIEWED_EARLY_ADJUSTED
    return "late", ResumptionStatus.REVIEWED_LATE_ADJUSTED
