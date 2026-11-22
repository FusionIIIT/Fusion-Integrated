from django.db.models import QuerySet

from modules.iaa.models import ExpenseVoucherRequest
from modules.iaa.selectors.scoping import scope_requests


def get_requests(principal, status: str | None = None) -> QuerySet[ExpenseVoucherRequest]:
    qs = scope_requests(ExpenseVoucherRequest.objects.prefetch_related("items"), principal)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_request_by_id(principal, request_id: int) -> ExpenseVoucherRequest | None:
    return get_requests(principal).filter(id=request_id).first()


def get_pending_approvals_for_user(principal) -> QuerySet[ExpenseVoucherRequest]:
    qs = scope_requests(ExpenseVoucherRequest.objects.all(), principal)
    return qs.filter(
        status__in=["finance_validated", "approval_pending", "escalated"],
        assigned_approver_id=principal.user_id,
    )
