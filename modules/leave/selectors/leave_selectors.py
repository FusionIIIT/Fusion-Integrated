"""Selectors for ELM query operations (Qwen 14B)."""

from django.db.models import Q, QuerySet

from modules.leave.models import LeaveAccount, LeaveRequest


def get_user_leave_requests(user_id: str) -> QuerySet[LeaveRequest]:
    """EL-UC-012: View user's own applications."""
    return LeaveRequest.objects.filter(applicant_id=user_id).order_by("-created_at")


def get_user_accounts(user_id: str, year: int) -> QuerySet[LeaveAccount]:
    """EL-UC-012: View user's current balances."""
    return LeaveAccount.objects.filter(user_id=user_id, year=year)


def get_substitute_inbox(substitute_id: str) -> QuerySet[LeaveRequest]:
    """EL-UC-002: Substitute task inbox."""
    return LeaveRequest.objects.filter(substitute_id=substitute_id, status="AWAITING_SUBSTITUTE")


def get_unit_head_inbox(unit_head_id: str) -> QuerySet[LeaveRequest]:
    """EL-UC-003: Unit head pending approvals and recommendations."""
    return LeaveRequest.objects.filter(
        unit_head_id=unit_head_id,
        status__in=["AWAITING_UNIT_HEAD", "CANCELLATION_PENDING_UH"]
    )


def get_establishment_inbox() -> QuerySet[LeaveRequest]:
    """EL-UC-004: Establishment routing inbox."""
    return LeaveRequest.objects.filter(
        status__in=["AWAITING_ESTABLISHMENT", "CANCELLATION_PENDING_EST"]
    )


def get_sanction_inbox(authority_id: str | None = None) -> QuerySet[LeaveRequest]:
    """EL-UC-005, EL-UC-011: Final sanction and resumption inbox."""
    qs = LeaveRequest.objects.filter(
        status__in=[
            "AWAITING_SANCTION",
            "AWAITING_DIRECTOR_SELF_SANCTION",
            "CANCELLATION_PENDING_SANCTION",
            "RESUMPTION_PENDING"
        ]
    )
    if authority_id:
        qs = qs.filter(sanctioning_authority_id=authority_id)
    return qs


def get_actor_inbox(actor_id: str) -> QuerySet[LeaveRequest]:
    """Return only pending tasks explicitly routed to this authenticated actor."""
    return LeaveRequest.objects.filter(
        Q(substitute_id=actor_id, status="AWAITING_SUBSTITUTE")
        | Q(routing_config__isnull=False, unit_head_id=actor_id,
            status__in=["AWAITING_UNIT_HEAD", "CANCELLATION_PENDING_UH"])
        | Q(routing_config__isnull=False, establishment_user_id=actor_id,
            status__in=["AWAITING_ESTABLISHMENT", "CANCELLATION_PENDING_EST"])
        | Q(routing_config__isnull=False, sanctioning_authority_id=actor_id,
            status__in=["AWAITING_SANCTION", "CANCELLATION_PENDING_SANCTION", "RESUMPTION_PENDING"])
        | Q(status="AWAITING_DIRECTOR_SELF_SANCTION", applicant_id=actor_id)
    ).distinct().order_by("created_at")
