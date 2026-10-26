from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.core.exceptions import ValidationError

from modules.leave_elm.models import (
    LeaveType,
    LeaveBalance,
    LeaveApplication,
    LeaveAction,
    HolidayCalendar,
)


def calculate_leave_days(leave_type_code: str, start_date: date, end_date: date, half_day: bool = False, half_day_period: str = 'NONE') -> Decimal:
    """
    Computes duration in days according to BR-EL-010 and BR-EL-011:
    - Half-day CL: 0.5 days.
    - EL, COL, VL: Continuous-day counting including intervening weekends and holidays.
    - CL, SCL, RH: Excludes weekends (Saturday/Sunday) and published closed holidays.
    """
    if start_date > end_date:
        raise ValidationError("End date cannot be earlier than start date.")

    if half_day:
        if start_date != end_date:
            raise ValidationError("Half-day leave must be on a single date.")
        if half_day_period not in ['FIRST_HALF', 'SECOND_HALF']:
            raise ValidationError("Half-day leave must specify FIRST_HALF or SECOND_HALF.")
        return Decimal('0.5')

    code = leave_type_code.upper()
    total_calendar_days = (end_date - start_date).days + 1

    if code in ['EL', 'COL', 'VL']:
        # BR-EL-011: Continuous counting across the approved interval
        return Decimal(str(total_calendar_days))

    # For CL, SCL, RH: Exclude Saturdays, Sundays, and closed holidays
    current_date = start_date
    working_days = 0
    closed_holidays = set(
        HolidayCalendar.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            is_restricted_holiday=False
        ).values_list('date', flat=True)
    )

    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in closed_holidays:
            working_days += 1
        current_date += timedelta(days=1)

    return Decimal(str(working_days))


def check_leave_overlap(
    applicant_username: str,
    start_date: date,
    end_date: date,
    half_day: bool = False,
    half_day_period: str = 'NONE',
    exclude_application_id: int = None
) -> None:
    """
    BR-EL-012: Enforces applicant non-overlap with active pending/approved leaves.
    Exception: Single-date half-day CL permitted on the same date if different halves.
    """
    active_statuses = [
        'SUBSTITUTE_PENDING',
        'PENDING_UNIT_HEAD',
        'PENDING_HIGHER_SANCTION',
        'APPROVED'
    ]

    overlapping_apps = LeaveApplication.objects.filter(
        applicant_username=applicant_username,
        status__in=active_statuses,
        start_date__lte=end_date,
        end_date__gte=start_date
    )

    if exclude_application_id:
        overlapping_apps = overlapping_apps.exclude(pk=exclude_application_id)

    for app in overlapping_apps:
        # Check half-day CL non-overlap exception (BR-EL-012)
        if (
            start_date == end_date and
            app.start_date == app.end_date and
            start_date == app.start_date and
            half_day and app.half_day and
            app.leave_type.code == 'CL' and
            half_day_period in ['FIRST_HALF', 'SECOND_HALF'] and
            app.half_day_period in ['FIRST_HALF', 'SECOND_HALF'] and
            half_day_period != app.half_day_period
        ):
            # Non-overlapping halves on the same date: permitted!
            continue
        
        raise ValidationError(
            f"Impermissible overlap with existing application #{app.id} "
            f"({app.leave_type.code}: {app.start_date} to {app.end_date}, status: {app.status})."
        )


def validate_substitute_eligibility(
    applicant_username: str,
    substitute_username: str,
    start_date: date,
    end_date: date
) -> None:
    """
    BR-EL-014:
    - Substitute must not be the applicant.
    - Substitute must have no overlapping pending or approved leave during responsibility period.
    """
    if not substitute_username:
        return

    if substitute_username.strip().lower() == applicant_username.strip().lower():
        raise ValidationError("Applicant cannot be their own substitute.")

    active_statuses = [
        'SUBSTITUTE_PENDING',
        'PENDING_UNIT_HEAD',
        'PENDING_HIGHER_SANCTION',
        'APPROVED'
    ]

    substitute_leaves = LeaveApplication.objects.filter(
        applicant_username=substitute_username,
        status__in=active_statuses,
        start_date__lte=end_date,
        end_date__gte=start_date
    )

    if substitute_leaves.exists():
        first_conflict = substitute_leaves.first()
        raise ValidationError(
            f"Nominated substitute '{substitute_username}' is on leave during this period "
            f"(App #{first_conflict.id}: {first_conflict.start_date} to {first_conflict.end_date})."
        )


@transaction.atomic
def apply_leave(
    applicant_username: str,
    leave_type_code: str,
    start_date: date,
    end_date: date,
    half_day: bool = False,
    half_day_period: str = 'NONE',
    reason: str = '',
    substitute_username: str = None,
    station_leave: bool = False,
    station_details: dict = None,
    is_extension: bool = False,
    original_application: LeaveApplication = None,
    actor_username: str = None
) -> LeaveApplication:
    """
    Validates rules, computes days, checks balance, and creates application.
    """
    try:
        leave_type = LeaveType.objects.get(code=leave_type_code.upper(), is_active=True)
    except LeaveType.DoesNotExist:
        raise ValidationError(f"Invalid or inactive leave type: {leave_type_code}")

    # BR-EL-003: Restricted Holiday check
    if leave_type.code == 'RH':
        if start_date != end_date:
            raise ValidationError("Restricted Holiday (RH) must be requested for exactly one day.")
        rh_exists = HolidayCalendar.objects.filter(
            date=start_date,
            is_restricted_holiday=True
        ).exists()
        if not rh_exists:
            raise ValidationError(f"{start_date} is not an applicable published Restricted Holiday.")

    # Calculate days count (BR-EL-010, BR-EL-011)
    days_count = calculate_leave_days(
        leave_type_code=leave_type.code,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        half_day_period=half_day_period
    )

    # Check non-overlap (BR-EL-012)
    check_leave_overlap(
        applicant_username=applicant_username,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        half_day_period=half_day_period
    )

    # Substitute eligibility (BR-EL-014)
    if substitute_username:
        validate_substitute_eligibility(
            applicant_username=applicant_username,
            substitute_username=substitute_username,
            start_date=start_date,
            end_date=end_date
        )

    # Check balance sufficiency
    year = start_date.year
    balance_record, _ = LeaveBalance.objects.get_or_create(
        username=applicant_username,
        leave_type=leave_type,
        year=year,
        defaults={
            'balance': leave_type.max_days_per_year,
            'credited': leave_type.max_days_per_year,
            'utilized': Decimal('0.0')
        }
    )

    if balance_record.balance < days_count:
        raise ValidationError(
            f"Insufficient {leave_type.code} balance. Required: {days_count}, Available: {balance_record.balance}"
        )

    # BR-EL-013: Station leave coupling
    if station_leave and not station_details:
        raise ValidationError("Station details (address, contact, timing) are required for Station Leave.")

    # Determine initial workflow state (BR-EL-015)
    if substitute_username:
        status = 'SUBSTITUTE_PENDING'
        substitute_status = 'PENDING'
    else:
        status = 'PENDING_UNIT_HEAD'
        substitute_status = 'NOT_REQUIRED'

    application = LeaveApplication.objects.create(
        applicant_username=applicant_username,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        half_day_period=half_day_period,
        days_count=days_count,
        status=status,
        reason=reason,
        substitute_username=substitute_username,
        substitute_status=substitute_status,
        station_leave=station_leave,
        station_details=station_details,
        is_extension=is_extension,
        original_application=original_application
    )

    LeaveAction.objects.create(
        application=application,
        actor_username=actor_username or applicant_username,
        action='SUBMITTED',
        remarks=f"Applied for {days_count} day(s) of {leave_type.code}."
    )

    return application


@transaction.atomic
def respond_substitute(
    application: LeaveApplication,
    substitute_username: str,
    accept: bool,
    remarks: str = ''
) -> LeaveApplication:
    """
    BR-EL-015: Substitute consent gate and decline recovery.
    - Accept releases the routing gate to PENDING_UNIT_HEAD.
    - Decline leaves gate closed (substitute_status='DECLINED').
    """
    if application.status != 'SUBSTITUTE_PENDING':
        raise ValidationError("Application is not awaiting substitute consent.")

    if application.substitute_username != substitute_username:
        raise ValidationError("User is not the nominated substitute for this application.")

    if accept:
        application.substitute_status = 'ACCEPTED'
        application.substitute_remarks = remarks
        application.status = 'PENDING_UNIT_HEAD'
        application.save()

        LeaveAction.objects.create(
            application=application,
            actor_username=substitute_username,
            action='SUBSTITUTE_ACCEPTED',
            remarks=remarks
        )
    else:
        application.substitute_status = 'DECLINED'
        application.substitute_remarks = remarks
        application.save()

        LeaveAction.objects.create(
            application=application,
            actor_username=substitute_username,
            action='SUBSTITUTE_DECLINED',
            remarks=remarks
        )

    return application


@transaction.atomic
def nominate_new_substitute(
    application: LeaveApplication,
    applicant_username: str,
    new_substitute_username: str
) -> LeaveApplication:
    """
    Recovery path when previous substitute declined (BR-EL-015).
    """
    if application.applicant_username != applicant_username:
        raise ValidationError("Only the applicant can nominate a new substitute.")

    if application.status != 'SUBSTITUTE_PENDING' or application.substitute_status != 'DECLINED':
        raise ValidationError("A new substitute can only be nominated when the previous substitute declined.")

    validate_substitute_eligibility(
        applicant_username=applicant_username,
        substitute_username=new_substitute_username,
        start_date=application.start_date,
        end_date=application.end_date
    )

    application.substitute_username = new_substitute_username
    application.substitute_status = 'PENDING'
    application.substitute_remarks = ''
    application.save()

    LeaveAction.objects.create(
        application=application,
        actor_username=applicant_username,
        action='COMMENTED',
        remarks=f"Nominated new substitute: {new_substitute_username}."
    )

    return application


@transaction.atomic
def process_unit_head_decision(
    application: LeaveApplication,
    actor_username: str,
    decision: str,  # 'APPROVE', 'REJECT', 'RECOMMEND', 'NOT_RECOMMEND'
    remarks: str = ''
) -> LeaveApplication:
    """
    BR-EL-016: For CL and RH, Unit Head is the final authority.
    BR-EL-017: For SCL, EL, COL, VL, Unit Head records Recommendation (RECOMMENDED / NOT_RECOMMENDED),
    and both outcomes continue to Higher Sanction path!
    """
    if application.status != 'PENDING_UNIT_HEAD':
        raise ValidationError("Application is not pending Unit Head action.")

    code = application.leave_type.code.upper()

    if code in ['CL', 'RH']:
        # Final decision scope (BR-EL-016)
        if decision == 'APPROVE':
            application.status = 'APPROVED'
            # Deduct balance
            _deduct_leave_balance(application)
            action_code = 'APPROVED'
        elif decision == 'REJECT':
            application.status = 'REJECTED'
            action_code = 'REJECTED'
        else:
            raise ValidationError(f"Invalid Unit Head decision '{decision}' for {code}. Expected APPROVE or REJECT.")

        application.unit_head_remarks = remarks
        application.save()

        LeaveAction.objects.create(
            application=application,
            actor_username=actor_username,
            action=action_code,
            remarks=remarks
        )

    else:
        # Higher-sanction path recommendation (BR-EL-017)
        if decision in ['RECOMMEND', 'APPROVE']:
            application.unit_head_recommendation = 'RECOMMENDED'
            action_code = 'RECOMMENDED'
        elif decision in ['NOT_RECOMMEND', 'REJECT']:
            application.unit_head_recommendation = 'NOT_RECOMMENDED'
            action_code = 'NOT_RECOMMENDED'
        else:
            raise ValidationError(f"Invalid decision '{decision}'. Expected RECOMMEND or NOT_RECOMMEND.")

        application.unit_head_remarks = remarks
        application.status = 'PENDING_HIGHER_SANCTION'
        application.save()

        LeaveAction.objects.create(
            application=application,
            actor_username=actor_username,
            action=action_code,
            remarks=remarks
        )

    return application


@transaction.atomic
def process_higher_sanction_decision(
    application: LeaveApplication,
    actor_username: str,
    decision: str,  # 'APPROVE', 'REJECT'
    remarks: str = ''
) -> LeaveApplication:
    """
    BR-EL-018: Final Sanctioning Authority decision for SCL, EL, COL, VL.
    """
    if application.status != 'PENDING_HIGHER_SANCTION':
        raise ValidationError("Application is not pending Higher Sanction approval.")

    if decision == 'APPROVE':
        application.status = 'APPROVED'
        _deduct_leave_balance(application)
        action_code = 'APPROVED'
    elif decision == 'REJECT':
        application.status = 'REJECTED'
        action_code = 'REJECTED'
    else:
        raise ValidationError("Invalid sanction decision. Expected APPROVE or REJECT.")

    application.higher_sanction_authority = actor_username
    application.sanction_remarks = remarks
    application.save()

    LeaveAction.objects.create(
        application=application,
        actor_username=actor_username,
        action=action_code,
        remarks=remarks
    )

    return application


@transaction.atomic
def withdraw_application(
    application: LeaveApplication,
    applicant_username: str,
    remarks: str = ''
) -> LeaveApplication:
    """
    BR-EL-022: Immediate withdrawal of pending request before final approval.
    """
    if application.applicant_username != applicant_username:
        raise ValidationError("Only the applicant can withdraw their application.")

    if application.status in ['APPROVED', 'REJECTED', 'WITHDRAWN', 'CANCELLED']:
        raise ValidationError(f"Cannot withdraw application in '{application.status}' state.")

    application.status = 'WITHDRAWN'
    application.save()

    LeaveAction.objects.create(
        application=application,
        actor_username=applicant_username,
        action='WITHDRAWN',
        remarks=remarks or "Application withdrawn by applicant."
    )

    return application


@transaction.atomic
def cancel_approved_leave(
    application: LeaveApplication,
    applicant_username: str,
    reason: str,
    current_date: date = None
) -> LeaveApplication:
    """
    BR-EL-023: Cancellation of approved leave before start.
    - Allowed only before start date (today < start_date).
    - Restores deducted balance.
    """
    if application.applicant_username != applicant_username:
        raise ValidationError("Only the applicant can cancel their approved leave.")

    if application.status != 'APPROVED':
        raise ValidationError("Only approved leave can be cancelled.")

    check_date = current_date or date.today()
    if check_date >= application.start_date:
        raise ValidationError("Approved leave can only be cancelled before its start date.")

    if not reason:
        raise ValidationError("Cancellation reason is required.")

    application.status = 'CANCELLED'
    application.cancellation_reason = reason
    application.save()

    # Restore balance
    _restore_leave_balance(application)

    LeaveAction.objects.create(
        application=application,
        actor_username=applicant_username,
        action='CANCELLED',
        remarks=f"Cancellation before start date: {reason}"
    )

    return application


@transaction.atomic
def convert_faculty_vl_to_el(faculty_username: str, year: int) -> Decimal:
    """
    BR-EL-007 & BR-EL-008:
    At year end, all unused faculty VL converts to EL at 2 VL : 1 EL,
    including fractional conversion. Converted EL is credited to the faculty EL balance,
    may carry forward, and VL itself lapses.
    """
    try:
        vl_type = LeaveType.objects.get(code='VL')
        el_type = LeaveType.objects.get(code='EL')
    except LeaveType.DoesNotExist:
        raise ValidationError("Leave types VL or EL not found in system.")

    vl_balance_obj = LeaveBalance.objects.filter(
        username=faculty_username,
        leave_type=vl_type,
        year=year
    ).first()

    if not vl_balance_obj or vl_balance_obj.balance <= Decimal('0.0'):
        return Decimal('0.0')

    unused_vl = vl_balance_obj.balance
    converted_el = unused_vl / Decimal('2.0')

    # Update VL balance: utilized becomes credited, balance becomes 0
    vl_balance_obj.utilized = vl_balance_obj.credited
    vl_balance_obj.balance = Decimal('0.0')
    vl_balance_obj.save()

    # Credit converted EL to EL balance
    el_balance_obj, _ = LeaveBalance.objects.get_or_create(
        username=faculty_username,
        leave_type=el_type,
        year=year,
        defaults={
            'balance': el_type.max_days_per_year,
            'credited': el_type.max_days_per_year,
            'utilized': Decimal('0.0')
        }
    )
    el_balance_obj.balance += converted_el
    el_balance_obj.credited += converted_el
    el_balance_obj.save()

    return converted_el


@transaction.atomic
def process_resumption(
    application: LeaveApplication,
    actual_resumption_date: date,
    actor_username: str,
    remarks: str = ''
) -> LeaveApplication:
    """
    BR-EL-027 & BR-EL-028: Return from EL/COL/VL resumption review.
    - If actual resumption equals approved end date: no balance adjustment.
    - If actual resumption is earlier or later: adjusts balance according to actual duration.
    """
    if application.leave_type.code not in ['EL', 'COL', 'VL']:
        raise ValidationError("Resumption review applies only to EL, COL, and VL.")

    if application.status != 'APPROVED':
        raise ValidationError("Resumption can only be submitted for approved leaves.")

    application.actual_resumption_date = actual_resumption_date
    application.save()

    expected_end = application.end_date
    if actual_resumption_date != expected_end:
        # Recompute actual days
        actual_days = calculate_leave_days(
            leave_type_code=application.leave_type.code,
            start_date=application.start_date,
            end_date=actual_resumption_date
        )
        diff = actual_days - application.days_count

        year = application.start_date.year
        balance_obj = LeaveBalance.objects.get(
            username=application.applicant_username,
            leave_type=application.leave_type,
            year=year
        )

        balance_obj.balance -= diff
        balance_obj.utilized += diff
        balance_obj.save()

        application.days_count = actual_days
        application.save()

    LeaveAction.objects.create(
        application=application,
        actor_username=actor_username,
        action='RESUMPTION_RECORDED',
        remarks=remarks or f"Resumed on {actual_resumption_date}."
    )

    return application


def _deduct_leave_balance(application: LeaveApplication) -> None:
    year = application.start_date.year
    balance_obj = LeaveBalance.objects.get(
        username=application.applicant_username,
        leave_type=application.leave_type,
        year=year
    )
    balance_obj.balance -= application.days_count
    balance_obj.utilized += application.days_count
    balance_obj.save()


def _restore_leave_balance(application: LeaveApplication) -> None:
    year = application.start_date.year
    balance_obj = LeaveBalance.objects.get(
        username=application.applicant_username,
        leave_type=application.leave_type,
        year=year
    )
    balance_obj.balance += application.days_count
    balance_obj.utilized -= application.days_count
    balance_obj.save()
