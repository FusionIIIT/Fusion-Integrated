"""Substitute service for response and decline recovery.

Implements EL-UC-002, EL-UC-019, BR-EL-014, BR-EL-015.
"""

from django.db import transaction

from core.api.exceptions import BadRequestError
from fusion_auth.principal import Principal
from modules.leave.domain.constants import Event, RequestStatus, SubstituteStatus
from modules.leave.domain.exceptions import LeaveDomainError
from modules.leave.domain.validation import validate_substitute
from modules.leave.models.requests import LeaveRequest
from modules.leave.models.sla import SlaTaskClock
from modules.leave.selectors.requests import (
    get_request_by_id,
    get_substitute_active_intervals,
)
from modules.leave.services.transitions import _translate_error, execute_transition


def respond_to_substitute_request(
    request_id: int,
    accept: bool,
    principal: Principal,
    remarks: str = "",
) -> LeaveRequest:
    """Handles substitute response: accept releases consent gate, decline requires replacement."""
    req = get_request_by_id(request_id, principal)

    if req.substitute_user_id != principal.user_id:
        raise BadRequestError("You are not the nominated substitute for this request.")

    with transaction.atomic():
        event = Event.SUBSTITUTE_ACCEPT if accept else Event.SUBSTITUTE_DECLINE
        req.substitute_status = (
            SubstituteStatus.ACCEPTED.value if accept else SubstituteStatus.DECLINED.value
        )
        req.save(update_fields=["substitute_status", "updated_at"])

        # Stop active substitute SLA clock
        SlaTaskClock.objects.filter(
            request=req,
            task_type="substitute_response",
            is_pending=True,
        ).update(is_pending=False)

        is_director = False  # Checked on applicant
        context = {"is_director": is_director}

        req = execute_transition(
            request_id=req.id,
            event=event,
            actor_user_id=principal.user_id,
            actor_role="substitute",
            remarks=remarks
            or ("Accepted substitute request" if accept else "Declined substitute request"),
            context=context,
        )

        # If accepted and transitioned to Unit Head review, start Unit Head SLA clock
        if req.status == RequestStatus.AWAITING_UNIT_HEAD_REVIEW:
            SlaTaskClock.objects.create(
                request=req,
                task_type="unit_head_review",
                assigned_to_role="Unit Head",
                state=req.status,
            )

        return req


def nominate_replacement_substitute(
    request_id: int,
    replacement_user_id: int,
    principal: Principal,
) -> LeaveRequest:
    """Applicant nominates an eligible replacement substitute after decline (EL-UC-019)."""
    req = get_request_by_id(request_id, principal)

    if req.user_id != principal.user_id:
        raise BadRequestError("Only the applicant may nominate a replacement substitute.")

    try:
        sub_intervals = get_substitute_active_intervals(replacement_user_id)
        validate_substitute(
            req.user_id,
            replacement_user_id,
            sub_intervals,
            req.start_date,
            req.end_date,
        )
    except LeaveDomainError as err:
        raise _translate_error(err) from err

    with transaction.atomic():
        req.substitute_user_id = replacement_user_id
        req.substitute_status = SubstituteStatus.PENDING.value
        req.save(update_fields=["substitute_user_id", "substitute_status", "updated_at"])

        req = execute_transition(
            request_id=req.id,
            event=Event.NOMINATE_REPLACEMENT,
            actor_user_id=principal.user_id,
            actor_role="applicant",
            remarks=f"Nominated replacement substitute (User ID: {replacement_user_id})",
        )

        # Start new substitute SLA clock
        SlaTaskClock.objects.create(
            request=req,
            task_type="substitute_response",
            assigned_to_user_id=replacement_user_id,
            assigned_to_role="substitute",
            state=req.status,
        )

        return req
