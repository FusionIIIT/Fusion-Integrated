from django.db.models import Q

from modules.leave.domain.workflow import PENDING_STATES
from modules.leave.models import LeaveAccountTransaction, LeaveApplication


def visible_applications(principal, *, status="", request_kind=""):
    qs = LeaveApplication.objects.select_related("original_application")
    if status:
        qs = qs.filter(status=status)
    if request_kind:
        qs = qs.filter(request_kind=request_kind)
    if principal.has_permission("leave.record.update"):
        return qs
    uid = principal.user_id
    assigned = Q(substitute_user_id=uid)
    assigned |= Q(unit_head_user_id=uid)
    assigned |= Q(establishment_user_id=uid)
    assigned |= Q(final_authority_user_id=uid)
    if principal.has_permission("leave.application.review") or principal.has_permission(
            "leave.application.approve"):
        return qs.filter(Q(applicant_user_id=uid) | assigned).distinct()
    return qs.filter(applicant_user_id=uid)


def assigned_tasks(principal):
    uid = principal.user_id
    return LeaveApplication.objects.filter(
        Q(substitute_user_id=uid) | Q(unit_head_user_id=uid)
        | Q(establishment_user_id=uid) | Q(final_authority_user_id=uid),
        status__in=PENDING_STATES,
    ).order_by("created_at", "pk")


def account_transactions(user_id: int, leave_type: str = ""):
    qs = LeaveAccountTransaction.objects.filter(user_id=user_id)
    return qs.filter(leave_type=leave_type) if leave_type else qs
