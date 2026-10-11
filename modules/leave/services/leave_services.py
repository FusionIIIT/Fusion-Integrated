"""Services for Employee Leave Management (ELM).
Handles state transitions, DB transactions, balance updates, and audit logs.
"""
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from modules.leave.models import (
    LeaveApplication, LeaveBalance, LeaveWorkflowActionLog,
    HolidayCalendar, LeavePolicy, VacationPeriod
)
from modules.leave.domain import rules


@transaction.atomic
def apply_leave(
    applicant_id: str,
    applicant_role: str,
    category: str,
    start_date: date,
    end_date: date,
    purpose: str,
    is_half_day: bool = False,
    half_day_type: str = None,
    is_station_leave: bool = False,
    station_leave_destination: str = None,
    substitute_id: str = None,
    unit_head_id: str = None,
) -> LeaveApplication:
    """EL-UC-001 (CW-EL-01): Submit leave application with full business validations."""
    if start_date > end_date:
        raise ValidationError("Start date cannot be after end date.")

    # Validate category
    if category not in rules.LEAVE_CATEGORIES:
        raise ValidationError(f"Invalid leave category: {category}")

    # Station Leave coupling (BR-EL-013)
    if is_station_leave and not station_leave_destination:
        raise ValidationError("Station leave destination is required.")

    # Substitute validation (BR-EL-014)
    requires_substitute = bool(substitute_id)
    if requires_substitute:
        if substitute_id == applicant_id:
            raise ValidationError("Applicant cannot nominate self as substitute (BR-EL-014).")

        # Substitute overlap check
        sub_overlaps = LeaveApplication.objects.filter(
            applicant_id=substitute_id,
            status__in=["APPROVED", "AWAITING_UNIT_HEAD", "AWAITING_SANCTION"],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()
        if sub_overlaps:
            raise ValidationError("Nominated substitute has active/pending leave during this period.")

    # Applicant Overlap check (BR-EL-012)
    active_leaves = LeaveApplication.objects.filter(
        applicant_id=applicant_id,
        status__in=["APPROVED", "AWAITING_UNIT_HEAD", "AWAITING_SANCTION", "AWAITING_SUBSTITUTE"],
    )
    for existing in active_leaves:
        if rules.check_leave_overlap(
            start_date, end_date, is_half_day, half_day_type,
            existing.start_date, existing.end_date, existing.is_half_day, existing.half_day_type
        ):
            raise ValidationError("Impermissible overlap with an active or pending leave request (BR-EL-012).")

    # Calendar and counting (BR-EL-010, BR-EL-011)
    holidays = list(HolidayCalendar.objects.filter(is_published=True).values_list("date", flat=True))
    chargeable = rules.calculate_chargeable_days(category, start_date, end_date, is_half_day, holidays)

    # Balance validation (BR-EL-002, 003, 004, 005, 009)
    current_year = start_date.year
    bal_record, _ = LeaveBalance.objects.get_or_create(
        user_id=applicant_id, category=category, year=current_year,
        defaults={"balance": 0.0}
    )
    if bal_record.balance < chargeable:
        raise ValidationError(f"Insufficient leave balance for {category}. Available: {bal_record.balance}, Requested: {chargeable}")

    initial_status = rules.determine_initial_routing_state(category, applicant_role, requires_substitute)

    app = LeaveApplication.objects.create(
        applicant_id=applicant_id,
        applicant_role=applicant_role,
        category=category,
        start_date=start_date,
        end_date=end_date,
        chargeable_days=chargeable,
        purpose=purpose,
        is_half_day=is_half_day,
        half_day_type=half_day_type,
        is_station_leave=is_station_leave,
        station_leave_destination=station_leave_destination,
        requires_substitute=requires_substitute,
        substitute_id=substitute_id,
        substitute_status="PENDING" if requires_substitute else "NOT_REQUIRED",
        unit_head_id=unit_head_id,
        status=initial_status,
    )

    LeaveWorkflowActionLog.objects.create(
        application=app, actor_id=applicant_id, action="SUBMIT",
        from_status="DRAFT", to_status=initial_status, remarks="Application submitted."
    )
    return app


@transaction.atomic
def respond_substitute(application_id: int, substitute_id: str, accept: bool) -> LeaveApplication:
    """EL-UC-002 (BW-EL-02, BW-EL-03): Substitute accepts or declines."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id)
    if app.substitute_id != substitute_id or app.status != rules.STATUS_AWAITING_SUBSTITUTE:
        raise ValidationError("Invalid substitute action or task no longer pending.")

    from_status = app.status
    if accept:
        app.substitute_status = "ACCEPTED"
        if app.applicant_role == "director":
            app.status = rules.STATUS_AWAITING_DIRECTOR
        else:
            app.status = rules.STATUS_AWAITING_UNIT_HEAD
    else:
        app.substitute_status = "DECLINED"
        app.status = rules.STATUS_APPLICANT_ACTION_REQUIRED

    app.save()
    LeaveWorkflowActionLog.objects.create(
        application=app, actor_id=substitute_id,
        action="SUBSTITUTE_ACCEPT" if accept else "SUBSTITUTE_DECLINE",
        from_status=from_status, to_status=app.status
    )
    return app


@transaction.atomic
def nominate_replacement_substitute(application_id: int, applicant_id: str, replacement_id: str) -> LeaveApplication:
    """EL-UC-019 (BW-EL-03): Nominate replacement substitute after decline."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id)
    if app.applicant_id != applicant_id or app.status != rules.STATUS_APPLICANT_ACTION_REQUIRED:
        raise ValidationError("Application not in Applicant Action Required state.")

    if replacement_id == applicant_id:
        raise ValidationError("Applicant cannot nominate self.")

    app.substitute_id = replacement_id
    app.substitute_status = "PENDING"
    app.status = rules.STATUS_AWAITING_SUBSTITUTE
    app.save()

    LeaveWorkflowActionLog.objects.create(
        application=app, actor_id=applicant_id, action="REPLACE_SUBSTITUTE",
        from_status=rules.STATUS_APPLICANT_ACTION_REQUIRED, to_status=app.status
    )
    return app


@transaction.atomic
def unit_head_review(
    application_id: int,
    unit_head_id: str,
    action: str,  # 'APPROVE', 'REJECT', 'RECOMMEND', 'NOT_RECOMMEND'
    remarks: str = ""
) -> LeaveApplication:
    """EL-UC-003: Review at Unit Head level."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id)
    if app.status != rules.STATUS_AWAITING_UNIT_HEAD:
        raise ValidationError("Application not awaiting Unit Head review.")

    from_status = app.status

    # CL and RH final sanction (BR-EL-016)
    if app.category in ("CL", "RH"):
        if action == "APPROVE":
            app.status = rules.STATUS_APPROVED
            # Deduct balance
            bal = LeaveBalance.objects.get(user_id=app.applicant_id, category=app.category, year=app.start_date.year)
            bal.balance -= app.chargeable_days
            bal.save()
        elif action == "REJECT":
            app.status = rules.STATUS_REJECTED
            app.rejection_reason = remarks
        else:
            raise ValidationError("CL and RH require APPROVE or REJECT.")
    else:
        # SCL, EL, COL, VL recommendation (BR-EL-017)
        if action in ("RECOMMEND", "NOT_RECOMMEND"):
            app.unit_head_recommendation = "RECOMMENDED" if action == "RECOMMEND" else "NOT_RECOMMENDED"
            # Route to Sanctioning
            app.status = rules.STATUS_AWAITING_SANCTION
        else:
            raise ValidationError("Higher-sanction leave requires RECOMMEND or NOT_RECOMMEND.")

    app.save()
    LeaveWorkflowActionLog.objects.create(
        application=app, actor_id=unit_head_id, action=f"UH_{action}",
        from_status=from_status, to_status=app.status, remarks=remarks
    )
    return app


@transaction.atomic
def final_sanction(
    application_id: int,
    sanctioning_id: str,
    approve: bool,
    remarks: str = ""
) -> LeaveApplication:
    """EL-UC-005 (BW-EL-04-09): Sanctioning Authority final approve/reject."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id)
    if app.status not in (rules.STATUS_AWAITING_SANCTION, rules.STATUS_AWAITING_DIRECTOR):
        raise ValidationError("Application not awaiting final sanction.")

    from_status = app.status
    if approve:
        app.status = rules.STATUS_APPROVED
        # Deduct balance
        bal = LeaveBalance.objects.get(user_id=app.applicant_id, category=app.category, year=app.start_date.year)
        bal.balance -= app.chargeable_days
        bal.save()
    else:
        app.status = rules.STATUS_REJECTED
        app.rejection_reason = remarks

    app.save()
    LeaveWorkflowActionLog.objects.create(
        application=app, actor_id=sanctioning_id,
        action="FINAL_APPROVE" if approve else "FINAL_REJECT",
        from_status=from_status, to_status=app.status, remarks=remarks
    )
    return app


@transaction.atomic
def withdraw_application(application_id: int, applicant_id: str) -> LeaveApplication:
    """EL-UC-007 (BR-EL-022, BR-EL-034): Immediate withdrawal before final approval."""
    app = LeaveApplication.objects.select_for_update().get(id=application_id)
    if app.applicant_id != applicant_id:
        raise ValidationError("Unauthorized.")
    if app.status in (rules.STATUS_APPROVED, rules.STATUS_REJECTED, rules.STATUS_WITHDRAWN, rules.STATUS_CANCELLED):
        raise ValidationError("Cannot withdraw finalized request.")

    from_status = app.status
    app.status = rules.STATUS_WITHDRAWN
    app.save()

    LeaveWorkflowActionLog.objects.create(
        application=app, actor_id=applicant_id, action="WITHDRAW",
        from_status=from_status, to_status=rules.STATUS_WITHDRAWN
    )
    return app
