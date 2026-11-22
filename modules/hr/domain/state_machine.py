from __future__ import annotations

from dataclasses import dataclass

PENDING_VERIFICATION = "pending_verification"
PENDING_AUTHORITY = "pending_authority"
PENDING_NEXT_AUTHORITY = "pending_next_authority"
APPROVED = "approved"
REJECTED = "rejected"
FINANCIAL_PROCESSING_RECORDED = "financial_processing_recorded"

SUBMITTED = "submitted"
PENDING_REVIEW = "pending_review"
APPRAISAL_PENDING_NEXT = "pending_next_authority"
CLOSED = "closed"

LEAVE_PENDING = "pending_authority"
LEAVE_PENDING_NEXT = "pending_next_authority"
LEAVE_APPROVED = "approved"
LEAVE_REJECTED = "rejected"
MAX_LEAVE_ROUTE_LENGTH = 2


class InvalidTransition(Exception):
    def __init__(self, state: str, action: str):
        super().__init__(f"Action {action!r} is not valid while in {state!r}.")
        self.state = state
        self.action = action


@dataclass(frozen=True)
class ClaimTransition:
    state: str
    authority_step: int


LEAVE_DECISIONS = {
    (LEAVE_PENDING, "forward"): LEAVE_PENDING_NEXT,
    (LEAVE_PENDING, "approve"): LEAVE_APPROVED,
    (LEAVE_PENDING, "reject"): LEAVE_REJECTED,
    (LEAVE_PENDING_NEXT, "forward"): LEAVE_PENDING_NEXT,
    (LEAVE_PENDING_NEXT, "approve"): LEAVE_APPROVED,
    (LEAVE_PENDING_NEXT, "reject"): LEAVE_REJECTED,
}


def supports_leave_route_length(route_length: int) -> bool:
    return 1 <= route_length <= MAX_LEAVE_ROUTE_LENGTH


def decide_leave(
    state: str, *, action: str, authority_step: int, route_length: int
) -> ClaimTransition:
    next_state = LEAVE_DECISIONS.get((state, action))
    if next_state is None:
        raise InvalidTransition(state, action)
    if not supports_leave_route_length(route_length) or authority_step >= route_length:
        raise InvalidTransition(state, "route_invalid")
    next_step = authority_step
    if action == "forward":
        if authority_step != 0:
            raise InvalidTransition(state, "forwarding_already_used")
        if authority_step + 1 >= route_length:
            raise InvalidTransition(state, "no_next_authority")
        next_step += 1
    elif action == "approve" and authority_step + 1 != route_length:
        raise InvalidTransition(state, "approval_must_follow_route")
    return ClaimTransition(next_state, next_step)


def verify_claim(state: str, *, verified: bool, has_route: bool) -> ClaimTransition:
    if state != PENDING_VERIFICATION:
        raise InvalidTransition(state, "verify")
    if not verified:
        return ClaimTransition(PENDING_VERIFICATION, 0)
    if not has_route:
        raise InvalidTransition(state, "route_not_configured")
    return ClaimTransition(PENDING_AUTHORITY, 0)


def decide_claim(
    state: str,
    *,
    action: str,
    authority_step: int,
    route_length: int,
) -> ClaimTransition:
    if state not in {PENDING_AUTHORITY, PENDING_NEXT_AUTHORITY}:
        raise InvalidTransition(state, action)
    if route_length < 1 or authority_step >= route_length:
        raise InvalidTransition(state, "route_invalid")
    if action == "forward":
        if authority_step + 1 >= route_length:
            raise InvalidTransition(state, "no_next_authority")
        return ClaimTransition(PENDING_NEXT_AUTHORITY, authority_step + 1)
    if action in {"approve", "reject"}:
        if action == "approve" and authority_step + 1 != route_length:
            raise InvalidTransition(state, "approval_must_follow_route")
        return ClaimTransition(APPROVED if action == "approve" else REJECTED, authority_step)
    raise InvalidTransition(state, action)


def verify_appraisal_state(state: str) -> None:
    if state != SUBMITTED:
        raise InvalidTransition(state, "assign_reviewers")


def review_appraisal(
    state: str,
    *,
    action: str,
    current_index: int,
    reviewer_count: int,
) -> ClaimTransition:
    if state not in {PENDING_REVIEW, APPRAISAL_PENDING_NEXT}:
        raise InvalidTransition(state, action)
    if reviewer_count < 1 or current_index >= reviewer_count:
        raise InvalidTransition(state, "reviewers_invalid")
    if action == "forward":
        if current_index + 1 >= reviewer_count:
            raise InvalidTransition(state, "no_next_reviewer")
        return ClaimTransition(APPRAISAL_PENDING_NEXT, current_index + 1)
    if action == "finalize":
        if current_index + 1 != reviewer_count:
            raise InvalidTransition(state, "finalization_must_follow_route")
        return ClaimTransition(CLOSED, current_index)
    raise InvalidTransition(state, action)
