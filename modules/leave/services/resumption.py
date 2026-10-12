from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.models import LeaveRequest, Resumption
from modules.leave.services import authz

P_SUBMIT_RESUMPTION = "leave.request.create"
P_REVIEW_RESUMPTION = "leave.resumption.verify"


@transaction.atomic
def submit_resumption(*, actor, request_id: int, resumed_on: date) -> Resumption:
    """EL-UC-011, BR-EL-027: Submit a resumption for a leave request."""
    authz.require(actor, P_SUBMIT_RESUMPTION)
    request = LeaveRequest.objects.select_for_update().filter(pk=request_id).first()
    if request is None:
        raise NotFoundError("No such leave request.")
    if request.status != "approved":
        raise ConflictError("Only approved requests can be resumed.")
    if resumed_on <= request.end_date:
        outcome = "early"
    elif resumed_on == request.end_date + timedelta(days=1):
        outcome = "normal"
    else:
        outcome = "late"
    return Resumption.objects.create(
        request=request,
        resumed_on=resumed_on,
        outcome=outcome,
        status="submitted",
        reviewed_by_user_id=None,
        reviewed_at=None,
    )


@transaction.atomic
def review_resumption(*, actor, resumption_id: int, accept: bool) -> Resumption:
    """EL-UC-011, BR-EL-028: Review a submitted resumption."""
    authz.require(actor, P_REVIEW_RESUMPTION)
    resumption = Resumption.objects.select_for_update().filter(pk=resumption_id).first()
    if resumption is None:
        raise NotFoundError("No such resumption.")
    if resumption.status != "submitted":
        raise ConflictError("Only submitted resumptions can be reviewed.")
    resumption.status = "accepted" if accept else "rejected"
    resumption.reviewed_by_user_id = actor.user_id
    resumption.reviewed_at = timezone.now()
    resumption.save(update_fields=["status", "reviewed_by_user_id", "reviewed_at"])
    return resumption
