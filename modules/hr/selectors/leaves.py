from django.db.models import Prefetch, Q, QuerySet

from modules.hr.models import LeaveBalance, LeaveRequest


def visible_leave_requests(principal) -> QuerySet[LeaveRequest]:
    requests = LeaveRequest.objects.select_related("employee").prefetch_related(
        Prefetch("ledger_entries")
    )
    if principal.has_permission("hr.leave.view"):
        return requests
    scope = Q()
    if principal.has_permission("hr.leave.view_self"):
        scope |= Q(employee__user_id=principal.user_id)
    if principal.has_permission("hr.leave.approve"):
        scope |= Q(current_authority_user_id=principal.user_id)
    return requests.filter(scope) if scope else requests.none()


def leave_request_for_user(*, request_id: int, principal) -> LeaveRequest | None:
    return visible_leave_requests(principal).filter(pk=request_id).first()


def leave_balances_for_employee(employee_id: int) -> QuerySet[LeaveBalance]:
    return LeaveBalance.objects.filter(employee_id=employee_id).order_by("leave_type")


def managed_leave_balances() -> QuerySet[LeaveBalance]:
    return LeaveBalance.objects.select_related("employee").order_by(
        "employee__user_id", "leave_type"
    )
