"""Substitute consent (EL-UC-002, BR-EL-014/015)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.elm.domain import enums as e
from modules.elm.domain import routing
from modules.elm.models import SubstituteAssignment
from modules.elm.services import notifications
from modules.elm.services.requests import advance


def _fail(code: str, message: str):
    raise ConflictError(message, code=code)


@transaction.atomic
def respond(*, actor, assignment_id: int, accept: bool,
            reason: str = "") -> SubstituteAssignment:
    assignment = (SubstituteAssignment.objects
                  .select_related("request")
                  .filter(pk=assignment_id).first())
    if assignment is None or assignment.substitute_user_id != actor.user_id:
        _fail("not_found", "No such substitute request.")
    if assignment.status != "pending":
        _fail("already_responded", "You have already responded to this request.")

    request = assignment.request
    assignment.status = "accepted" if accept else "declined"
    assignment.responded_at = timezone.now()
    assignment.decline_reason = "" if accept else reason
    assignment.save(update_fields=["status", "responded_at", "decline_reason",
                                   "updated_at"])

    if accept:
        director = bool((request.route or {}).get("applicant_is_director"))
        to_status = routing.status_after_substitute(applicant_is_director=director)
        advance(request=request, to_status=to_status, actor_user_id=actor.user_id,
                actor_role=e.SUBSTITUTE)
    else:
        advance(request=request, to_status=e.APPLICANT_ACTION_REQUIRED,
                actor_user_id=actor.user_id, actor_role=e.SUBSTITUTE,
                note=reason)
        notifications.enqueue(
            topic="request.substitute_declined",
            dedupe_key=f"subdeclined:req{request.pk}",
            subject=f"Substitute declined request #{request.pk}",
            body="Your nominated substitute declined. Nominate a replacement or "
                 "withdraw the request.",
            recipient_user_id=request.user_id,
            payload={"request_id": request.pk})
    return assignment


def pending_for(actor):
    return SubstituteAssignment.objects.filter(
        substitute_user_id=actor.user_id, status="pending").select_related("request")
