from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain.categories import is_eligible
from modules.leave.domain.counting import count_days
from modules.leave.domain.state_machine import assert_transition
from modules.leave.models import Holiday, LeaveBalance, LeaveRequest, RequestAction
from modules.leave.services import authz
from modules.leave.services.admin import ensure_balances

P_APPLY = "leave.request.create"
P_WITHDRAW = P_CANCEL = "leave.request.create"
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
        Holiday.objects.filter(
            is_published=True, date__gte=start_date, date__lte=end_date
        ).values_list("date", flat=True)
    )
    days = count_days(category, start_date, end_date, is_half_day, holidays)

    ensure_balances(user_id=actor.user_id, year=start_date.year)
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=actor.user_id, year=start_date.year, category=category
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

    ensure_balances(user_id=request.user_id, year=request.start_date.year)
    balance = LeaveBalance.objects.select_for_update().get(
        user_id=request.user_id, year=request.start_date.year, category=request.category
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

    request = (
        LeaveRequest.objects.select_for_update()
        .filter(pk=request_id, substitute_user_id=actor.user_id, status="substitute_pending")
        .first()
    )
    if request is None:
        raise NotFoundError("No such substitute request.", code="not_found")

    from_status = request.status
    if accept:
        request.substitute_status = "accepted"
        request.status = "unit_review"
    else:
        request.substitute_status = "declined"

    request.save(update_fields=["substitute_status", "status", "updated_at"])

    RequestAction.objects.create(
        request=request,
        actor_user_id=actor.user_id,
        action="substitute_accepted" if accept else "substitute_declined",
        from_status=from_status,
        to_status=request.status,
    )

    return request
