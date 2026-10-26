"""The batched public contract for attendance/payroll integrations."""

from collections.abc import Sequence

from django.utils import timezone

from modules.elm.models import AttendanceEvent, LeaveBalance


def get_employee_leave_summaries(user_ids: Sequence[int], year=None):
    year = year or timezone.localdate().year
    ids = list(map(str, user_ids))
    result = {user_id: {} for user_id in ids}
    for balance in LeaveBalance.objects.filter(user_id__in=ids, year=year):
        result[balance.user_id][balance.leave_type] = str(balance.balance)
    return result


def get_attendance_events(event_ids: Sequence[str]):
    return list(AttendanceEvent.objects.filter(pk__in=event_ids).values())


def acknowledge_attendance_events(event_ids):
    return AttendanceEvent.objects.filter(pk__in=event_ids, delivered_at__isnull=True).update(
        delivered_at=timezone.now()
    )
