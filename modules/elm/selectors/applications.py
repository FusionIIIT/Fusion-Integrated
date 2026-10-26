"""Application and balance read selectors for Employee Leave Management.

All reads and ownership filtering live here — once per module, not once per view.
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.elm.domain.policy import ApplicationStatus
from modules.elm.models import LeaveApplication, LeaveBalance


def visible_applications(principal) -> QuerySet[LeaveApplication]:
    """Return applications visible to the given principal."""
    qs = LeaveApplication.objects.select_related("leave_type", "original_application")
    user_id = getattr(principal, "user_id", getattr(principal, "id", 0)) or 0
    check = getattr(principal, "has_permission", None)

    if check and (
        check("leave_elm.application.approve") or check("leave_elm.offline.record")
    ):
        return qs

    # Normal users see applications where they are applicant or designated substitute
    return qs.filter(Q(user_id=user_id) | Q(substitute_user_id=user_id))


def approval_queue(principal) -> QuerySet[LeaveApplication]:
    """Return applications currently awaiting review or action by the principal."""
    qs = LeaveApplication.objects.select_related("leave_type", "original_application")
    user_id = getattr(principal, "user_id", getattr(principal, "id", 0)) or 0
    check = getattr(principal, "has_permission", None)

    is_approver = bool(check and check("leave_elm.application.approve"))

    conditions = Q()

    # Substitute queue: applications waiting for this principal to accept/decline
    if user_id:
        conditions |= Q(
            substitute_user_id=user_id,
            status=ApplicationStatus.AWAITING_SUBSTITUTE.value,
        )

    # Approver queue: applications pending Unit Head, Sanction Authority, or Director action
    if is_approver:
        approver_statuses = [
            ApplicationStatus.AWAITING_UNIT_HEAD.value,
            ApplicationStatus.AWAITING_FINAL_SANCTION.value,
            ApplicationStatus.RECOMMENDED.value,
            ApplicationStatus.AWAITING_DIRECTOR.value,
            ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD.value,
            ApplicationStatus.CANCELLATION_PENDING_SANCTION_AUTHORITY.value,
        ]
        conditions |= Q(status__in=approver_statuses)
        # Also include duty resumption pending review
        conditions |= Q(resumption_status="pending_review")

    if not conditions:
        return qs.none()

    return qs.filter(conditions).order_by("-created_at")


def visible_balances(
    principal, target_user_id: int | None = None, year: int | None = None
) -> QuerySet[LeaveBalance]:
    """Return leave balances visible to the principal."""
    qs = LeaveBalance.objects.select_related("leave_type")
    user_id = getattr(principal, "user_id", getattr(principal, "id", 0)) or 0
    check = getattr(principal, "has_permission", None)

    if target_user_id and target_user_id != user_id:
        if not (check and check("leave_elm.balance.view")):
            return qs.none()
        qs = qs.filter(user_id=target_user_id)
    else:
        qs = qs.filter(user_id=user_id)

    if year:
        qs = qs.filter(year=year)

    return qs.order_by("leave_type__code")
