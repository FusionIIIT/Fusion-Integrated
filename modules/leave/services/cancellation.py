"""Cancellation service for approved leave before start date.

Implements CW-EL-02, EL-UC-008, BR-EL-016, BR-EL-017, BR-EL-018, BR-EL-023, BR-EL-024.
"""

from datetime import date

from core.api.exceptions import BadRequestError
from fusion_auth.principal import Principal
from modules.leave.domain.constants import Event, LeaveCategory
from modules.leave.domain.exceptions import LeaveDomainError
from modules.leave.domain.validation import validate_cancellation_pre_start
from modules.leave.models.requests import LeaveRequest
from modules.leave.selectors.policy import get_current_policy
from modules.leave.selectors.requests import get_request_by_id
from modules.leave.services.transitions import _translate_error, execute_transition


def request_cancellation(
    request_id: int,
    principal: Principal,
    current_date: date | None = None,
    remarks: str = "",
) -> LeaveRequest:
    """Employee requests cancellation of approved leave before its start (EL-UC-008 / BR-EL-023)."""
    req = get_request_by_id(request_id, principal)

    if req.user_id != principal.user_id:
        raise BadRequestError("Only the applicant may request cancellation of this leave.")

    today = current_date or date.today()
    try:
        validate_cancellation_pre_start(req.start_date, today)
    except LeaveDomainError as err:
        raise _translate_error(err) from err

    return execute_transition(
        request_id=req.id,
        event=Event.REQUEST_CANCELLATION,
        actor_user_id=principal.user_id,
        actor_role="applicant",
        remarks=remarks or "Cancellation requested by employee before leave start",
    )


def review_cancellation_unit_head(
    request_id: int,
    action: str,  # "approve", "reject", "recommend"
    principal: Principal,
    remarks: str = "",
) -> LeaveRequest:
    """Unit Head reviews cancellation request."""
    req = get_request_by_id(request_id, principal)
    policy = get_current_policy()

    if req.category in (LeaveCategory.CL, LeaveCategory.RH):
        if action not in ("approve", "reject"):
            raise BadRequestError("Unit Head must approve or reject CL/RH cancellation.")
        event = Event.APPROVE_CANCELLATION if action == "approve" else Event.REJECT_CANCELLATION
        return execute_transition(
            request_id=req.id,
            event=event,
            actor_user_id=principal.user_id,
            actor_role="unit_head",
            remarks=remarks or f"Unit Head cancellation decision: {action}",
        )

    # Higher-sanction categories
    context = {"establishment_enabled": policy.establishment_step_enabled}
    return execute_transition(
        request_id=req.id,
        event=Event.RECOMMEND_CANCELLATION,
        actor_user_id=principal.user_id,
        actor_role="unit_head",
        remarks=remarks or "Unit Head recommended cancellation for higher sanction",
        context=context,
    )


def route_cancellation_establishment(
    request_id: int,
    principal: Principal,
    remarks: str = "",
) -> LeaveRequest:
    """Establishment routes cancellation to Sanctioning Authority."""
    req = get_request_by_id(request_id, principal)
    return execute_transition(
        request_id=req.id,
        event=Event.ROUTE_CANCELLATION,
        actor_user_id=principal.user_id,
        actor_role="establishment",
        remarks=remarks or "Cancellation verified and routed by Establishment",
    )


def sanction_cancellation(
    request_id: int,
    action: str,  # "approve" or "reject"
    principal: Principal,
    remarks: str = "",
) -> LeaveRequest:
    """Sanctioning Authority decides cancellation request."""
    req = get_request_by_id(request_id, principal)
    if action not in ("approve", "reject"):
        raise BadRequestError("Decision must be 'approve' or 'reject'.")

    event = Event.APPROVE_CANCELLATION if action == "approve" else Event.REJECT_CANCELLATION
    return execute_transition(
        request_id=req.id,
        event=event,
        actor_user_id=principal.user_id,
        actor_role="sanctioning_authority",
        remarks=remarks or f"Sanctioning authority cancellation decision: {action}",
    )
