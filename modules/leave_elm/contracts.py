from collections.abc import Sequence
from modules.leave_elm.models import LeaveApplication, LeaveBalance
from django.db.models import QuerySet

class LeaveElmContracts:
    @staticmethod
    def get_leave_balances(user_ids: Sequence[int]) -> QuerySet[LeaveBalance]:
        return LeaveBalance.objects.select_related('leave_category').filter(user_id__in=user_ids).order_by('user_id', 'id')

    @staticmethod
    def get_leave_application_summaries(user_ids: Sequence[int]) -> QuerySet[LeaveApplication]:
        return LeaveApplication.objects.select_related('leave_type', 'leave_type__leave_category').filter(user_id__in=user_ids).order_by('-created_at', '-id')
