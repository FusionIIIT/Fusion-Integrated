"""Substitute workflow services (BR-EL-014, BR-EL-015, EL-UC-002, EL-UC-019)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.leave.models import LeaveActionHistory, LeaveApplication, SubstituteRequest
from modules.leave.selectors.applications import get_active_overlapping_leaves, get_application_by_id
from modules.leave.services.notifications import enqueue as enqueue_notification


@transaction.atomic
def respond_to_substitute_request(*, substitute_user_id: int, request_id: int, decision: str, remarks: str = "") -> SubstituteRequest:
    """Substitute colleague accepts or declines responsibility (EL-UC-002, BR-EL-015)."""
    try:
        application_id = SubstituteRequest.objects.only("application_id").get(pk=request_id, substitute_user_id=substitute_user_id).application_id
    except SubstituteRequest.DoesNotExist:
        raise NotFoundError("Substitute request not found.", code="substitute_request_not_found")
    app = get_application_by_id(application_id, for_update=True)
    try:
        sub_req = SubstituteRequest.objects.select_for_update().get(pk=request_id, substitute_user_id=substitute_user_id)
    except SubstituteRequest.DoesNotExist:
        raise NotFoundError("Substitute request not found.", code="substitute_request_not_found")
    if not sub_req.is_current:
        raise ConflictError("This substitute request has been superseded.", code="stale_substitute_request")
    if app.status != "substitute_pending":
        raise ConflictError(f"The leave application is no longer awaiting substitute consent (status {app.status!r}).", code="application_not_pending_substitute")
    if sub_req.status != "pending":
        raise ConflictError(f"Request is already {sub_req.status}.", code="already_responded")
    if decision not in ("accepted", "declined"):
        raise BadRequestError("Decision must be 'accepted' or 'declined'.", code="invalid_decision")
    sub_req.status = decision
    sub_req.response_remarks = remarks
    sub_req.responded_at = timezone.now()
    sub_req.save(update_fields=["status", "response_remarks", "responded_at", "updated_at"])
    if decision == "accepted":
        app.status = "under_review"
        app.save(update_fields=["status", "updated_at"])
        enqueue_notification(recipient_user_id=app.unit_head_user_id or app.sanctioning_authority_user_id, topic="application.assigned", dedupe_key=f"leave:{app.pk}:review-assigned", subject="Leave request requires review", body=f"Substitute consent was received for request #{app.pk}; review can proceed.")
        LeaveActionHistory.objects.create(application=app, actor_user_id=substitute_user_id, actor_role="substitute", action="substitute_accepted", remarks=remarks)
    else:
        LeaveActionHistory.objects.create(application=app, actor_user_id=substitute_user_id, actor_role="substitute", action="substitute_declined", remarks=remarks)
        enqueue_notification(recipient_user_id=app.user_id, topic="substitute.declined", dedupe_key=f"leave:{app.pk}:substitute-declined:{sub_req.pk}", subject="Substitute declined the leave request", body=f"The nominated substitute declined request #{app.pk}. Nominate a replacement or withdraw the request.")
    return sub_req


@transaction.atomic
def re_nominate_substitute(*, user_id: int, application_id: int, new_substitute_user_id: int, responsibilities: str = "") -> SubstituteRequest:
    """Nominate replacement substitute after previous declined (EL-UC-019, BR-EL-015)."""
    app = get_application_by_id(application_id, user_id=user_id, for_update=True)
    if app.status != "substitute_pending":
        raise ConflictError("Substitute can only be re-nominated while application is pending substitute consent.", code="not_pending_substitute")
    if new_substitute_user_id == user_id:
        raise BadRequestError("You cannot nominate yourself as your substitute.", code="substitute_self")
    from modules.directory import contracts as directory
    substitute = directory.get_users([new_substitute_user_id]).get(new_substitute_user_id)
    if substitute is None or substitute.kind not in {"faculty", "staff"}:
        raise BadRequestError("Substitute must be another active employee.", code="invalid_substitute")
    if get_active_overlapping_leaves(new_substitute_user_id, app.start_date, app.end_date).exists():
        raise ConflictError("Nominated substitute has pending or approved leave during this period.", code="substitute_unavailable")
    SubstituteRequest.objects.filter(application=app).update(is_current=False)
    new_req = SubstituteRequest.objects.create(application=app, substitute_user_id=new_substitute_user_id, responsibilities=responsibilities, status="pending", is_current=True)
    enqueue_notification(recipient_user_id=new_substitute_user_id, topic="substitute.assigned", dedupe_key=f"leave:{app.pk}:substitute:{new_substitute_user_id}", subject="Leave responsibility request", body=f"You have been nominated as a substitute for leave request #{app.pk}.")
    LeaveActionHistory.objects.create(application=app, actor_user_id=user_id, actor_role="employee", action="substitute_renominated", remarks=f"Re-nominated u{new_substitute_user_id}")
    return new_req
