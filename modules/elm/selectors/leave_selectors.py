from django.utils import timezone

from modules.elm.models import LeaveBalance, LeaveRequest


def get_user_leaves(user_id):
    return LeaveRequest.objects.filter(applicant_user_id=str(user_id)).prefetch_related(
        "action_logs"
    )


def get_user_balances(user_id, year=None):
    return LeaveBalance.objects.filter(user_id=str(user_id), year=year or timezone.localdate().year)


def get_pending_substitute_requests(user_id):
    return LeaveRequest.objects.filter(substitute_user_id=str(user_id), status="PENDING_SUBSTITUTE")


def get_pending_unit_head_approvals(user_id):
    return LeaveRequest.objects.filter(
        current_approver_user_id=str(user_id), status="PENDING_UNIT_HEAD"
    )
