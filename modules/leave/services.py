"""Domain and workflow services for Employee Leave Management (ELM)."""
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from modules.leave.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveType,
    LeaveWorkflowHistory,
)


def calculate_leave_days(
    leave_type: LeaveType,
    start_date: date,
    end_date: date,
    is_half_day: bool = False,
) -> Decimal:
    """Calculate effective leave days according to BR-EL-010 and BR-EL-011."""
    if is_half_day:
        return Decimal("0.5")

    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        return Decimal("0.0")

    if leave_type.is_continuous_counting:
        return Decimal(str(total_days))

    holidays = set(
        HolidayCalendar.objects.filter(
            date__range=[start_date, end_date], is_restricted=False
        ).values_list("date", flat=True)
    )

    count = 0
    curr = start_date
    while curr <= end_date:
        if curr.weekday() < 5 and curr not in holidays:
            count += 1
        curr += timedelta(days=1)

    return Decimal(str(count))


def get_or_create_balance(
    employee_id: str, leave_type: LeaveType, year: int
) -> LeaveBalance:
    """Ensure an employee has an initialized LeaveBalance record for the year."""
    balance, _created = LeaveBalance.objects.get_or_create(
        employee_id=employee_id,
        leave_type=leave_type,
        year=year,
        defaults={"credited": leave_type.max_days_per_year},
    )
    return balance


def validate_application_rules(
    applicant_id: str,
    leave_type: LeaveType,
    start_date: date,
    end_date: date,
    is_half_day: bool = False,
    half_day_period: str = "",
    substitute_id: str = "",
    station_leave_required: bool = False,
    departure_date: date | None = None,
    arrival_date: date | None = None,
    exclude_application_id: int | None = None,
) -> Decimal:
    """Enforce business rules BR-EL-001 through BR-EL-015 before submission."""
    if end_date < start_date:
        raise ValidationError({"end_date": "End date cannot be earlier than start date."})

    if is_half_day:
        if leave_type.code != "CL":
            raise ValidationError(
                {"is_half_day": "Half-day leave is only permitted for Casual Leave (CL)."}
            )
        if start_date != end_date:
            raise ValidationError(
                {"end_date": "Half-day CL must have identical start and end date."}
            )
        if half_day_period not in ("FIRST_HALF", "SECOND_HALF"):
            raise ValidationError(
                {"half_day_period": "Must select FIRST_HALF or SECOND_HALF for half-day CL."}
            )

    if leave_type.code == "RH":
        is_rh = HolidayCalendar.objects.filter(
            date=start_date, is_restricted=True, year=start_date.year
        ).exists()
        if not is_rh or start_date != end_date:
            raise ValidationError(
                {"start_date": "Restricted Holiday request must match a single published RH date."}
            )

    leave_days = calculate_leave_days(leave_type, start_date, end_date, is_half_day)
    if leave_days <= Decimal("0.0"):
        raise ValidationError(
            {"leave_days": "Calculated leave days must be greater than zero."}
        )

    balance = get_or_create_balance(applicant_id, leave_type, start_date.year)
    if balance.available < leave_days:
        raise ValidationError(
            {
                "leave_days": (
                    f"Insufficient leave balance: requested {leave_days} days, "
                    f"available {balance.available} days."
                )
            }
        )

    applicant_qs = LeaveApplication.objects.filter(
        applicant_id=applicant_id,
        status__in=[
            LeaveApplication.STATUS_DRAFT,
            LeaveApplication.STATUS_AWAITING_SUBSTITUTE,
            LeaveApplication.STATUS_SUBSTITUTE_DECLINED,
            LeaveApplication.STATUS_AWAITING_UNIT_HEAD,
            LeaveApplication.STATUS_AWAITING_ESTABLISHMENT,
            LeaveApplication.STATUS_AWAITING_SANCTION,
            LeaveApplication.STATUS_AWAITING_DIRECTOR,
            LeaveApplication.STATUS_APPROVED,
        ],
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_application_id:
        applicant_qs = applicant_qs.exclude(pk=exclude_application_id)

    for existing in applicant_qs:
        if (
            is_half_day
            and existing.is_half_day
            and existing.start_date == start_date
            and existing.half_day_period != half_day_period
        ):
            continue
        raise ValidationError(
            {"start_date": f"Overlaps with active leave application #{existing.id}."}
        )

    if leave_type.requires_substitute and substitute_id:
        if substitute_id == applicant_id:
            raise ValidationError(
                {"substitute_id": "An applicant cannot nominate themselves as substitute."}
            )
        sub_qs = LeaveApplication.objects.filter(
            applicant_id=substitute_id,
            status__in=[
                LeaveApplication.STATUS_AWAITING_UNIT_HEAD,
                LeaveApplication.STATUS_AWAITING_ESTABLISHMENT,
                LeaveApplication.STATUS_AWAITING_SANCTION,
                LeaveApplication.STATUS_AWAITING_DIRECTOR,
                LeaveApplication.STATUS_APPROVED,
            ],
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if sub_qs.exists():
            raise ValidationError(
                {"substitute_id": "Nominated substitute has active leave during this period."}
            )

    if station_leave_required:
        if not departure_date or not arrival_date:
            raise ValidationError(
                {"departure_date": "Departure and arrival dates are required for Station Leave."}
            )
        if arrival_date < departure_date:
            raise ValidationError(
                {"arrival_date": "Station leave arrival date cannot precede departure date."}
            )

    return leave_days


@transaction.atomic
def submit_leave_application(
    applicant_id: str,
    leave_type: LeaveType,
    start_date: date,
    end_date: date,
    reason: str,
    is_half_day: bool = False,
    half_day_period: str = "",
    substitute_id: str = "",
    station_leave_required: bool = False,
    departure_date: date | None = None,
    arrival_date: date | None = None,
    station_address: str = "",
    emergency_contact: str = "",
    is_director: bool = False,
) -> LeaveApplication:
    """Submit a leave application and route to first workflow gate per CW-EL-01."""
    leave_days = validate_application_rules(
        applicant_id=applicant_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_period=half_day_period,
        substitute_id=substitute_id,
        station_leave_required=station_leave_required,
        departure_date=departure_date,
        arrival_date=arrival_date,
    )

    if leave_type.requires_substitute and substitute_id:
        initial_status = LeaveApplication.STATUS_AWAITING_SUBSTITUTE
        sub_status = LeaveApplication.SUB_STATUS_PENDING
    elif is_director:
        initial_status = LeaveApplication.STATUS_AWAITING_DIRECTOR
        sub_status = LeaveApplication.SUB_STATUS_NONE
    else:
        initial_status = LeaveApplication.STATUS_AWAITING_UNIT_HEAD
        sub_status = LeaveApplication.SUB_STATUS_NONE

    app = LeaveApplication.objects.create(
        applicant_id=applicant_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        leave_days=leave_days,
        reason=reason,
        status=initial_status,
        is_half_day=is_half_day,
        half_day_period=half_day_period if is_half_day else "",
        station_leave_required=station_leave_required,
        departure_date=departure_date if station_leave_required else None,
        arrival_date=arrival_date if station_leave_required else None,
        station_address=station_address if station_leave_required else "",
        emergency_contact=emergency_contact if station_leave_required else "",
        substitute_id=substitute_id,
        substitute_status=sub_status,
    )

    LeaveWorkflowHistory.objects.create(
        application=app,
        actor_id=applicant_id,
        action="SUBMITTED",
        from_state="DRAFT",
        to_state=initial_status,
        remarks=reason,
    )
    return app


@transaction.atomic
def respond_to_substitute_request(
    application: LeaveApplication,
    substitute_id: str,
    action: str,
    remarks: str = "",
    is_director: bool = False,
) -> LeaveApplication:
    """Process substitute response (Accept/Decline) according to EL-UC-002."""
    if application.substitute_id != substitute_id:
        raise ValidationError("Only the nominated substitute may respond to this request.")

    if application.status != LeaveApplication.STATUS_AWAITING_SUBSTITUTE:
        raise ValidationError("Application is not awaiting substitute response.")

    from_state = application.status
    if action == "accept":
        application.substitute_status = LeaveApplication.SUB_STATUS_ACCEPTED
        application.substitute_remarks = remarks
        application.substitute_responded_at = timezone.now()
        application.status = (
            LeaveApplication.STATUS_AWAITING_DIRECTOR
            if is_director
            else LeaveApplication.STATUS_AWAITING_UNIT_HEAD
        )
        action_name = "SUBSTITUTE_ACCEPTED"
    elif action == "decline":
        application.substitute_status = LeaveApplication.SUB_STATUS_DECLINED
        application.substitute_remarks = remarks
        application.substitute_responded_at = timezone.now()
        application.status = LeaveApplication.STATUS_SUBSTITUTE_DECLINED
        action_name = "SUBSTITUTE_DECLINED"
    else:
        raise ValidationError("Invalid action: must be 'accept' or 'decline'.")

    application.save()
    LeaveWorkflowHistory.objects.create(
        application=application,
        actor_id=substitute_id,
        action=action_name,
        from_state=from_state,
        to_state=application.status,
        remarks=remarks,
    )
    return application


@transaction.atomic
def nominate_replacement_substitute(
    application: LeaveApplication,
    applicant_id: str,
    new_substitute_id: str,
    remarks: str = "",
) -> LeaveApplication:
    """Applicant nominates another substitute after decline per EL-UC-019."""
    if application.applicant_id != applicant_id:
        raise ValidationError("Only the applicant can nominate a replacement substitute.")

    if application.status != LeaveApplication.STATUS_SUBSTITUTE_DECLINED:
        raise ValidationError(
            "Replacement substitute nomination is only valid after substitute decline."
        )

    if new_substitute_id == applicant_id:
        raise ValidationError("Cannot nominate self as substitute.")

    from_state = application.status
    application.substitute_id = new_substitute_id
    application.substitute_status = LeaveApplication.SUB_STATUS_PENDING
    application.substitute_remarks = ""
    application.substitute_responded_at = None
    application.status = LeaveApplication.STATUS_AWAITING_SUBSTITUTE
    application.save()

    LeaveWorkflowHistory.objects.create(
        application=application,
        actor_id=applicant_id,
        action="REPLACEMENT_SUBSTITUTE_NOMINATED",
        from_state=from_state,
        to_state=application.status,
        remarks=f"Nominated replacement: {new_substitute_id}. {remarks}",
    )
    return application


@transaction.atomic
def review_by_unit_head(
    application: LeaveApplication,
    unit_head_id: str,
    action: str,
    recommendation: str = "",
    remarks: str = "",
) -> LeaveApplication:
    """Unit Head review: final for CL/RH; recommends higher-sanction per BR-EL-016/017."""
    if application.status != LeaveApplication.STATUS_AWAITING_UNIT_HEAD:
        raise ValidationError("Application is not awaiting Unit Head review.")

    from_state = application.status
    code = application.leave_type.code
    now = timezone.now()

    if code in ("CL", "RH"):
        if action == "approve":
            application.status = LeaveApplication.STATUS_APPROVED
            application.unit_head_id = unit_head_id
            application.unit_head_remarks = remarks
            application.unit_head_action_at = now
            _deduct_leave_balance(application)
            action_name = "APPROVED"
        elif action == "reject":
            application.status = LeaveApplication.STATUS_REJECTED
            application.unit_head_id = unit_head_id
            application.unit_head_remarks = remarks
            application.unit_head_action_at = now
            action_name = "REJECTED"
        else:
            raise ValidationError("Action for CL/RH must be 'approve' or 'reject'.")
    else:
        rec = recommendation or ("RECOMMENDED" if action == "recommend" else "NOT_RECOMMENDED")
        application.unit_head_id = unit_head_id
        application.unit_head_recommendation = rec
        application.unit_head_remarks = remarks
        application.unit_head_action_at = now
        application.status = LeaveApplication.STATUS_AWAITING_SANCTION
        action_name = f"UNIT_HEAD_{rec}"

    application.save()
    LeaveWorkflowHistory.objects.create(
        application=application,
        actor_id=unit_head_id,
        action=action_name,
        from_state=from_state,
        to_state=application.status,
        remarks=remarks,
    )
    return application


@transaction.atomic
def review_by_sanctioning_authority(
    application: LeaveApplication,
    authority_id: str,
    action: str,
    remarks: str = "",
) -> LeaveApplication:
    """Final sanction decision for higher-sanction requests per EL-UC-005."""
    valid_states = [
        LeaveApplication.STATUS_AWAITING_SANCTION,
        LeaveApplication.STATUS_AWAITING_DIRECTOR,
    ]
    if application.status not in valid_states:
        raise ValidationError("Application is not awaiting sanctioning authority decision.")

    from_state = application.status
    now = timezone.now()

    if action == "approve":
        application.status = LeaveApplication.STATUS_APPROVED
        application.sanctioning_authority_id = authority_id
        application.sanction_remarks = remarks
        application.sanctioned_at = now
        _deduct_leave_balance(application)
        action_name = "APPROVED"
    elif action == "reject":
        application.status = LeaveApplication.STATUS_REJECTED
        application.sanctioning_authority_id = authority_id
        application.sanction_remarks = remarks
        application.sanctioned_at = now
        action_name = "REJECTED"
    else:
        raise ValidationError("Action must be 'approve' or 'reject'.")

    application.save()
    LeaveWorkflowHistory.objects.create(
        application=application,
        actor_id=authority_id,
        action=action_name,
        from_state=from_state,
        to_state=application.status,
        remarks=remarks,
    )
    return application


@transaction.atomic
def withdraw_leave_application(
    application: LeaveApplication,
    applicant_id: str,
    remarks: str = "",
) -> LeaveApplication:
    """Immediate withdrawal of pending request per BR-EL-022 and EL-UC-007."""
    if application.applicant_id != applicant_id:
        raise ValidationError("Only the applicant can withdraw their leave application.")

    pending_states = [
        LeaveApplication.STATUS_DRAFT,
        LeaveApplication.STATUS_AWAITING_SUBSTITUTE,
        LeaveApplication.STATUS_SUBSTITUTE_DECLINED,
        LeaveApplication.STATUS_AWAITING_UNIT_HEAD,
        LeaveApplication.STATUS_AWAITING_ESTABLISHMENT,
        LeaveApplication.STATUS_AWAITING_SANCTION,
        LeaveApplication.STATUS_AWAITING_DIRECTOR,
    ]
    if application.status not in pending_states:
        raise ValidationError(
            f"Cannot withdraw application in non-pending state '{application.status}'."
        )

    from_state = application.status
    application.status = LeaveApplication.STATUS_WITHDRAWN
    application.save()

    LeaveWorkflowHistory.objects.create(
        application=application,
        actor_id=applicant_id,
        action="WITHDRAWN",
        from_state=from_state,
        to_state=application.status,
        remarks=remarks,
    )
    return application


@transaction.atomic
def request_approved_leave_cancellation(
    application: LeaveApplication,
    applicant_id: str,
    reason: str,
) -> LeaveApplication:
    """Request pre-start cancellation of approved leave per BR-EL-023 and EL-UC-008."""
    if application.applicant_id != applicant_id:
        raise ValidationError("Only the applicant can request cancellation.")

    if application.status != LeaveApplication.STATUS_APPROVED:
        raise ValidationError("Only approved leave can be cancelled.")

    today = timezone.localdate()
    if today >= application.start_date:
        raise ValidationError(
            "Pre-start cancellation is unavailable once leave date has arrived or passed."
        )

    from_state = application.status
    application.status = LeaveApplication.STATUS_CANCELLATION_REQUESTED
    application.cancellation_reason = reason
    application.cancellation_requested_at = timezone.now()
    application.save()

    LeaveWorkflowHistory.objects.create(
        application=application,
        actor_id=applicant_id,
        action="CANCELLATION_REQUESTED",
        from_state=from_state,
        to_state=application.status,
        remarks=reason,
    )
    return application


@transaction.atomic
def review_cancellation_request(
    application: LeaveApplication,
    reviewer_id: str,
    action: str,
    remarks: str = "",
) -> LeaveApplication:
    """Review cancellation request and restore balance on approval per BR-EL-023."""
    if application.status != LeaveApplication.STATUS_CANCELLATION_REQUESTED:
        raise ValidationError("Application is not pending cancellation review.")

    from_state = application.status
    if action == "approve":
        application.status = LeaveApplication.STATUS_CANCELLED
        _restore_leave_balance(application)
        action_name = "CANCELLATION_APPROVED"
    elif action == "reject":
        application.status = LeaveApplication.STATUS_APPROVED
        action_name = "CANCELLATION_REJECTED"
    else:
        raise ValidationError("Action must be 'approve' or 'reject'.")

    application.save()
    LeaveWorkflowHistory.objects.create(
        application=application,
        actor_id=reviewer_id,
        action=action_name,
        from_state=from_state,
        to_state=application.status,
        remarks=remarks,
    )
    return application


@transaction.atomic
def submit_resumption_of_duty(
    application: LeaveApplication,
    applicant_id: str,
    resumption_date: date,
    remarks: str = "",
) -> LeaveApplication:
    """Submit actual resumption date following EL/COL/VL per BR-EL-027 and EL-UC-010."""
    if application.applicant_id != applicant_id:
        raise ValidationError("Only the applicant can submit resumption of duty.")

    if application.status != LeaveApplication.STATUS_APPROVED:
        raise ValidationError("Resumption can only be submitted for approved leave.")

    if application.leave_type.code not in ("EL", "COL", "VL"):
        raise ValidationError(
            "Resumption workflow applies exclusively to EL, COL, and VL categories."
        )

    application.resumption_date = resumption_date
    application.resumption_remarks = remarks
    application.resumption_status = LeaveApplication.RESUMPTION_PENDING
    application.save()

    LeaveWorkflowHistory.objects.create(
        application=application,
        actor_id=applicant_id,
        action="RESUMPTION_SUBMITTED",
        from_state=application.status,
        to_state=application.status,
        remarks=f"Resumed on {resumption_date}. {remarks}",
    )
    return application


@transaction.atomic
def review_resumption_submission(
    application: LeaveApplication,
    reviewer_id: str,
    action: str,
    remarks: str = "",
) -> LeaveApplication:
    """Review resumption and adjust balance for early or late return per BR-EL-028."""
    if application.resumption_status != LeaveApplication.RESUMPTION_PENDING:
        raise ValidationError("Resumption is not pending review.")

    if not application.resumption_date:
        raise ValidationError("Resumption date is missing.")

    if action == "approve":
        application.resumption_status = LeaveApplication.RESUMPTION_APPROVED
        application.resumption_reviewer_id = reviewer_id
        application.resumption_reviewed_at = timezone.now()

        expected_return = application.end_date + timedelta(days=1)
        actual_return = application.resumption_date

        if actual_return < expected_return:
            actual_end = actual_return - timedelta(days=1)
            actual_days = calculate_leave_days(
                application.leave_type, application.start_date, actual_end
            )
            saved_days = application.leave_days - actual_days
            if saved_days > Decimal("0.0"):
                _adjust_consumed_balance(application, -saved_days)
                application.leave_days = actual_days
                application.end_date = actual_end
        elif actual_return > expected_return:
            extra_start = expected_return
            extra_end = actual_return - timedelta(days=1)
            extra_days = calculate_leave_days(
                application.leave_type, extra_start, extra_end
            )
            if extra_days > Decimal("0.0"):
                _adjust_consumed_balance(application, extra_days)
                application.leave_days += extra_days
                application.end_date = extra_end

        application.save()
        LeaveWorkflowHistory.objects.create(
            application=application,
            actor_id=reviewer_id,
            action="RESUMPTION_APPROVED",
            from_state=application.status,
            to_state=application.status,
            remarks=remarks,
        )
    elif action == "reject":
        application.resumption_status = LeaveApplication.RESUMPTION_REJECTED
        application.resumption_reviewer_id = reviewer_id
        application.resumption_reviewed_at = timezone.now()
        application.save()
        LeaveWorkflowHistory.objects.create(
            application=application,
            actor_id=reviewer_id,
            action="RESUMPTION_REJECTED",
            from_state=application.status,
            to_state=application.status,
            remarks=remarks,
        )
    else:
        raise ValidationError("Action must be 'approve' or 'reject'.")

    return application


def _deduct_leave_balance(application: LeaveApplication) -> None:
    balance = get_or_create_balance(
        application.applicant_id, application.leave_type, application.start_date.year
    )
    balance.consumed += application.leave_days
    balance.save(update_fields=["consumed", "updated_at"])


def _restore_leave_balance(application: LeaveApplication) -> None:
    balance = get_or_create_balance(
        application.applicant_id, application.leave_type, application.start_date.year
    )
    balance.consumed = max(Decimal("0.0"), balance.consumed - application.leave_days)
    balance.save(update_fields=["consumed", "updated_at"])


def _adjust_consumed_balance(application: LeaveApplication, delta_days: Decimal) -> None:
    balance = get_or_create_balance(
        application.applicant_id, application.leave_type, application.start_date.year
    )
    balance.consumed = max(Decimal("0.0"), balance.consumed + delta_days)
    balance.save(update_fields=["consumed", "updated_at"])
