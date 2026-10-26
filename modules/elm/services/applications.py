"""Service functions for ELM leave applications and substitute nominations."""

from datetime import date

from django.db import transaction

from modules.elm.domain.policy import (
    check_date_overlap,
    is_valid_transition,
    requested_days,
    validate_balance_sufficiency,
    validate_substitute_eligibility,
)
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
    reason: str = "",
    station_leave_details: str = "",
) -> LeaveApplication:
    """Submit a leave application after validating balance sufficiency and no overlaps."""
    days = requested_days(start_date, end_date)
    balance_obj = LeaveBalance.objects.filter(
        employee_id=applicant_id, leave_type=leave_type
    ).first()
    if balance_obj is None:
        raise ValueError(f"No leave balance found for {leave_type.leave_type}.")

    validate_balance_sufficiency(balance_obj.balance, days)

    overlapping_apps = LeaveApplication.objects.filter(
        applicant_id=applicant_id,
        status__in=["AWAITING_SUBSTITUTE", "AWAITING_APPROVAL", "APPROVED"],
    )

    for app in overlapping_apps:
        if check_date_overlap(app.start_date, app.end_date, start_date, end_date):
            raise ValueError("Overlapping leave application exists.")

    return LeaveApplication.objects.create(
        applicant_id=applicant_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        station_leave_details=station_leave_details,
        reason=reason,
        status="AWAITING_APPROVAL",
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
    """Nominate an eligible substitute and set application status to AWAITING_SUBSTITUTE."""
    validate_substitute_eligibility(leave_application.applicant_id, substitute_id)

    nomination = SubstituteNomination.objects.create(
        leave_application=leave_application,
        substitute_id=substitute_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status="PENDING",
    )

    leave_application.status = "AWAITING_SUBSTITUTE"
    leave_application.save(update_fields=["status"])
    return nomination


@transaction.atomic
def respond_substitute_nomination(
    *,
    nomination: SubstituteNomination,
    accept: bool,
    decline_reason: str = "",
) -> SubstituteNomination:
    """Handle substitute consent (accept moves to AWAITING_APPROVAL; decline records reason)."""
    if accept:
        nomination.status = "ACCEPTED"
        nomination.leave_application.status = "AWAITING_APPROVAL"
        nomination.leave_application.save(update_fields=["status"])
    else:
        nomination.status = "DECLINED"
        nomination.decline_reason = decline_reason

    nomination.save()
    return nomination


@transaction.atomic
def review_leave_application(
    *,
    application: LeaveApplication,
    approve: bool,
) -> LeaveApplication:
    """Review leave application: approve atomically deducts leave days; reject updates status."""
    if approve:
        if not is_valid_transition(application.status, "APPROVED"):
            raise ValueError("Invalid transition.")

        balance_obj = (
            LeaveBalance.objects.select_for_update()
            .filter(employee_id=application.applicant_id, leave_type=application.leave_type)
            .first()
        )
        if balance_obj is None:
            raise ValueError("No leave balance record found for applicant.")

        days = requested_days(application.start_date, application.end_date)
        validate_balance_sufficiency(balance_obj.balance, days)
        balance_obj.balance -= days
        balance_obj.save(update_fields=["balance"])

        application.status = "APPROVED"
    else:
        if not is_valid_transition(application.status, "REJECTED"):
            raise ValueError("Invalid transition.")

        application.status = "REJECTED"

    application.save(update_fields=["status"])
    return application


@transaction.atomic
def withdraw_application(*, application: LeaveApplication) -> LeaveApplication:
    """Withdraw a pending leave application per BR-EL-022."""
    if not is_valid_transition(application.status, "WITHDRAWN"):
        raise ValueError("Invalid transition.")

    application.status = "WITHDRAWN"
    application.save(update_fields=["status"])
    return application


def get_employee_balances(*, employee_id: int):
    """Retrieve all leave balance records for an employee."""
    return LeaveBalance.objects.filter(employee_id=employee_id).select_related("leave_type")
