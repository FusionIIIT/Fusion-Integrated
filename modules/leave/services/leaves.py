"""All writes to a leave request. Raises domain errors, not DRF."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest, LeaveTransition
from modules.leave.selectors import leaves as scoping


def actor_kind(actor, request=None) -> str:
    if actor is None:
        return sm.SYSTEM
    if scoping.is_staff(actor):
        return sm.AUTHORITY
    return sm.EMPLOYEE


def resolve_or_raise(frm: str, to: str, kind: str):
    try:
        return sm.resolve(frm, to, kind)
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"A leave cannot move from '{exc.frm}' to '{exc.to}'.",
            code="invalid_transition") from exc
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError(
            "Your role cannot do this step.") from exc


def submit_leave(*, user_id: int, category: str, start_date,
                 end_date, purpose: str = "", half_day: bool = False,
                 station_leave: bool = False, station_details: str = "",
                 substitute_user_id=None) -> LeaveRequest:
    req = LeaveRequest.objects.create(
        user_id=user_id, category=category,
        start_date=start_date, end_date=end_date,
        purpose=purpose, half_day=half_day,
        station_leave=station_leave, station_details=station_details,
        substitute_user_id=substitute_user_id, status=sm.DRAFT)
    if substitute_user_id:
        move(req, to_status=sm.AWAITING_SUB, actor=None)
    else:
        move(req, to_status=sm.UNIT_HEAD, actor=None)
    return req


def move(req: LeaveRequest, *, to_status: str, actor, reason: str = "") -> LeaveRequest:
    kind = actor_kind(actor, req)
    resolve_or_raise(req.status, to_status, kind)
    frm = req.status
    req.status = to_status
    req.save(update_fields=["status", "updated_at"])
    LeaveTransition.objects.create(
        request=req, from_status=frm, to_status=to_status,
        actor_user_id=getattr(actor, "user_id", None), reason=reason)
    return req


def transition(*, request_id: int, to_status: str, actor,
               reason: str = "", scope=None) -> LeaveRequest:
    qs = scope if scope is not None else LeaveRequest.objects.all()
    try:
        req = qs.get(pk=request_id)
    except LeaveRequest.DoesNotExist as exc:
        raise NotFoundError("Leave request not found.") from exc
    with transaction.atomic():
        locked = LeaveRequest.objects.select_for_update().get(pk=req.pk)
        return move(locked, to_status=to_status, actor=actor, reason=reason)
