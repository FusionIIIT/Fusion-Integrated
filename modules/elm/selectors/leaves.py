"""Read selectors for ELM. Ownership filtering lives here."""
from django.db.models import QuerySet

from modules.elm.models.balances import LeaveBalance
from modules.elm.models.leaves import LeaveRequest


def get_user_leaves(user_id: int) -> QuerySet[LeaveRequest]:
    """Retrieve all leave applications for the current user."""
    return LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")


def get_user_leave_detail(user_id: int, leave_id: int) -> LeaveRequest | None:
    """Retrieve a specific leave request owned by user."""
    return LeaveRequest.objects.filter(user_id=user_id, pk=leave_id).first()


def get_user_balances(user_id: int, year: int) -> QuerySet[LeaveBalance]:
    """Retrieve all leave balance quotas for a user in a specific year."""
    return LeaveBalance.objects.filter(user_id=user_id, year=year)


def get_substitute_pending_requests(substitute_user_id: int) -> QuerySet[LeaveRequest]:
    """Retrieve all pending requests where user is nominated as substitute."""
    return LeaveRequest.objects.filter(
        substitute_user_id=substitute_user_id,
        status__in=["awaiting_substitute", "extension_pending_substitute"],
    ).order_by("created_at")


def get_unit_head_pending_requests(unit_head_user_id: int | None = None) -> QuerySet[LeaveRequest]:
    """Retrieve requests awaiting Unit Head review."""
    qs = LeaveRequest.objects.filter(status__in=[
        "awaiting_unit_head",
        "cancellation_pending_unit_head",
        "extension_pending_unit_head",
    ])
    if unit_head_user_id:
        qs = qs.filter(unit_head_user_id=unit_head_user_id)
    return qs.order_by("created_at")


def get_establishment_pending_requests() -> QuerySet[LeaveRequest]:
    """Retrieve requests awaiting Establishment verification."""
    return LeaveRequest.objects.filter(status__in=[
        "awaiting_establishment",
        "cancellation_pending_establishment",
        "extension_pending_establishment",
    ]).order_by("created_at")


def get_sanctioning_authority_pending_requests(authority_user_id: int | None = None) -> QuerySet[LeaveRequest]:
    """Retrieve requests awaiting final sanction."""
    qs = LeaveRequest.objects.filter(status__in=[
        "awaiting_final_sanction",
        "awaiting_director_self_sanction",
        "cancellation_pending_final",
        "extension_pending_final",
        "resumption_pending",
    ])
    if authority_user_id:
        qs = qs.filter(sanctioning_authority_user_id=authority_user_id)
    return qs.order_by("created_at")
