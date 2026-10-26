"""The substitute's answer and the applicant's replacement nomination (EL-UC-002, EL-UC-019)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain import state_machine as sm
from modules.leave.domain.overlap import Interval
from modules.leave.models import LeaveRequest, Substitution
from modules.leave.services import applications, authz, workflow


@transaction.atomic
def respond(*, substitution_id: int, accept: bool, actor, remarks: str = "") -> LeaveRequest:
    authz.require(actor, "leave.substitution.review")
    sub = Substitution.objects.filter(pk=substitution_id,
                                      substitute_user_id=actor.user_id).first()
    if sub is None:
        raise NotFoundError("No such substitute request.")
    req = workflow.lock_request(sub.request_id)
    sub = Substitution.objects.select_for_update().get(pk=sub.pk)
    if sub.status != Substitution.PENDING or req.status != sm.AWAITING_SUBSTITUTE:
        raise ConflictError("This request is no longer waiting for your answer.",
                            code="no_longer_pending")
    if accept:
        problems = applications.nominee_problems(
            req.user_id, actor.user_id, Interval(req.start_date, req.end_date, req.half))
        if problems:
            raise ConflictError(problems[0].message, code=problems[0].code)
    elif not remarks.strip():
        raise ConflictError("Tell the applicant why you cannot cover for them.",
                            code="reason_required")
    sub.status = Substitution.ACCEPTED if accept else Substitution.DECLINED
    sub.responded_at, sub.remarks = timezone.now(), remarks[:300]
    sub.save(update_fields=["status", "responded_at", "remarks", "updated_at"])
    return workflow.move(req, sm.SUBSTITUTE_ACCEPT if accept else sm.SUBSTITUTE_DECLINE,
                         actor_lane=sm.SUBSTITUTE, actor=actor,
                         outcome="accepted" if accept else "declined", remarks=remarks)


@transaction.atomic
def renominate(*, request_id: int, nominee_id: int, actor) -> LeaveRequest:
    authz.require(actor, "leave.request.create")
    req = workflow.lock_request(request_id, LeaveRequest.objects.filter(user_id=actor.user_id))
    if req.status != sm.APPLICANT_ACTION:
        raise ConflictError("A replacement substitute can be nominated only after the previous "
                            "one declined.", code="not_awaiting_replacement")
    problems = applications.nominee_problems(
        req.user_id, nominee_id, Interval(req.start_date, req.end_date, req.half))
    if problems:
        raise applications.ValidationFailed(problems[0].message, code=problems[0].code)
    Substitution.objects.create(request=req, substitute_user_id=nominee_id)
    return workflow.move(req, sm.RENOMINATE, actor_lane=sm.EMPLOYEE, actor=actor,
                         outcome="renominated", substitute_id=nominee_id)
