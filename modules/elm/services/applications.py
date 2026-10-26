from django.db import transaction
from django.db.models import Q
from decimal import Decimal
from datetime import timedelta
from core.api.exceptions import DomainError
from modules.elm.models import LeaveRequest, LeaveDecision
from modules.elm.services.entitlements import get_balance


class LeaveApplicationError(DomainError):
    code = "leave_application_error"
    message = "An error occurred while processing the leave application."


class LeaveApplicationConflictError(DomainError):
    code = "leave_application_conflict"
    message = "The leave application conflicts with an existing request."


class LeaveApplicationInsufficientBalanceError(DomainError):
    code = "leave_application_insufficient_balance"
    message = "Insufficient balance for the requested leave. Please check your balance and try again."


class LeaveApplicationUnknownCategoryError(DomainError):
    code = "leave_application_unknown_category"
    message = "Unknown leave category. Please select a valid category and try again."


class LeaveApplicationEndDateBeforeStartDateError(DomainError):
    code = "leave_application_end_date_before_start_date"
    message = "End date must be after start date. Please correct the dates and try again."


def _count_days(category, start_date, end_date, half_day):
    if half_day:
        return Decimal("0.5")
    days = 0
    current = start_date
    while current <= end_date:
        if category in ["EL", "COL", "VL"] or (category in ["CL", "RH", "SCL"] and current.weekday() < 5):
            days += 1
        current += timedelta(days=1)
    return Decimal(days)


def submit_leave_request(applicant_user_id, category, start_date, end_date, reason, half_day=False, station_leave_details=None, substitute_user_id=None):
    with transaction.atomic():
        if category not in ["CL", "RH", "SCL", "EL", "COL", "VL"]:
            raise LeaveApplicationUnknownCategoryError("Invalid leave category.")

        if end_date < start_date:
            raise LeaveApplicationEndDateBeforeStartDateError("End date must be after start date.")

        if LeaveRequest.objects.filter(
            applicant_user_id=applicant_user_id,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).exclude(status__in=["Withdrawn", "Rejected"]).exists():
            raise LeaveApplicationConflictError("Overlap with another request.")

        balance = get_balance(applicant_user_id, category, start_date.year)
        days = _count_days(category, start_date, end_date, half_day)
        if days > balance:
            raise LeaveApplicationInsufficientBalanceError("Insufficient balance for the requested leave. Please check your balance and try again.")

        leave_request = LeaveRequest.objects.create(
            applicant_user_id=applicant_user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            half_day=half_day,
            station_leave_details=station_leave_details,
            substitute_user_id=substitute_user_id,
            status="Awaiting Substitute Response" if substitute_user_id else "Awaiting Unit Head Review",
            user_id=applicant_user_id  # Set user_id correctly
        )

        LeaveDecision.objects.create(
            leave_request=leave_request,
            actor_user_id=applicant_user_id,
            action="submitted",
            user_id=applicant_user_id  # Set user_id correctly
        )

        return leave_request


def withdraw_leave_request(request_id, actor_user_id):
    with transaction.atomic():
        leave_request = LeaveRequest.objects.get(id=request_id)
        if leave_request.applicant_user_id != actor_user_id or leave_request.status not in ["Awaiting Substitute Response", "Awaiting Unit Head Review"]:
            raise LeaveApplicationError("You are not authorized to withdraw this leave request.")

        leave_request.status = "Withdrawn"
        leave_request.save()

        LeaveDecision.objects.create(
            leave_request=leave_request,
            actor_user_id=actor_user_id,
            action="withdrawn",
            user_id=actor_user_id  # Set user_id correctly
        )
