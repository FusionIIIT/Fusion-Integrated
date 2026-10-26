"""Selectors for actionable tasks and approval queues."""

from django.db.models import Q, QuerySet

from modules.leave.models import LeaveApplication, LeaveHierarchyConfig


def pending_approvals_for_principal(principal) -> QuerySet[LeaveApplication]:
    """Return requests currently awaiting the principal's review/approval."""
    user_id = principal.user_id
    role = principal.active_role or ""

    # Check if user is configured as unit head for any department
    is_unit_head = LeaveHierarchyConfig.objects.filter(
        unit_head_user_id=user_id
    ).exists() or role in ("HOD", "unit_head")
    is_dr_estt = LeaveHierarchyConfig.objects.filter(dr_estt_user_id=user_id).exists() or role in (
        "dr_establishment",
        "establishment_officer",
    )
    is_sanction_auth = LeaveHierarchyConfig.objects.filter(
        Q(dean_user_id=user_id) | Q(registrar_user_id=user_id) | Q(director_user_id=user_id)
    ).exists() or role in ("Dean Academic", "Registrar", "Director", "leave_admin", "admin")

    q = Q(pk__isnull=True)  # empty baseline

    if is_unit_head:
        q |= Q(status="AWAITING_UNIT_HEAD") | Q(status="AWAITING_CANCELLATION")

    if is_dr_estt:
        q |= Q(status="AWAITING_ESTABLISHMENT")

    if is_sanction_auth:
        q |= Q(status="AWAITING_SANCTION") | Q(resumption_status="SUBMITTED")

    # If admin, show all pending
    if principal.has_permission("leave.type.manage"):
        q = Q(
            status__in=[
                "AWAITING_UNIT_HEAD",
                "AWAITING_ESTABLISHMENT",
                "AWAITING_SANCTION",
                "AWAITING_CANCELLATION",
            ]
        ) | Q(resumption_status="SUBMITTED")

    return LeaveApplication.objects.filter(q).order_by("created_at")
