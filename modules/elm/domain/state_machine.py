"""ELM Workflow State Machine (Section 7, 8, 9, 10)."""
from modules.elm.domain.constants import (
    CL,
    DECISION_APPROVED,
    DECISION_REJECTED,
    RECOMMENDATION_NOT_RECOMMENDED,
    RECOMMENDATION_RECOMMENDED,
    RH,
    STATUS_APPROVED,
    STATUS_CANCELLATION_REQUESTED,
    STATUS_CANCELLED,
    STATUS_PENDING_HIGHER_SANCTION,
    STATUS_PENDING_SUBSTITUTE,
    STATUS_PENDING_UNIT_HEAD,
    STATUS_REJECTED,
    STATUS_RESUMED,
    STATUS_SUBSTITUTE_DECLINED,
    STATUS_WITHDRAWN,
    SUBSTITUTE_ACCEPTED,
    SUBSTITUTE_DECLINED,
)


class InvalidTransitionError(Exception):
    pass


def initial_status(has_substitute: bool, is_director_self: bool = False) -> str:
    """Determine initial status on application submission."""
    if is_director_self:
        return STATUS_APPROVED
    if has_substitute:
        return STATUS_PENDING_SUBSTITUTE
    return STATUS_PENDING_UNIT_HEAD


def transition_substitute_response(current_status: str, response: str) -> str:
    """Handle substitute consent response."""
    if current_status != STATUS_PENDING_SUBSTITUTE:
        raise InvalidTransitionError(f"Cannot record substitute response when in status {current_status!r}.")

    if response == SUBSTITUTE_ACCEPTED:
        return STATUS_PENDING_UNIT_HEAD
    if response == SUBSTITUTE_DECLINED:
        return STATUS_SUBSTITUTE_DECLINED
    raise InvalidTransitionError(f"Unknown substitute response: {response!r}.")


def transition_renominate_substitute(current_status: str) -> str:
    """Handle re-nominating another eligible substitute after decline."""
    if current_status != STATUS_SUBSTITUTE_DECLINED:
        raise InvalidTransitionError(f"Cannot re-nominate substitute from status {current_status!r}.")
    return STATUS_PENDING_SUBSTITUTE


def transition_unit_head_decision(
    current_status: str,
    category: str,
    decision_or_rec: str,
) -> str:
    """Handle Unit Head review (Section 7).

    - For CL and RH: Unit Head is final decision authority (Approve / Reject).
    - For SCL, EL, COL, VL: Unit Head records Recommended or Not Recommended.
      Both proceed to higher sanction (Not Recommended is not a final rejection).
    """
    if current_status != STATUS_PENDING_UNIT_HEAD:
        raise InvalidTransitionError(f"Cannot record Unit Head action when in status {current_status!r}.")

    if category in (CL, RH):
        if decision_or_rec == DECISION_APPROVED:
            return STATUS_APPROVED
        if decision_or_rec == DECISION_REJECTED:
            return STATUS_REJECTED
        raise InvalidTransitionError(f"Invalid final decision {decision_or_rec!r} for {category}.")

    # For SCL, EL, COL, VL
    if decision_or_rec in (RECOMMENDATION_RECOMMENDED, RECOMMENDATION_NOT_RECOMMENDED):
        return STATUS_PENDING_HIGHER_SANCTION
    raise InvalidTransitionError(f"Invalid recommendation {decision_or_rec!r} for {category}.")


def transition_higher_sanction(current_status: str, decision: str) -> str:
    """Handle final sanctioning authority decision."""
    if current_status != STATUS_PENDING_HIGHER_SANCTION:
        raise InvalidTransitionError(f"Cannot record higher sanction when in status {current_status!r}.")

    if decision == DECISION_APPROVED:
        return STATUS_APPROVED
    if decision == DECISION_REJECTED:
        return STATUS_REJECTED
    raise InvalidTransitionError(f"Invalid higher sanction decision: {decision!r}.")


def transition_withdraw(current_status: str) -> str:
    """Handle immediate withdrawal before final approval (Section 8)."""
    if current_status in (STATUS_APPROVED, STATUS_REJECTED, STATUS_WITHDRAWN, STATUS_CANCELLED, STATUS_RESUMED):
        raise InvalidTransitionError(f"Cannot withdraw application in status {current_status!r}.")
    return STATUS_WITHDRAWN


def transition_request_cancellation(current_status: str) -> str:
    """Handle cancellation request for approved leave before start (Section 8)."""
    if current_status != STATUS_APPROVED:
        raise InvalidTransitionError(f"Only approved leaves can be cancelled; current is {current_status!r}.")
    return STATUS_CANCELLATION_REQUESTED


def transition_cancellation_decision(current_status: str, decision: str) -> str:
    """Handle decision on cancellation request."""
    if current_status != STATUS_CANCELLATION_REQUESTED:
        raise InvalidTransitionError(f"Cannot record cancellation decision when in {current_status!r}.")

    if decision == DECISION_APPROVED:
        return STATUS_CANCELLED
    if decision == DECISION_REJECTED:
        return STATUS_APPROVED
    raise InvalidTransitionError(f"Invalid cancellation decision: {decision!r}.")


def transition_resumption(current_status: str) -> str:
    """Handle resumption review (Section 10)."""
    if current_status != STATUS_APPROVED:
        raise InvalidTransitionError(f"Cannot resume leave from status {current_status!r}.")
    return STATUS_RESUMED
