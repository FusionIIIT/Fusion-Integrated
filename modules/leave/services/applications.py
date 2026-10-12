from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import is_eligible
from modules.leave.domain.counting import count_days
from modules.leave.domain.state_machine import assert_transition
from modules.leave.models import LeaveBalance, LeaveRequest, RequestAction
from modules.leave.services import authz

P_APPLY = "leave.request.create"
P_WITHDRAW = "leave.request.withdraw"
P_CANCEL = "leave.request.cancel"
P_SUBSTITUTE_RESPONSE = "leave.substitute.respond"


@transaction.atomic
def apply(
    *,
    actor,
    category,
    start_date,
    end_date,
    purpose,
    is_half_day=False,
    half_session="",
    station_leave=False,
    station_address="",
    substitute_user_id=None,
    unit_id=None,
    is_faculty=False,
) -> LeaveRequest:
    """EL-UC-001/002/007/008, BR-EL-001/010/011/012/013/015/022/023/034"""
    authz.require(actor, P_APPLY)

    if not is_eligible(category, is_faculty):
        raise ConflictError(
            f"Category {category} is not eligible for this user.", code="category_not_eligible"
        )

    holidays = set(
        holiday.date
        for holiday in LeaveRequest.objects.filter(
            start_date__lte=end_date, end_date__gte=start_date
        ).values_list("start_date", flat=True)
    )
    days = count_days(category, start_date, end_date, is_half_day, holidays)

    balance = LeaveBalance.objects.get(
        user_id=actor.user_id, year=timezone.now().year, category=category
    )
    if balance.entitled - balance.used < days:
        raise ConflictError(
            f"Not enough balance for {category} leave.", code="insufficient_balance"
        )

    if LeaveRequest.objects.filter(
        user_id=actor.user_id,
        status__in=["substitute_pending", "unit_review", "routing", "sanction"],
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists():
        raise ConflictError("Overlap with existing leave request.", code="overlap_error")

    request = LeaveRequest.objects.create(
        user_id=actor.user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_session=half_session,
        days=days,
        purpose=purpose,
        station_leave=station_leave,
        station_address=station_address,
        substitute_user_id=substitute_user_id,
        unit_id=unit_id,
        status="substitute_pending" if substitute_user_id else "unit_review",
    )

    RequestAction.objects.create(
        request=request,
        actor_user_id=actor.user_id,
        action="create",
        from_status="",
        to_status=request.status,
    )

    return request


@transaction.atomic
def withdraw(*, actor, request_id) -> LeaveRequest:
    """EL-UC-002, BR-EL-022"""
    authz.require(actor, P_WITHDRAW)

    request = LeaveRequest.objects.select_for_update().get(
        pk=request_id,
        user_id=actor.user_id,
        status__in=["substitute_pending", "unit_review", "routing"],
    )
    assert_transition(request.status, "withdrawn")

    request.status = "withdrawn"
    request.decided_at = timezone.now()
    request.decided_by_user_id = actor.user_id
    request.decision_note = "Withdrawn by user"
    request.save(update_fields=["status", "decided_at", "decided_by_user_id", "decision_note"])

    RequestAction.objects.create(
        request=request,
        actor_user_id=actor.user_id,
        action="withdraw",
        from_status=request.status,
        to_status=request.status,
    )

    return request


@transaction.atomic
def request_cancellation(*, actor, request_id) -> LeaveRequest:
    """EL-UC-007, BR-EL-023"""
    authz.require(actor, P_CANCEL)

    request = LeaveRequest.objects.select_for_update().get(
        pk=request_id, user_id=actor.user_id, status="approved", start_date__gt=timezone.now()
    )
    assert_transition(request.status, "cancelled")

    request.status = "cancelled"
    request.decided_at = timezone.now()
    request.decided_by_user_id = actor.user_id
    request.decision_note = "Cancelled by user"
    request.save(update_fields=["status", "decided_at", "decided_by_user_id", "decision_note"])

    balance = LeaveBalance.objects.get(
        user_id=actor.user_id, year=timezone.now().year, category=request.category
    )
    balance.used -= request.days
    balance.save(update_fields=["used"])

    RequestAction.objects.create(
        request=request,
        actor_user_id=actor.user_id,
        action="cancel",
        from_status=request.status,
        to_status=request.status,
    )

    return request


@transaction.atomic
def respond_substitute(*, actor, request_id, accept: bool) -> LeaveRequest:
    """EL-UC-002, BR-EL-015"""
    authz.require(actor, P_SUBSTITUTE_RESPONSE)

    request = LeaveRequest.objects.select_for_update().get(
        pk=request_id, substitute_user_id=actor.user_id, status="substitute_pending"
    )
    assert_transition(request.status, "unit_review" if accept else "substitute_response")

    request.substitute_status = "accepted" if accept else "declined"
    request.decided_at = timezone.now()
    request.decided_by_user_id = actor.user_id
    request.decision_note = "Substitute response" if accept else "Substitute declined"
    request.save(
        update_fields=["substitute_status", "decided_at", "decided_by_user_id", "decision_note"]
    )

    RequestAction.objects.create(
        request=request,
        actor_user_id=actor.user_id,
        action="substitute_response",
        from_status=request.status,
        to_status=request.status,
    )

    return request
