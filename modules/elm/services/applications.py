"""Service functions for ELM leave applications and substitute nominations."""

from datetime import date

from django.db import transaction

from modules.elm.domain.policy import requested_days
from modules.elm.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveType,
    SubstituteNomination,
)


@transaction.atomic
def submit_leave_application(
    *,
    applicant_id: int,
    leave_type: LeaveType,
    start_date: date,
    end_date: date,
    station_leave_details: str = "",
) -> LeaveApplication:
    requested_days(start_date, end_date)
    return LeaveApplication.objects.create(
        applicant_id=applicant_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        station_leave_details=station_leave_details,
        status="PENDING",
    )


@transaction.atomic
def nominate_substitute(
    *,
    leave_application: LeaveApplication,
    substitute_id: int,
    start_date: date,
    end_date: date,
    reason: str = "",
) -> SubstituteNomination:
    return SubstituteNomination.objects.create(
        leave_application=leave_application,
        substitute_id=substitute_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
    )


@transaction.atomic
def withdraw_application(*, application: LeaveApplication) -> LeaveApplication:
    application.status = "WITHDRAWN"
    application.save(update_fields=["status"])
    return application


def get_employee_balances(*, employee_id: int):
    return LeaveBalance.objects.filter(employee_id=employee_id).select_related("leave_type")
