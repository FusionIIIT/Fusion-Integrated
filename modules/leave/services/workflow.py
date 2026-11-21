"""The one choke point every request state change goes through.

`advance` locks the row, consults the transition table, checks that the caller
is the person the step belongs to, writes history and applies the ledger and
notification effects of the new state, all in one transaction.
"""
from __future__ import annotations

from collections.abc import Callable

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain.accounting import Reason
from modules.leave.domain.categories import LABELS, Category
from modules.leave.domain.workflow import (
    ASSIGNEE,
    PENDING,
    Actor,
    Decision,
    Event,
    IllegalTransition,
    Route,
    State,
    WrongActor,
    next_state,
    unit_head_event,
)
from modules.leave.models import LeaveRequest, LeaveTransition
from modules.leave.services import accounts
from modules.leave.services.notify import notify

_FIELD = {
    Actor.APPLICANT: "user_id",
    Actor.SUBSTITUTE: "substitute_user_id",
    Actor.UNIT_HEAD: "unit_head_user_id",
    Actor.ESTABLISHMENT: "establishment_user_id",
    Actor.SANCTIONING: "sanctioning_user_id",
}


def route_of(req: LeaveRequest) -> Route:
    return Route(unit_head_final=req.unit_head_final,
                 establishment=req.establishment_user_id is not None,
                 director_self=req.director_self)


def assignee_of(req: LeaveRequest) -> int | None:
    role = ASSIGNEE.get(State(req.status))
    return getattr(req, _FIELD[role]) if role else None


def _check_actor(req: LeaveRequest, role: Actor, user_id: int | None) -> None:
    if role is Actor.SYSTEM:
        return
    if user_id is None or getattr(req, _FIELD[role]) != user_id:
        raise PermissionDeniedError("This step of the request is assigned to someone else.",
                                    code="not_assignee")
    # BR-EL-020 is the only case where someone acts on their own leave.
    own = req.user_id == user_id and role is not Actor.APPLICANT
    if own and not (role is Actor.SANCTIONING and req.director_self):
        raise PermissionDeniedError("You cannot act on your own leave request.",
                                    code="self_action")


def _describe(req: LeaveRequest) -> str:
    what = {"new": "leave", "cancellation": "cancellation of leave",
            "extension": "extension of leave"}[req.kind]
    return (f"{LABELS[Category(req.category)]} {what} "
            f"{req.start_date:%d %b %Y} to {req.end_date:%d %b %Y} (request #{req.pk})")


def advance(request_id: int, event: Event, role: Actor, user_id: int | None, *,
            note: str = "", mutate: Callable[[LeaveRequest], None] | None = None
            ) -> LeaveRequest:
    with transaction.atomic():
        req = LeaveRequest.objects.select_for_update().filter(pk=request_id).first()
        if req is None:
            raise NotFoundError("That leave request does not exist.")
        try:
            target = next_state(State(req.status), event, role)
        except IllegalTransition as exc:
            raise ConflictError(str(exc), code="illegal_transition") from exc
        except WrongActor as exc:
            raise PermissionDeniedError(str(exc), code="wrong_actor") from exc
        _check_actor(req, role, user_id)
        previous = req.status
        now = timezone.now()
        req.status, req.status_changed_at = target.value, now
        if target in (State.APPROVED, State.REJECTED):
            req.decided_at = now
        if mutate:
            mutate(req)
        req.save()
        LeaveTransition.objects.create(request=req, from_status=previous,
                                       to_status=target.value, event=event.value,
                                       actor_user_id=user_id, note=note[:2000])
        _effects(req, target, user_id)
    return req


def _effects(req: LeaveRequest, target: State, user_id: int | None) -> None:
    if target in PENDING:
        notify([assignee_of(req)], "assigned",  # BR-EL-035
               f"Action needed: {_describe(req)}.", request=req)
    elif target is State.APPROVED and req.kind == LeaveRequest.CANCELLATION:
        _cancel_parent(req, user_id)
        notify([req.user_id], "decision", f"Approved: {_describe(req)}.", request=req)
    elif target is State.APPROVED:
        accounts.lock(req.user_id)
        accounts.post(req.user_id, Category(req.category), req.start_date.year, -req.days,
                      Reason.DEBIT, request=req, key=f"debit:{req.pk}", by=user_id)
        notify([req.user_id], "decision", f"Approved: {_describe(req)}.", request=req)
    elif target is State.REJECTED:
        notify([req.user_id], "decision", f"Not approved: {_describe(req)}.", request=req)
    elif target is State.WITHDRAWN:
        # BR-EL-022: everyone already involved learns processing has stopped.
        notify([req.substitute_user_id, req.unit_head_user_id, req.establishment_user_id,
                req.sanctioning_user_id], "withdrawn", f"Withdrawn: {_describe(req)}.",
               request=req)


def _cancel_parent(cancellation: LeaveRequest, user_id: int | None) -> None:
    """BR-EL-023: the original is marked Cancelled, not edited, and its debit returns."""
    parent = advance(cancellation.parent_id, Event.MARK_CANCELLED, Actor.SYSTEM, None,
                     note=f"Cancelled by request #{cancellation.pk}")
    spent = parent.ledger.aggregate(t=Sum("days"))["t"]
    if spent and spent < 0:
        accounts.lock(parent.user_id)
        accounts.post(parent.user_id, Category(parent.category), parent.start_date.year,
                      -spent, Reason.RESTORE, request=parent, key=f"restore:{parent.pk}",
                      by=user_id)


def review_at_unit_head(request_id: int, user_id: int, decision: Decision,
                        note: str = "") -> LeaveRequest:
    """EL-UC-003."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if req is None:
        raise NotFoundError("That leave request does not exist.")
    try:
        event = unit_head_event(route_of(req), decision)
    except IllegalTransition as exc:
        raise ConflictError(str(exc), code="wrong_decision") from exc

    def record(r: LeaveRequest) -> None:
        if not r.unit_head_final:
            r.recommendation = decision.value

    return advance(request_id, event, Actor.UNIT_HEAD, user_id, note=note, mutate=record)


def route_at_establishment(request_id: int, user_id: int, note: str = "") -> LeaveRequest:
    """EL-UC-004."""
    return advance(request_id, Event.ESTABLISHMENT_ROUTE, Actor.ESTABLISHMENT, user_id,
                   note=note)


def final_decision(request_id: int, user_id: int, approve: bool,
                   note: str = "") -> LeaveRequest:
    """EL-UC-005."""
    event = Event.FINAL_APPROVE if approve else Event.FINAL_REJECT
    return advance(request_id, event, Actor.SANCTIONING, user_id, note=note)
