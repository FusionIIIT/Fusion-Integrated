from collections.abc import Sequence
from modules.leave_elm.models import LeaveApplication, LeaveBalance
from django.db.models import QuerySet, Count

class LeaveElmContracts:
    @staticmethod
    def get_leave_balances(user_ids: Sequence[int]) -> QuerySet[LeaveBalance]:
        return LeaveBalance.objects.filter(user_id__in=user_ids)

    @staticmethod
    def get_leave_application_summaries(user_ids: Sequence[int]) -> QuerySet[LeaveApplication]:
        return LeaveApplication.objects.filter(user_id__in=user_ids).annotate(
            total_days=Count('days')
        )
