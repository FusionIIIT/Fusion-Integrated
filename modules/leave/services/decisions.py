from __future__ import annotations

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.leave.domain.state_machine import assert_transition
from modules.leave.models import LeaveBalance, LeaveRequest, RequestAction
from modules.leave.services import authz

P_REVIEW = "leave.request.review"
P_ROUTE = "leave.request.route"
P_SANCTION = "leave.request.sanction"


@transaction.atomic
def review(*, actor, scope, request_id: int, outcome: str, note: str = "") -> None:
    """BR-EL-016, BR-EL-017: review and route leave request."""
    authz.require(actor, P_REVIEW)
    if not scope.filter(pk=request_id).exists():
        raise NotFoundError("No such leave request.", code="not_found")
    request = LeaveRequest.objects.select_for_update().get(pk=request_id)
    assert_transition(request.status, "review")
    request.decided_by_user_id = actor.user_id
    request.decided_at = timezone.now()
    request.decision_note = note
    if request.category in ["CL", "RH"]:
        request.status = "approved" if outcome == "approve" else "rejected"
    else:
        request.status = "recommended" if outcome == "recommend" else "not_recommended"
    request.save(update_fields=["decided_by_user_id", "decided_at", "decision_note", "status"])
    RequestAction.objects.create(
        request=request,
        actor_user_id=actor.user_id,
        action="review",
        from_status=request.status,
        to_status=request.status,
        note=note,
    )


@transaction.atomic
def route(*, actor, scope, request_id: int, note: str = "") -> None:
    """BR-EL-018, BR-EL-019: route leave request for higher sanction."""
    authz.require(actor, P_ROUTE)
    if not scope.filter(pk=request_id).exists():
        raise NotFoundError("No such leave request.", code="not_found")
    request = LeaveRequest.objects.select_for_update().get(pk=request_id)
    assert_transition(request.status, "route")
    request.status = "routing"
    request.save(update_fields=["status"])
    RequestAction.objects.create(
        request=request,
        actor_user_id=actor.user_id,
        action="route",
        from_status=request.status,
        to_status=request.status,
        note=note,
    )


@transaction.atomic
def sanction(*, actor, scope, request_id: int, decision: str, note: str = "") -> None:
    """BR-EL-020: final sanction of leave request."""
    authz.require(actor, P_SANCTION)
    if not scope.filter(pk=request_id).exists():
        raise NotFoundError("No such leave request.", code="not_found")
    request = LeaveRequest.objects.select_for_update().get(pk=request_id)
    assert_transition(request.status, "sanction")
    request.decided_by_user_id = actor.user_id
    request.decided_at = timezone.now()
    request.decision_note = note
    if decision == "approve":
        request.status = "approved"
        request.save(update_fields=["decided_by_user_id", "decided_at", "decision_note", "status"])
        if request.category in ["EL", "COL", "VL"]:
            LeaveBalance.objects.filter(
                user_id=request.user_id, year=request.placement_year, category=request.category
            ).update(used=F("used") + request.days)
    else:
        request.status = "rejected"
        request.save(update_fields=["decided_by_user_id", "decided_at", "decision_note", "status"])
    RequestAction.objects.create(
        request=request,
        actor_user_id=actor.user_id,
        action="sanction",
        from_status=request.status,
        to_status=request.status,
        note=note,
    )
