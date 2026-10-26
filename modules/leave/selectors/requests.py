"""Leave request, substitute, and approval query selectors."""

from __future__ import annotations

from datetime import date

from django.db.models import Q, QuerySet

from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import LeaveRequest, SubstituteNomination

# States where an application is actively pending review or sanction
PENDING_APPROVAL_STATES = (
    LeaveState.AWAITING_UNIT_HEAD,
    LeaveState.AWAITING_ESTABLISHMENT,
    LeaveState.AWAITING_SANCTION,
    LeaveState.AWAITING_DIRECTOR,
    LeaveState.CANCELLATION_PENDING_UNIT_HEAD,
    LeaveState.CANCELLATION_PENDING_ESTABLISHMENT,
    LeaveState.CANCELLATION_PENDING_SANCTION,
    LeaveState.AWAITING_EXTENSION_UNIT_HEAD,
    LeaveState.EXTENSION_PENDING_ESTABLISHMENT,
    LeaveState.EXTENSION_PENDING_SANCTION,
    LeaveState.RESUMPTION_REVIEW_PENDING,
)


def get_user_requests(
    user_id: int | None,
    status: str | None = None,
    year: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> QuerySet[LeaveRequest]:
    """Return leave applications belonging strictly to user_id (EL-UC-012)."""
    if user_id is None:
        return LeaveRequest.objects.none()

    qs = (
        LeaveRequest.objects.filter(user_id=user_id)
        .select_related("leave_type")
        .order_by("-created_at", "-id")
    )
    if status:
        qs = qs.filter(status=status)
    if year is not None:
        qs = qs.filter(start_date__year=year)
    if start_date:
        qs = qs.filter(start_date__gte=start_date)
    if end_date:
        qs = qs.filter(end_date__lte=end_date)
    return qs


def get_pending_substitute_requests(
    substitute_user_id: int | None,
) -> QuerySet[SubstituteNomination]:
    """Return pending responsibility coverage requests for a substitute (EL-UC-002).

    Only returns nominations assigned to substitute_user_id with status='pending',
    where the parent request is actively awaiting substitute consent.
    """
    if substitute_user_id is None:
        return SubstituteNomination.objects.none()

    substitute_wait_states = (
        LeaveState.AWAITING_SUBSTITUTE,
        LeaveState.AWAITING_EXTENSION_SUBSTITUTE,
    )
    return (
        SubstituteNomination.objects.filter(
            substitute_user_id=substitute_user_id,
            status="pending",
            request__status__in=substitute_wait_states,
        )
        .select_related("request", "request__leave_type")
        .order_by("-created_at", "-id")
    )


def get_approvals_queue(
    approver_user_id: int | None = None,
    approver_role: str | None = None,
) -> QuerySet[LeaveRequest]:
    """Return leave requests awaiting decision by the specified approver/role.

    Enforces approver isolation:
    - If neither approver_user_id nor approver_role is provided, returns empty queryset.
    - Matches requests in pending approval states targeted to approver_user_id
      or approver_role.
    - Prevents self-approval by excluding requests applied by approver_user_id
      (except Director self-sanction, which transitions via dedicated BW-EL-07..09).
    """
    if approver_user_id is None and approver_role is None:
        return LeaveRequest.objects.none()

    qs = (
        LeaveRequest.objects.filter(status__in=PENDING_APPROVAL_STATES)
        .select_related("leave_type")
        .order_by("created_at", "id")
    )

    criteria = Q()
    if approver_user_id is not None:
        criteria |= Q(current_handler_user_id=approver_user_id)
    if approver_role:
        criteria |= Q(current_handler_role=approver_role)

    qs = qs.filter(criteria)

    # Prevent an applicant from acting as their own approver in standard queues
    if approver_user_id is not None and approver_role != "Director":
        qs = qs.exclude(user_id=approver_user_id)

    return qs
