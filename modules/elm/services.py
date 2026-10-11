from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    LeaveAccount,
    LeaveApplication,
    LeaveBalanceTransaction,
    LeaveStatus,
    LeaveType,
)


def get_leave_balance(employee, leave_type, year):
    account = LeaveAccount.objects.get(
        employee=employee,
        leave_type=leave_type,
        year=year,
    )

    transactions = account.transactions.all()

    total_changes = sum(
        (entry.amount for entry in transactions),
        Decimal("0.00"),
    )

    return (
        account.opening_balance
        + account.entitlement
        + total_changes
    )


def validate_leave_application(application):
    if application.end_date < application.start_date:
        raise ValidationError(
            {"end_date": "End date cannot precede start date."}
        )

    if application.leave_type not in LeaveType.values:
        raise ValidationError(
            {"leave_type": "Unsupported leave category."}
        )

    if not application.purpose.strip():
        raise ValidationError(
            {"purpose": "Purpose/reason is required."}
        )

    if (
        application.station_leave_required
        and not application.station_leave_details.strip()
    ):
        raise ValidationError(
            {
                "station_leave_details":
                    "Station Leave details are required."
            }
        )

    if (
        application.start_half != "FULL"
        or application.end_half != "FULL"
    ) and application.leave_type != LeaveType.CL:
        raise ValidationError(
            "Half-day leave is supported only for CL "
            "in this baseline."
        )

    overlaps = LeaveApplication.objects.filter(
        employee=application.employee,
        start_date__lte=application.end_date,
        end_date__gte=application.start_date,
        status__in=[
            LeaveStatus.AWAITING_SUBSTITUTE,
            LeaveStatus.PENDING_UNIT_HEAD,
            LeaveStatus.PENDING_AUTHORITY,
            LeaveStatus.APPROVED,
        ],
    ).exclude(pk=application.pk)

    if overlaps.exists():
        raise ValidationError(
            "The requested period overlaps another active leave."
        )

    # Additional policy-driven validation must be implemented
    # before submission:
    # - category eligibility
    # - available balance and entitlement
    # - published holiday/RH calendar
    # - leave-counting rules
    # - half-day CL overlap exceptions
    # - substitute eligibility and consent requirements


@transaction.atomic
def submit_leave_application(application_id, employee):
    application = (
        LeaveApplication.objects.select_for_update()
        .get(pk=application_id, employee=employee)
    )

    if application.status != LeaveStatus.DRAFT:
        raise ValidationError(
            "Only draft applications can be submitted."
        )

    validate_leave_application(application)

    if application.substitute_id:
        application.status = LeaveStatus.AWAITING_SUBSTITUTE
    else:
        application.status = LeaveStatus.PENDING_UNIT_HEAD

    application.save(
        update_fields=["status", "updated_at"]
    )

    return application
