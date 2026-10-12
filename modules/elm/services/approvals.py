"""Approval decisions: unit head, establishment and final sanction.

Authority stages are frozen in `request.route` at submission, so a later policy
change cannot reroute an in-flight request (BR-EL-030). Approving a request is
the only place a balance is moved.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.elm.domain import enums as e
from modules.elm.domain import routing
from modules.elm.models import LeaveRequest
from modules.elm.services import accounts, notifications
from modules.elm.services.requests import advance


def _fail(code: str, message: str):
    raise ConflictError(message, code=code)


def _load(request_id: int) -> LeaveRequest:
    request = LeaveRequest.objects.select_related().filter(pk=request_id).first()
    if request is None:
        _fail("not_found", "No such leave request.")
    return request


# -- unit head -----------------------------------------------------------------
@transaction.atomic
def unit_head_decide(*, actor, request_id: int, decision: str,
                     note: str = "") -> LeaveRequest:
    request = _load(request_id)
    if request.status != e.AWAITING_UNIT_HEAD:
        _fail("wrong_stage", "This request is not awaiting the unit head.")
    unit_head_final = request.category in e.UNIT_HEAD_FINAL

    if unit_head_final:
        if decision not in (e.APPROVE, e.REJECT):
            _fail("bad_decision", "A final decision must approve or reject.")
        to_status = e.APPROVED if decision == e.APPROVE else e.REJECTED
        _finish(request, to_status=to_status, decision=decision,
                actor_user_id=actor.user_id, actor_role=e.UNIT_HEAD, note=note)
    else:
        if decision not in (e.RECOMMENDED, e.NOT_RECOMMENDED):
            _fail("bad_decision",
                  "The unit head records a recommendation, not a decision.")
        to_status = routing.status_after_unit_head(
            category=request.category,
            establishment_required=bool(
                (request.route or {}).get("establishment_required")))
        advance(request=request, to_status=to_status, actor_user_id=actor.user_id,
                actor_role=e.UNIT_HEAD, note=note, decision=decision)
    return request


# -- establishment -------------------------------------------------------------
@transaction.atomic
def establishment_forward(*, actor, request_id: int, note: str = "") -> LeaveRequest:
    request = _load(request_id)
    if request.status != e.AWAITING_ESTABLISHMENT:
        _fail("wrong_stage", "This request is not awaiting establishment.")
    advance(request=request, to_status=e.AWAITING_FINAL_SANCTION,
            actor_user_id=actor.user_id, actor_role=e.ESTABLISHMENT, note=note,
            decision="verified")
    return request


# -- final sanction ------------------------------------------------------------
@transaction.atomic
def final_sanction(*, actor, request_id: int, decision: str, note: str = "",
                   role: str = e.SANCTION) -> LeaveRequest:
    request = _load(request_id)
    if request.status not in (e.AWAITING_FINAL_SANCTION,
                              e.AWAITING_DIRECTOR_SANCTION):
        _fail("wrong_stage", "This request is not awaiting final sanction.")
    director_stage = request.status == e.AWAITING_DIRECTOR_SANCTION
    if director_stage and role != e.DIRECTOR:
        _fail("wrong_actor", "Final sanction here rests with the Director.")
    actor_role = e.DIRECTOR if director_stage else e.SANCTION

    if decision not in (e.APPROVE, e.REJECT):
        _fail("bad_decision", "A sanction decision must approve or reject.")
    if decision == e.REJECT and not note:
        _fail("reason_required", "A rejection must record a reason.")

    to_status = e.APPROVED if decision == e.APPROVE else e.REJECTED
    _finish(request, to_status=to_status, decision=decision,
            actor_user_id=actor.user_id, actor_role=actor_role, note=note)
    return request


def _finish(request: LeaveRequest, *, to_status: str, decision: str,
            actor_user_id: int, actor_role: str, note: str) -> None:
    advance(request=request, to_status=to_status, actor_user_id=actor_user_id,
            actor_role=actor_role, note=note, decision=decision)
    if to_status == e.APPROVED:
        _apply_approval(request, actor_user_id=actor_user_id)
        topic, subject, body, tag = (
            "request.approved", f"Leave request #{request.pk} approved",
            "Your leave request has been sanctioned.",
            "approved")
    else:
        request.rejection_reason = note
        request.final_decision = e.REJECT
        request.decided_by_user_id = actor_user_id
        request.decided_at = timezone.now()
        request.save(update_fields=["rejection_reason", "final_decision",
                                    "decided_by_user_id", "decided_at",
                                    "updated_at"])
        topic, subject, body, tag = (
            "request.rejected", f"Leave request #{request.pk} rejected",
            note or "Your leave request was rejected.",
            "rejected")
    notifications.enqueue(
        topic=topic, dedupe_key=f"{tag}:req{request.pk}", subject=subject,
        body=body, recipient_user_id=request.user_id,
        payload={"request_id": request.pk})


def _apply_approval(request: LeaveRequest, *, actor_user_id: int) -> None:
    if request.kind == e.NEW:
        account = accounts.ensure_account(request.user_id, request.category,
                                         request.start_date.year)
        accounts.deduct(account=account, days=request.days, request=request,
                        actor_user_id=actor_user_id, note="Leave sanctioned")
    elif request.kind == e.CANCELLATION and request.original_id:
        original = request.original
        original.status = e.CANCELLED
        original.save(update_fields=["status", "updated_at"])
        account = accounts.ensure_account(original.user_id, original.category,
                                          original.start_date.year)
        accounts.restore(account=account, days=original.days, request=original,
                         actor_user_id=actor_user_id, note="Cancellation approved")
    elif request.kind == e.EXTENSION_KIND and request.original_id:
        account = accounts.ensure_account(request.user_id, request.category,
                                          request.start_date.year)
        accounts.deduct(account=account, days=request.days, request=request,
                        actor_user_id=actor_user_id, note="Extension sanctioned")
        original = request.original
        original.end_date = request.end_date
        original.days = original.days + request.days
        original.save(update_fields=["end_date", "days", "updated_at"])
    request.final_decision = e.APPROVE
    request.decided_by_user_id = actor_user_id
    request.decided_at = timezone.now()
    request.save(update_fields=["final_decision", "decided_by_user_id",
                                "decided_at", "updated_at"])
