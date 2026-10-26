"""Query selectors for Employee Leave Management (ELM).

Reads leave applications, balances, and pending approval queues.
Annotates legacy records without modifying stored database rows.
"""
from __future__ import annotations

import datetime
from django.db.models import QuerySet
from .models import LeaveBalance, LeaveRequest
from .domain import state_machine as sm


def _resolve_user_id(user_or_id: int | object) -> int:
    """Extract integer user_id from integer, IAM Principal, or User object."""
    if isinstance(user_or_id, int):
        return user_or_id
    actor_id = getattr(getattr(user_or_id, "principal", None), "user_id", None)
    if actor_id is not None:
        return actor_id
    return getattr(user_or_id, "user_id", getattr(user_or_id, "id", None))


def get_leave_requests_for_user(user_or_id: int | object) -> QuerySet[LeaveRequest]:
    """Retrieve all leave applications submitted by the given user, ordered by date."""
    user_id = _resolve_user_id(user_or_id)
    return LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")


def get_balances_for_user(user_or_id: int | object, year: int | None = None) -> QuerySet[LeaveBalance]:
    """Retrieve annual leave balances for the given user."""
    user_id = _resolve_user_id(user_or_id)
    if year is None:
        year = datetime.date.today().year
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("category")


def get_pending_substitute_requests(user_or_id: int | object) -> QuerySet[LeaveRequest]:
    """Retrieve coverage responsibility requests awaiting response from this substitute."""
    user_id = _resolve_user_id(user_or_id)
    return LeaveRequest.objects.filter(
        substitute_id=user_id,
        substitute_status="pending",
        status=sm.PENDING_SUBSTITUTE,
    ).order_by("start_date")


def get_pending_unit_head_reviews(unit_head_user_or_id: int | object) -> QuerySet[LeaveRequest]:
    """Retrieve requests awaiting Unit Head review, strictly excluding the Unit Head's own leave."""
    unit_head_id = _resolve_user_id(unit_head_user_or_id)
    return LeaveRequest.objects.filter(
        status__in=(sm.PENDING_UNIT_HEAD, sm.CANCELLATION_PENDING_UNIT_HEAD, sm.SUBMITTED_LEGACY)
    ).exclude(user_id=unit_head_id).order_by("created_at")


def get_pending_sanction_decisions(authority_user_or_id: int | object) -> QuerySet[LeaveRequest]:
    """Retrieve higher-sanction requests awaiting final decision, excluding self-applications."""
    authority_id = _resolve_user_id(authority_user_or_id)
    return LeaveRequest.objects.filter(
        status__in=(sm.PENDING_SANCTION, sm.CANCELLATION_PENDING_SANCTION)
    ).exclude(user_id=authority_id).order_by("created_at")


def get_director_self_sanctions(director_user_or_id: int | object) -> QuerySet[LeaveRequest]:
    """Retrieve Director-applicant requests awaiting self-sanction (BR-EL-020)."""
    director_id = _resolve_user_id(director_user_or_id)
    return LeaveRequest.objects.filter(
        user_id=director_id,
        status=sm.AWAITING_DIRECTOR_SANCTION,
    ).order_by("created_at")


def get_leave_request_by_id(pk: int) -> LeaveRequest | None:
    """Retrieve a single leave request by primary key."""
    try:
        return LeaveRequest.objects.select_related().prefetch_related("actions").get(pk=pk)
    except LeaveRequest.DoesNotExist:
        return None


def get_published_holidays_for_year(year: int):
    """Retrieve published holidays for the given year."""
    from .models import Holiday
    return Holiday.objects.filter(calendar__year=year, calendar__is_published=True).order_by("date")


def get_pending_approvals_for_user(user_id: int, roles: set[str] | list[str]) -> QuerySet[LeaveRequest]:
    """Retrieve all pending actionable work items for the given actor across their roles."""
    roles_set = set(roles)
    # 1. As substitute
    substitute_qs = get_pending_substitute_requests(user_id)

    # 2. As Unit Head
    if bool(roles_set & {"unit_head", "hod", "leave_admin"}):
        uh_qs = get_pending_unit_head_reviews(user_id)
    else:
        uh_qs = LeaveRequest.objects.none()

    # 3. As Sanctioning Authority
    if bool(roles_set & {"dean", "director", "registrar", "leave_admin"}):
        sanction_qs = get_pending_sanction_decisions(user_id)
    else:
        sanction_qs = LeaveRequest.objects.none()

    # 4. As Director (self-sanction)
    if "director" in roles_set:
        dir_qs = get_director_self_sanctions(user_id)
    else:
        dir_qs = LeaveRequest.objects.none()

    return (substitute_qs | uh_qs | sanction_qs | dir_qs).distinct().order_by("-created_at")


# Backwards compatibility aliases
list_leave_requests_for_user = get_leave_requests_for_user
get_user_leave_balances = get_balances_for_user
