from datetime import date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.elm.domain.constants import (
    CL,
    DECISION_APPROVED,
    DECISION_REJECTED,
    LEAVE_CATEGORIES,
    RECOMMENDATION_NOT_RECOMMENDED,
    RECOMMENDATION_RECOMMENDED,
    RH,
    STATUS_APPROVED,
    STATUS_CANCELLATION_REQUESTED,
    STATUS_CANCELLED,
    STATUS_PENDING_HIGHER_SANCTION,
    STATUS_PENDING_SUBSTITUTE,
    STATUS_PENDING_UNIT_HEAD,
    STATUS_REJECTED,
    STATUS_RESUMED,
    STATUS_SUBSTITUTE_DECLINED,
    STATUS_WITHDRAWN,
    SUBSTITUTE_ACCEPTED,
    SUBSTITUTE_DECLINED,
    VL,
)
from modules.elm.domain.counting import calculate_leave_days
from modules.elm.domain.eligibility import (
    check_overlap,
    validate_eligibility_and_balance,
    validate_substitute,
)
from modules.elm.domain.state_machine import (
    initial_status,
    transition_cancellation_decision,
    transition_higher_sanction,
    transition_request_cancellation,
    transition_resumption,
    transition_substitute_response,
    transition_unit_head_decision,
    transition_withdraw,
)
from modules.elm.models import (
    AcademicVacationPeriod,
    ApplicationTransition,
    EmployeeLeaveBalance,
    HolidayCalendar,
    LeaveApplication,
    WorkflowTask,
)
from modules.elm.selectors.balances import get_user_balances
from modules.elm.services.authz import require


@transaction.atomic
def submit_application(principal, data: dict) -> LeaveApplication:
    """Submit a new leave application (Sections 2, 5, 6)."""
    require(principal, "leave_elm.application.apply")

    category = data["leave_category"]
    start_date = data["start_date"]
    end_date = data["end_date"]
    half_day = data.get("half_day_type", "")
    reason = data.get("reason", "")
    substitute_id = data.get("substitute_user_id")

    # Fetch closed holidays and RH
    closed_holidays = set(
        HolidayCalendar.objects.filter(
            year=start_date.year, is_restricted_holiday=False, is_published=True
        ).values_list("date", flat=True)
    )
    rh_days = set(
        HolidayCalendar.objects.filter(
            year=start_date.year, is_restricted_holiday=True, is_published=True
        ).values_list("date", flat=True)
    )

    # Calculate leave days
    leave_days = calculate_leave_days(
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day_type=half_day,
        closed_holidays=closed_holidays,
    )

    # Check vacation period for VL
    is_vacation = AcademicVacationPeriod.objects.filter(
        start_date__lte=start_date, end_date__gte=end_date
    ).exists()

    # Get employee balance
    user_balances = {b.leave_category: b for b in get_user_balances(principal.user_id, start_date.year)}
    bal_obj = user_balances.get(category)
    available = bal_obj.available_days if bal_obj else Decimal("0.0")

    # Validate eligibility & balance
    is_rh = start_date in rh_days if category == RH else False
    try:
        validate_eligibility_and_balance(
            category=category,
            employee_kind=principal.kind,
            requested_days=leave_days,
            available_balance=available,
            start_date=start_date,
            is_vacation_period=is_vacation,
            is_rh_calendar_day=is_rh,
        )
    except Exception as exc:
        raise ValidationError(str(exc))

    # Overlap validation with active leaves
    existing = list(
        LeaveApplication.objects.filter(
            user_id=principal.user_id,
            status__in=[
                STATUS_PENDING_SUBSTITUTE,
                STATUS_PENDING_UNIT_HEAD,
                STATUS_PENDING_HIGHER_SANCTION,
                STATUS_APPROVED,
            ],
        ).values("start_date", "end_date", "leave_category", "half_day_type")
    )
    if check_overlap(start_date, end_date, category, half_day, existing):
        raise ValidationError("Leave request impermissibly overlaps with an active or pending leave.")

    # Validate substitute if nominated
    sub_status = "none"
    if substitute_id:
        sub_leaves = list(
            LeaveApplication.objects.filter(
                user_id=substitute_id,
                status__in=[
                    STATUS_PENDING_SUBSTITUTE,
                    STATUS_PENDING_UNIT_HEAD,
                    STATUS_PENDING_HIGHER_SANCTION,
                    STATUS_APPROVED,
                ],
            ).values("start_date", "end_date")
        )
        try:
            validate_substitute(principal.user_id, substitute_id, start_date, end_date, sub_leaves)
        except Exception as exc:
            raise ValidationError(str(exc))
        sub_status = "pending"

    # Determine initial status
    is_director = "Director" in getattr(principal, "roles", ())
    status = initial_status(has_substitute=bool(substitute_id), is_director_self=is_director)

    # Station Leave info
    is_station = data.get("is_station_leave", False)

    app = LeaveApplication.objects.create(
        user_id=principal.user_id,
        leave_category=category,
        start_date=start_date,
        end_date=end_date,
        half_day_type=half_day,
        calculated_days=leave_days,
        reason=reason,
        status=status,
        substitute_user_id=substitute_id,
        substitute_status=sub_status,
        is_station_leave=is_station,
        station_start_date=data.get("station_start_date"),
        station_end_date=data.get("station_end_date"),
        station_destination=data.get("station_destination", ""),
        station_contact_address=data.get("station_contact_address", ""),
        station_emergency_phone=data.get("station_emergency_phone", ""),
    )

    if status == STATUS_APPROVED:
        # Deduct balance immediately for Director self-sanction
        bal_obj.availed_days += leave_days
        bal_obj.save()
    else:
        # Hold in pending balance
        bal_obj.pending_days += leave_days
        bal_obj.save()

    # Log initial transition
    ApplicationTransition.objects.create(
        application=app,
        from_status="none",
        to_status=status,
        actor_user_id=principal.user_id,
        remarks="Application submitted.",
    )

    # Workflow task
    if substitute_id and sub_status == "pending":
        WorkflowTask.objects.create(
            application=app,
            assigned_user_id=substitute_id,
            role="Substitute",
            task_type="substitute",
        )

    return app


@transaction.atomic
def withdraw_application(principal, application_id: int) -> LeaveApplication:
    """Withdraw a pending leave application immediately (Section 8)."""
    require(principal, "leave_elm.application.withdraw")
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)

    if app.user_id != principal.user_id:
        raise ValidationError("You can only withdraw your own applications.")

    from_status = app.status
    app.status = transition_withdraw(from_status)
    app.save()

    # Release pending balance
    bal = EmployeeLeaveBalance.objects.filter(
        user_id=app.user_id, year=app.start_date.year, leave_category=app.leave_category
    ).first()
    if bal and bal.pending_days >= app.calculated_days:
        bal.pending_days -= app.calculated_days
        bal.save()

    ApplicationTransition.objects.create(
        application=app,
        from_status=from_status,
        to_status=app.status,
        actor_user_id=principal.user_id,
        remarks="Withdrawn by applicant.",
    )

    WorkflowTask.objects.filter(application=app, status="pending").update(status="cancelled")
    return app


@transaction.atomic
def respond_substitute(principal, application_id: int, action: str, remarks: str = "") -> LeaveApplication:
    """Record substitute consent (Section 6)."""
    require(principal, "leave_elm.substitute.respond")
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)

    if app.substitute_user_id != principal.user_id:
        raise ValidationError("You are not the nominated substitute for this request.")

    from_status = app.status
    if action == "accept":
        app.substitute_status = SUBSTITUTE_ACCEPTED
        app.status = transition_substitute_response(from_status, SUBSTITUTE_ACCEPTED)
    elif action == "decline":
        app.substitute_status = SUBSTITUTE_DECLINED
        app.status = transition_substitute_response(from_status, SUBSTITUTE_DECLINED)
    else:
        raise ValidationError(f"Invalid substitute action: {action!r}.")

    app.substitute_remarks = remarks
    app.save()

    ApplicationTransition.objects.create(
        application=app,
        from_status=from_status,
        to_status=app.status,
        actor_user_id=principal.user_id,
        remarks=f"Substitute {action}ed: {remarks}",
    )

    WorkflowTask.objects.filter(
        application=app, assigned_user_id=principal.user_id, task_type="substitute"
    ).update(status="completed")
    return app


@transaction.atomic
def recommend_unit_head(
    principal, application_id: int, recommendation: str, remarks: str = ""
) -> LeaveApplication:
    """Record Unit Head recommendation or final decision (Section 7)."""
    require(principal, "leave_elm.application.review")
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)

    from_status = app.status
    next_status = transition_unit_head_decision(from_status, app.leave_category, recommendation)

    app.unit_head_user_id = principal.user_id
    app.unit_head_recommendation = recommendation
    app.unit_head_remarks = remarks
    app.status = next_status

    bal = EmployeeLeaveBalance.objects.filter(
        user_id=app.user_id, year=app.start_date.year, leave_category=app.leave_category
    ).first()

    if next_status == STATUS_APPROVED:
        app.final_decision = DECISION_APPROVED
        app.final_decision_date = timezone.now()
        if bal:
            bal.pending_days = max(Decimal("0.0"), bal.pending_days - app.calculated_days)
            bal.availed_days += app.calculated_days
            bal.save()
    elif next_status == STATUS_REJECTED:
        app.final_decision = DECISION_REJECTED
        app.final_decision_date = timezone.now()
        if bal:
            bal.pending_days = max(Decimal("0.0"), bal.pending_days - app.calculated_days)
            bal.save()

    app.save()

    ApplicationTransition.objects.create(
        application=app,
        from_status=from_status,
        to_status=next_status,
        actor_user_id=principal.user_id,
        remarks=f"Unit Head: {recommendation}. {remarks}",
    )
    return app


@transaction.atomic
def sanction_application(
    principal, application_id: int, decision: str, remarks: str = ""
) -> LeaveApplication:
    """Record final sanctioning authority decision (Section 7)."""
    require(principal, "leave_elm.application.approve")
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)

    from_status = app.status
    next_status = transition_higher_sanction(from_status, decision)

    app.sanctioning_authority_user_id = principal.user_id
    app.final_decision = decision
    app.final_decision_date = timezone.now()
    app.final_remarks = remarks
    app.status = next_status

    bal = EmployeeLeaveBalance.objects.filter(
        user_id=app.user_id, year=app.start_date.year, leave_category=app.leave_category
    ).first()

    if decision == DECISION_APPROVED:
        if bal:
            bal.pending_days = max(Decimal("0.0"), bal.pending_days - app.calculated_days)
            bal.availed_days += app.calculated_days
            bal.save()
    elif decision == DECISION_REJECTED:
        if bal:
            bal.pending_days = max(Decimal("0.0"), bal.pending_days - app.calculated_days)
            bal.save()

    app.save()

    ApplicationTransition.objects.create(
        application=app,
        from_status=from_status,
        to_status=next_status,
        actor_user_id=principal.user_id,
        remarks=f"Sanctioning authority: {decision}. {remarks}",
    )
    return app


@transaction.atomic
def request_cancellation(principal, application_id: int, reason: str) -> LeaveApplication:
    """Request pre-start cancellation for approved leave (Section 8)."""
    require(principal, "leave_elm.application.cancel")
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)

    if app.user_id != principal.user_id:
        raise ValidationError("You can only cancel your own approved leaves.")

    if date.today() >= app.start_date:
        raise ValidationError("Once leave has begun, pre-start cancellation no longer applies.")

    from_status = app.status
    app.status = transition_request_cancellation(from_status)
    app.cancellation_reason = reason
    app.save()

    ApplicationTransition.objects.create(
        application=app,
        from_status=from_status,
        to_status=app.status,
        actor_user_id=principal.user_id,
        remarks=f"Cancellation requested: {reason}",
    )
    return app


@transaction.atomic
def approve_cancellation(
    principal, application_id: int, decision: str, remarks: str = ""
) -> LeaveApplication:
    """Approve or reject cancellation request (Section 8)."""
    require(principal, "leave_elm.application.approve")
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)

    from_status = app.status
    next_status = transition_cancellation_decision(from_status, decision)
    app.status = next_status

    if decision == DECISION_APPROVED:
        # Restore deducted balance
        bal = EmployeeLeaveBalance.objects.filter(
            user_id=app.user_id, year=app.start_date.year, leave_category=app.leave_category
        ).first()
        if bal:
            bal.availed_days = max(Decimal("0.0"), bal.availed_days - app.calculated_days)
            bal.save()

    app.save()

    ApplicationTransition.objects.create(
        application=app,
        from_status=from_status,
        to_status=next_status,
        actor_user_id=principal.user_id,
        remarks=f"Cancellation {decision}: {remarks}",
    )
    return app


@transaction.atomic
def request_extension(principal, parent_id: int, data: dict) -> LeaveApplication:
    """Request extension for ongoing EL/COL/VL (Section 9)."""
    require(principal, "leave_elm.application.extend")
    parent = LeaveApplication.objects.get(pk=parent_id)

    if parent.user_id != principal.user_id:
        raise ValidationError("You can only extend your own ongoing leave.")

    if parent.leave_category not in ("EL", "COL", "VL"):
        raise ValidationError("Extension is supported only for ongoing EL, COL, or VL.")

    data["is_extension"] = True
    data["parent_application_id"] = parent.pk
    data["leave_category"] = parent.leave_category
    return submit_application(principal, data)


@transaction.atomic
def submit_resumption(
    principal, application_id: int, actual_date: date, remarks: str = ""
) -> LeaveApplication:
    """Submit return to duty resumption details (Section 10)."""
    require(principal, "leave_elm.application.resume")
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)

    if app.user_id != principal.user_id:
        raise ValidationError("You can only submit resumption for your own leave.")

    if app.leave_category not in ("EL", "COL", "VL"):
        raise ValidationError("Resumption is supported only for EL, COL, and VL.")

    app.resumption_date = actual_date
    app.resumption_status = "pending"
    app.resumption_remarks = remarks
    app.save()

    ApplicationTransition.objects.create(
        application=app,
        from_status=app.status,
        to_status=app.status,
        actor_user_id=principal.user_id,
        remarks=f"Resumption reported on {actual_date}. {remarks}",
    )
    return app


@transaction.atomic
def review_resumption(
    principal, application_id: int, decision: str, remarks: str = ""
) -> LeaveApplication:
    """Review resumption and adjust balance for early/late return (Section 10)."""
    require(principal, "leave_elm.application.approve")
    app = LeaveApplication.objects.select_for_update().get(pk=application_id)

    from_status = app.status
    app.status = transition_resumption(from_status)
    app.resumption_status = decision

    if decision == DECISION_APPROVED and app.resumption_date:
        # Check early or late return
        diff_days = (app.resumption_date - app.end_date).days
        bal = EmployeeLeaveBalance.objects.filter(
            user_id=app.user_id, year=app.start_date.year, leave_category=app.leave_category
        ).first()

        if diff_days != 0 and bal:
            # early return: diff_days < 0 -> restore unused days
            # late return: diff_days > 0 -> deduct extra days
            bal.availed_days += Decimal(str(diff_days))
            bal.save()

    app.save()

    ApplicationTransition.objects.create(
        application=app,
        from_status=from_status,
        to_status=app.status,
        actor_user_id=principal.user_id,
        remarks=f"Resumption reviewed: {decision}. {remarks}",
    )
    return app
