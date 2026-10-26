from __future__ import annotations

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain.state_machine import (
    APPROVED,
    REJECTED,
    ROUTING,
    SANCTION,
    InvalidTransition,
    assert_transition,
)
from modules.leave.models import LeaveBalance, LeaveRequest, RequestAction
from modules.leave.services import authz

P_REVIEW = "leave.request.review"
P_ROUTE = "leave.request.route"
P_SANCTION = "leave.request.sanction"


def _move(request, actor, action, target, note):
    from_status = request.status
    try:
        assert_transition(from_status, target)
    except InvalidTransition as exc:
        raise ConflictError(str(exc), code="bad_transition") from exc
    request.status = target
    request.save(update_fields=["status"])
    RequestAction.objects.create(
        request=request,
        actor_user_id=actor.user_id,
        action=action,
        from_status=from_status,
        to_status=target,
        note=note,
    )


def _consume_balance(request):
    LeaveBalance.objects.filter(
        user_id=request.user_id, year=request.start_date.year, category=request.category
    ).update(used=F("used") + request.days)


@transaction.atomic
def review(
    *, actor, scope, request_id: int, outcome: str, note=""
):  # BR-EL-016, BR-EL-017: review and route leave request.
    authz.require(actor, P_REVIEW)
    if not scope.filter(pk=request_id).exists():
        raise NotFoundError("No such leave request.", code="not_found")
    request = LeaveRequest.objects.select_for_update().get(pk=request_id)
    request.decided_by_user_id = actor.user_id
    request.decided_at = timezone.now()
    request.decision_note = note
    if request.category in ["CL", "RH"]:
        if outcome == "approve":
            _move(request, actor, "review", APPROVED, note)
            _consume_balance(request)
        elif outcome == "reject":
            _move(request, actor, "review", REJECTED, note)
        else:
            raise ConflictError("Invalid outcome for category CL or RH.", code="bad_outcome")
    else:
        if outcome in ["recommend", "not_recommend"]:
            request.recommendation = outcome
            _move(request, actor, "review", ROUTING, note)
        else:
            raise ConflictError("Invalid outcome for other categories.", code="bad_outcome")
    return request


@transaction.atomic
def route(
    *, actor, scope, request_id: int, note=""
):  # BR-EL-018, BR-EL-019: route leave request for higher sanction.
    authz.require(actor, P_ROUTE)
    if not scope.filter(pk=request_id).exists():
        raise NotFoundError("No such leave request.", code="not_found")
    request = LeaveRequest.objects.select_for_update().get(pk=request_id)
    _move(request, actor, "route", SANCTION, note)
    return request


@transaction.atomic
def sanction(
    *, actor, scope, request_id: int, decision: str, note=""
):  # BR-EL-020: final sanction of leave request.
    authz.require(actor, P_SANCTION)
    if not scope.filter(pk=request_id).exists():
        raise NotFoundError("No such leave request.", code="not_found")
    request = LeaveRequest.objects.select_for_update().get(pk=request_id)
    request.decided_by_user_id = actor.user_id
    request.decided_at = timezone.now()
    request.decision_note = note
    if decision == "approve":
        _move(request, actor, "sanction", APPROVED, note)
        _consume_balance(request)
    elif decision == "reject":
        _move(request, actor, "sanction", REJECTED, note)
    else:
        raise ConflictError("Invalid decision.", code="bad_decision")
    return request
