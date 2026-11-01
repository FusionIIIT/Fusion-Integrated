"""The substitute's response and the recovery after a decline.

The consent gate is what BR-EL-015 is about: routing does not move while it is
closed, and a decline leaves it closed while opening the applicant's own
recovery route (EL-UC-002, EL-UC-019).
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest, SubstituteAssignment
from modules.leave.services import authz
from modules.leave.services import requests as request_service

log = logging.getLogger("fusion.leave.substitutes")


def pending_for(*, request_id: int, user_id: int) -> SubstituteAssignment:
    assignment = (SubstituteAssignment.objects
                  .filter(request_id=request_id, substitute_user_id=user_id,
                          state="pending")
                  .order_by("-id").first())
    if assignment is None:
        raise NotFoundError("You have no pending responsibility request for that leave.")
    return assignment


@transaction.atomic
def respond(*, actor, request_id: int, accept: bool, reason: str = ""
            ) -> LeaveRequest:
    """EL-UC-002: accept or decline; a stale response is refused."""
    authz.require(actor, "leave.substitute.review")
    row = LeaveRequest.objects.filter(pk=request_id).first()
    if row is None:
        raise NotFoundError("No such leave request.")
    if row.status not in (sm.AWAITING_SUBSTITUTE, sm.EXTENSION_AWAITING_SUBSTITUTE):
        raise ConflictError(
            "This request is no longer waiting for a substitute response.",
            code="stale_substitute_response")

    assignment = pending_for(request_id=request_id,
                             user_id=getattr(actor, "user_id", None))
    assignment.state = "accepted" if accept else "declined"
    assignment.reason = reason
    assignment.responded_at = timezone.now()
    assignment.save(update_fields=["state", "reason", "responded_at", "updated_at"])

    event = sm.ACCEPT if accept else sm.DECLINE
    moved = request_service.transition(request_id=request_id, event=event,
                                       actor=actor, reason=reason)
    log.info("leave.substitute.%s request=%s substitute=%s", assignment.state,
             request_id, assignment.substitute_user_id)
    return moved


@transaction.atomic
def nominate_replacement(*, actor, request_id: int, substitute_user_id: int
                         ) -> LeaveRequest:
    """EL-UC-019: exactly one replacement after a decline (BR-EL-015)."""
    authz.require(actor, "leave.request.create")
    row = LeaveRequest.objects.filter(pk=request_id).first()
    if row is None:
        raise NotFoundError("No such leave request.")
    if row.status not in (sm.APPLICANT_ACTION_REQUIRED,
                          sm.EXTENSION_APPLICANT_ACTION_REQUIRED):
        raise ConflictError(
            "This request is not waiting for you to nominate a replacement.",
            code="no_replacement_due")

    request_service.nominate_substitute(request=row,
                                       substitute_user_id=substitute_user_id,
                                       actor=actor)
    return request_service.transition(request_id=request_id, event=sm.REPLACE,
                                      actor=actor)
