"""Recording decisions: review, route, sanction and resumption.

Thin on purpose. Each function picks the event the officer's outcome means and
hands it to the one transactional choke point, so the guards and the ledger
effects cannot be reached by a second route (EL-UC-003 to EL-UC-005, EL-UC-011).
"""
from __future__ import annotations

import logging
from datetime import date

from django.db.models import QuerySet

from core.api.exceptions import NotFoundError
from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest
from modules.leave.selectors import scoping
from modules.leave.services import authz
from modules.leave.services import requests as request_service

log = logging.getLogger("fusion.leave.reviews")


def my_queue(actor) -> QuerySet[LeaveRequest]:
    """The requests waiting on the designations this actor is acting as."""
    if scoping.sees_everything(actor):
        return LeaveRequest.objects.order_by("submitted_at", "id")
    return scoping.requests_for(actor).order_by("submitted_at", "id")


def decide(*, actor, request_id: int, event: str, reason: str = "",
           recommendation: str = "", scope=None) -> LeaveRequest:
    """Record whatever the resolved path lets this officer record.

    The same entry point covers a Unit Head deciding CL/RH, a Unit Head
    recommending a higher-sanction case, the Establishment forwarding it and the
    sanctioning authority deciding it: which applies is the state machine's
    answer, not a parameter a caller may choose.
    """
    if event in (sm.APPROVE, sm.REJECT):
        authz.require(actor, "leave.request.review", "leave.request.approve")
    else:
        authz.require(actor, "leave.request.review")

    return request_service.transition(
        request_id=request_id, event=event, actor=actor, reason=reason,
        recommendation=recommendation, scope=scope)


def approve(*, actor, request_id: int, reason: str = "", scope=None) -> LeaveRequest:
    return decide(actor=actor, request_id=request_id, event=sm.APPROVE,
                  reason=reason, scope=scope)


def reject(*, actor, request_id: int, reason: str, scope=None) -> LeaveRequest:
    return decide(actor=actor, request_id=request_id, event=sm.REJECT,
                  reason=reason, scope=scope)


def recommend(*, actor, request_id: int, recommended: bool, reason: str = "",
              scope=None) -> LeaveRequest:
    """BR-EL-017: Not Recommended is a recorded recommendation, not a rejection."""
    return decide(actor=actor, request_id=request_id, event=sm.RECOMMEND,
                  recommendation="recommended" if recommended else "not_recommended",
                  reason=reason, scope=scope)


def forward(*, actor, request_id: int, reason: str = "", scope=None) -> LeaveRequest:
    """EL-UC-004: the Establishment step passes the request to the authority."""
    authz.require(actor, "leave.request.review")
    return request_service.transition(request_id=request_id, event=sm.FORWARD,
                                      actor=actor, reason=reason, scope=scope)


def submit_resumption(*, actor, request_id: int, actual_date: date,
                      notes: str = "") -> LeaveRequest:
    """EL-UC-010: only EL, COL and VL have a formal resumption review."""
    authz.require(actor, "leave.resumption.create")
    return request_service.transition(
        request_id=request_id, event=sm.SUBMIT_RESUMPTION, actor=actor,
        reason=notes, context={"actual_date": actual_date})


def resumption_event(*, approved_end: date, actual: date) -> str:
    """Which review event an actual return date means (BR-EL-028)."""
    return sm.resumption_event(actual=actual, approved_end=approved_end)


def review_resumption(*, actor, request_id: int, actual_date: date,
                      notes: str = "", scope=None) -> LeaveRequest:
    """Record the review of a submitted resumption (EL-UC-011)."""
    authz.require(actor, "leave.resumption.review")
    current = LeaveRequest.objects.filter(pk=request_id).first()
    if current is None:
        raise NotFoundError("No such leave request.")
    event = resumption_event(approved_end=current.end_date, actual=actual_date)
    return request_service.transition(request_id=request_id, event=event,
                                      actor=actor, reason=notes,
                                      context={"actual_date": actual_date},
                                      scope=scope)


def resumption_review_applies(row: LeaveRequest) -> bool:
    return cat.is_resumption_reviewed(row.category)


def reviewable_outcomes(row: LeaveRequest) -> tuple[str, ...]:
    """What this request's current step may record, from the transition table."""
    kind = authz.actor_kind(None, row=row)
    return tuple(sm.allowed_events(row.status, kind))
