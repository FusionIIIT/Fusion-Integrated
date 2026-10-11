from django.db import transaction

from modules.elm.models import LeaveRequest


@transaction.atomic
def create_leave_request(*, employee, leave_type, start_date, end_date, reason):
    if end_date < start_date:
        raise ValueError("End date cannot be before start date.")

    return LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status=LeaveRequest.Status.PENDING,
    )


def list_employee_requests(*, employee):
    return LeaveRequest.objects.filter(employee=employee).order_by("-created_at")
