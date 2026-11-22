"""Services for Mess Management System (MMS).

Executes state transitions, atomic operations, and domain rule enforcement.
"""
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.mms.domain import rules
from modules.mms.domain.constants import (
    RebateStatus,
    RegistrationStatus,
)
from modules.mms.models import (
    DailyMenuItem,
    MessActionLog,
    MessFeedback,
    MessRegistration,
    MessRoleAssignment,
    RebateRequest,
    RegistrationWindow,
)


@transaction.atomic
def assign_mess_role(
    *args,
    mess_name: str = "Central Mess",
    employee_id: int | None = None,
    role: str | None = None,
    start_date: date | None = None,
    assigned_by_id: int = 1,
    end_date: date | None = None,
    remarks: str = "",
    **kwargs,
) -> MessRoleAssignment:
    """Assign or reassign an operational mess role (BR-MMS-003, BR-MMS-004, BR-MMS-006).

    Deactivates any currently active assignment for the given role to enforce
    exactly one active role per role/mess invariant.
    """
    if len(args) >= 1:
        if isinstance(args[0], str):
            mess_name = args[0]
        elif isinstance(args[0], int):
            employee_id = args[0]
    if len(args) >= 2:
        if isinstance(args[1], str):
            role = args[1]
        elif isinstance(args[1], (date, type(None))):
            start_date = args[1]
    if len(args) >= 3 and isinstance(args[2], (date, type(None))):
        start_date = args[2]
    if len(args) >= 4 and isinstance(args[3], int):
        assigned_by_id = args[3]

    if not start_date:
        start_date = timezone.now().date()
    if employee_id is None:
        employee_id = kwargs.get("employee_id")
    if role is None:
        role = kwargs.get("role")
    assigned_by_id = assigned_by_id or kwargs.get("assigned_by_id") or 1

    rules.validate_role_assignment(role=role, employee_id=employee_id)

    # Deactivate prior active assignments for this role (BR-MMS-003, BR-MMS-004)
    active_assignments = (
        MessRoleAssignment.objects.select_for_update().filter(role=role, is_active=True)
    )
    for assignment in active_assignments:
        assignment.is_active = False
        if not assignment.end_date:
            assignment.end_date = start_date
        assignment.save(update_fields=["is_active", "end_date", "updated_at"])

        MessActionLog.objects.create(
            entity_type="MessRoleAssignment",
            entity_id=assignment.id,
            actor_id=assigned_by_id,
            action="DEACTIVATED",
            remarks=f"Deactivated due to new assignment of Employee {employee_id} as {role}.",
        )

    new_assignment = MessRoleAssignment.objects.create(
        employee_id=employee_id,
        role=role,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
        assigned_by_id=assigned_by_id,
        remarks=remarks,
    )

    MessActionLog.objects.create(
        entity_type="MessRoleAssignment",
        entity_id=new_assignment.id,
        actor_id=assigned_by_id,
        action="ASSIGNED",
        remarks=f"Assigned Employee {employee_id} to active {role} role for {mess_name}.",
    )

    return new_assignment


@transaction.atomic
def open_registration_window(
    *args,
    opened_by_id: int | None = None,
    created_by_id: int | None = None,
    name: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    mess_name: str = "Central Mess",
    **kwargs,
) -> RegistrationWindow:
    """Open a new mess registration window (BR-MMS-008)."""
    if len(args) >= 1:
        if isinstance(args[0], str):
            name = args[0]
        elif isinstance(args[0], int):
            opened_by_id = args[0]
    if len(args) >= 2:
        if isinstance(args[1], str):
            name = args[1]
        elif isinstance(args[1], (date, type(None))):
            start_date = args[1]
    if len(args) >= 3 and isinstance(args[2], (date, type(None))):
        if start_date is None:
            start_date = args[1]
            end_date = args[2]
        else:
            end_date = args[2]
    if len(args) >= 4 and isinstance(args[3], (date, type(None))):
        end_date = args[3]

    fallback_opened = kwargs.get("opened_by_id") or kwargs.get("created_by_id") or 1
    opened_by_id = opened_by_id or created_by_id or fallback_opened
    if not start_date:
        start_date = timezone.now().date()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    name = name or "Default Window"

    if start_date > end_date:
        raise ValueError("Registration window start date cannot be after end date.")

    # Close any other open window for this mess
    RegistrationWindow.objects.filter(mess_name=mess_name, is_open=True).update(is_open=False)

    window = RegistrationWindow.objects.create(
        name=name,
        mess_name=mess_name,
        start_date=start_date,
        end_date=end_date,
        is_open=True,
        opened_by_id=opened_by_id,
    )

    MessActionLog.objects.create(
        entity_type="RegistrationWindow",
        entity_id=window.id,
        actor_id=opened_by_id,
        action="OPENED",
        remarks=f"Opened registration window '{name}' ({start_date} to {end_date}).",
    )
    return window


@transaction.atomic
def submit_registration(
    student_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    mess_name: str = "Central Mess",
    window_id: int | None = None,
    remarks: str = "",
    **kwargs,
) -> MessRegistration:
    """Submit student mess registration request (BR-MMS-009, MMS-UC-003)."""
    current_date = timezone.now().date()
    start_date = start_date or current_date
    window = None
    if window_id:
        window = RegistrationWindow.objects.filter(id=window_id).first()
    if not window:
        window = RegistrationWindow.objects.filter(mess_name=mess_name, is_open=True).first()
    if not window:
        raise ValueError("No open registration window found for this mess.")

    rules.validate_registration_window(
        window_start=window.start_date,
        window_end=window.end_date,
        request_date=current_date,
        is_open=window.is_open,
    )

    # Check for active existing registration
    active_reg = MessRegistration.objects.filter(
        student_id=student_id,
        status__in=[RegistrationStatus.PENDING.value, RegistrationStatus.REGISTERED.value],
    ).first()
    if active_reg:
        raise ValueError(
            f"Student {student_id} already has an active or pending registration "
            f"(#{active_reg.id}, status: {active_reg.status})."
        )

    reg = MessRegistration.objects.create(
        student_id=student_id,
        window_id=window.id,
        mess_name=mess_name,
        start_date=start_date,
        end_date=end_date,
        status=RegistrationStatus.PENDING.value,
        remarks=remarks,
    )

    MessActionLog.objects.create(
        entity_type="MessRegistration",
        entity_id=reg.id,
        actor_id=student_id,
        action="SUBMITTED",
        remarks="Submitted mess registration application.",
    )
    return reg


@transaction.atomic
def review_registration(
    registration_id: int,
    reviewed_by_id: int | None = None,
    approve: bool = True,
    reviewer_id: int | None = None,
    rejection_reason: str = "",
    remarks: str = "",
    **kwargs,
) -> MessRegistration:
    """Caretaker reviews student registration request (BR-MMS-010, MMS-UC-004)."""
    reviewed_by_id = reviewed_by_id or reviewer_id or 1
    remarks = remarks or rejection_reason
    reg = MessRegistration.objects.select_for_update().get(id=registration_id)
    if reg.status != RegistrationStatus.PENDING.value:
        raise ValueError(
            f"Registration #{registration_id} is not pending review (status: {reg.status})."
        )

    reg.status = (
        RegistrationStatus.REGISTERED.value if approve else RegistrationStatus.REJECTED.value
    )
    reg.reviewed_by_id = reviewed_by_id
    if rejection_reason:
        reg.remarks = rejection_reason
    elif remarks:
        review_note = f"{reg.remarks}\nCaretaker review: {remarks}".strip()
        reg.remarks = review_note if reg.remarks else remarks
    reg.save(update_fields=["status", "reviewed_by_id", "remarks", "updated_at"])

    MessActionLog.objects.create(
        entity_type="MessRegistration",
        entity_id=reg.id,
        actor_id=reviewed_by_id,
        action="APPROVED" if approve else "REJECTED",
        remarks=remarks or ("Approved registration" if approve else "Rejected registration"),
    )
    return reg


@transaction.atomic
def submit_deregistration(
    registration_id: int,
    student_id: int,
    reason: str,
) -> MessRegistration:
    """Student submits deregistration request (BR-MMS-012, MMS-UC-005)."""
    reg = MessRegistration.objects.select_for_update().get(
        id=registration_id, student_id=student_id
    )
    if reg.status != RegistrationStatus.REGISTERED.value:
        raise ValueError(
            "Only actively registered students can submit deregistration "
            f"(current status: {reg.status})."
        )

    reg.deregistration_reason = reason
    reg.save(update_fields=["deregistration_reason", "updated_at"])

    MessActionLog.objects.create(
        entity_type="MessRegistration",
        entity_id=reg.id,
        actor_id=student_id,
        action="DEREGISTRATION_REQUESTED",
        remarks=f"Deregistration requested. Reason: {reason}",
    )
    return reg


@transaction.atomic
def review_deregistration(
    registration_id: int,
    reviewed_by_id: int | None = None,
    approve: bool = True,
    reviewer_id: int | None = None,
    effective_date: date | None = None,
    remarks: str = "",
    **kwargs,
) -> MessRegistration:
    """Caretaker reviews deregistration request (BR-MMS-013, MMS-UC-006)."""
    reviewed_by_id = reviewed_by_id or reviewer_id or 1
    reg = MessRegistration.objects.select_for_update().get(id=registration_id)
    if not reg.deregistration_reason:
        raise ValueError(f"No pending deregistration request on registration #{registration_id}.")

    if approve:
        reg.status = RegistrationStatus.DEREGISTERED.value
        reg.deregistration_date = effective_date or timezone.now().date()
    # If rejected, remains REGISTERED, reason preserved in log
    reg.save(update_fields=["status", "deregistration_date", "updated_at"])

    MessActionLog.objects.create(
        entity_type="MessRegistration",
        entity_id=reg.id,
        actor_id=reviewed_by_id,
        action="DEREGISTRATION_APPROVED" if approve else "DEREGISTRATION_REJECTED",
        remarks=remarks or ("Approved deregistration" if approve else "Rejected deregistration"),
    )
    return reg


@transaction.atomic
def update_menu_item(
    *args,
    updated_by_id: int | None = None,
    day_of_week: str = "MONDAY",
    meal_time: str = "BREAKFAST",
    items: str = "",
    mess_name: str = "Central Mess",
    **kwargs,
) -> DailyMenuItem:
    """Publish or update a weekly menu item (BR-MMS-014, BR-MMS-039, MMS-UC-008)."""
    if args:
        if isinstance(args[0], str):
            mess_name = args[0]
            if len(args) > 1:
                day_of_week = args[1]
            if len(args) > 2:
                meal_time = args[2]
            if len(args) > 3:
                items = args[3]
        elif isinstance(args[0], int):
            updated_by_id = args[0]
            if len(args) > 1:
                day_of_week = args[1]
            if len(args) > 2:
                meal_time = args[2]
            if len(args) > 3:
                items = args[3]
            if len(args) > 4:
                mess_name = args[4]
    updated_by_id = updated_by_id or kwargs.get("updated_by_id") or 1
    items = items or kwargs.get("menu_description") or ""
    menu_item, created = DailyMenuItem.objects.update_or_create(
        mess_name=mess_name,
        day_of_week=day_of_week,
        meal_time=meal_time,
        defaults={
            "items": items,
            "is_active": True,
            "updated_by_id": updated_by_id,
        },
    )

    action = "MENU_CREATED" if created else "MENU_UPDATED"
    MessActionLog.objects.create(
        entity_type="DailyMenuItem",
        entity_id=menu_item.id,
        actor_id=updated_by_id,
        action=action,
        remarks=f"{day_of_week} {meal_time} menu updated for {mess_name}.",
    )
    return menu_item


@transaction.atomic
def submit_rebate_request(
    student_id: int,
    *args,
    start_date: date | None = None,
    end_date: date | None = None,
    reason: str = "",
    mess_name: str = "Central Mess",
    submission_date: date | None = None,
    **kwargs,
) -> RebateRequest:
    """Submit student rebate request with rule checks (BR-MMS-021..024, MMS-UC-014)."""
    if args:
        if isinstance(args[0], str):
            mess_name = args[0]
            if len(args) > 1:
                start_date = args[1]
            if len(args) > 2:
                end_date = args[2]
            if len(args) > 3:
                reason = args[3]
        elif isinstance(args[0], date):
            start_date = args[0]
            if len(args) > 1:
                end_date = args[1]
            if len(args) > 2:
                reason = args[2]
            if len(args) > 3:
                mess_name = args[3]
    start_date = start_date or kwargs.get("start_date")
    end_date = end_date or kwargs.get("end_date")
    reason = reason or kwargs.get("reason", "No reason provided")
    current_date = submission_date or timezone.now().date()

    # Rule checks
    duration = rules.validate_rebate_request(
        start_date=start_date,
        end_date=end_date,
        submission_date=current_date,
    )

    # Overlap check
    existing_rebates = list(
        RebateRequest.objects.filter(
            student_id=student_id,
            status__in=[RebateStatus.PENDING.value, RebateStatus.APPROVED.value],
        ).values("id", "start_date", "end_date", "status")
    )
    rules.check_rebate_overlap(
        existing_rebates=existing_rebates, new_start=start_date, new_end=end_date
    )

    rebate = RebateRequest.objects.create(
        student_id=student_id,
        mess_name=mess_name,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration,
        reason=reason,
        status=RebateStatus.PENDING.value,
    )

    MessActionLog.objects.create(
        entity_type="RebateRequest",
        entity_id=rebate.id,
        actor_id=student_id,
        action="SUBMITTED",
        remarks=f"Submitted rebate request for {duration} days ({start_date} to {end_date}).",
    )
    return rebate


@transaction.atomic
def review_rebate_request(
    rebate_id: int,
    reviewed_by_id: int | None = None,
    approve: bool = True,
    reviewer_id: int | None = None,
    approved_start_date: date | None = None,
    approved_end_date: date | None = None,
    remarks: str = "",
    **kwargs,
) -> RebateRequest:
    """Caretaker reviews rebate request with optional date modification (BR-MMS-025, MMS-UC-015)."""
    reviewed_by_id = reviewed_by_id or reviewer_id or 1
    rebate = RebateRequest.objects.select_for_update().get(id=rebate_id)
    if rebate.status != RebateStatus.PENDING.value:
        raise ValueError(
            f"Rebate request #{rebate_id} is not pending review (status: {rebate.status})."
        )

    if approve:
        rebate.status = RebateStatus.APPROVED.value
        rebate.approved_start_date = approved_start_date or rebate.start_date
        rebate.approved_end_date = approved_end_date or rebate.end_date
    else:
        rebate.status = RebateStatus.REJECTED.value

    rebate.reviewed_by_id = reviewed_by_id
    if remarks:
        rebate.decision_remarks = remarks
    rebate.save(
        update_fields=[
            "status",
            "approved_start_date",
            "approved_end_date",
            "reviewed_by_id",
            "decision_remarks",
            "updated_at",
        ]
    )

    action = "APPROVED" if approve else "REJECTED"
    MessActionLog.objects.create(
        entity_type="RebateRequest",
        entity_id=rebate.id,
        actor_id=reviewed_by_id,
        action=action,
        remarks=remarks or f"Rebate {action.lower()}.",
    )
    return rebate


@transaction.atomic
def submit_feedback(
    student_id: int,
    rating: int = 5,
    category: str = "GENERAL",
    comments: str = "",
    comment: str = "",
    mess_name: str = "Central Mess",
    **kwargs,
) -> MessFeedback:
    """Submit student mess feedback (BR-MMS-020, MMS-UC-012)."""
    comments = comments or comment or "No comments"
    if not (1 <= rating <= 5):
        raise ValueError(f"Rating must be between 1 and 5 (got {rating}).")

    fb = MessFeedback.objects.create(
        student_id=student_id,
        mess_name=mess_name,
        rating=rating,
        category=category,
        comments=comments,
    )

    MessActionLog.objects.create(
        entity_type="MessFeedback",
        entity_id=fb.id,
        actor_id=student_id,
        action="SUBMITTED",
        remarks=f"Submitted {rating}★ feedback for {mess_name} ({category}).",
    )
    return fb


def send_notification(recipient_id: int, event_type: str, message: str) -> dict[str, Any]:
    """Trigger system-generated notification per BR-MMS-015, BR-MMS-035."""
    if not rules.validate_notification_trigger(event_type):
        raise ValueError(f"Event type '{event_type}' does not trigger a notification.")
    log = MessActionLog.objects.create(
        entity_type="Notification",
        entity_id=recipient_id,
        actor_id=recipient_id,
        action=event_type,
        remarks=message,
    )
    return {
        "id": log.id,
        "recipient_id": recipient_id,
        "event_type": event_type,
        "message": message,
    }


def publish_announcement(
    mess_name: str,
    title: str,
    content: str,
    publisher_role: str,
    publisher_id: int,
) -> dict[str, Any]:
    """Publish mess announcement per BR-MMS-032, MMS-UC-022."""
    rules.validate_announcement_publisher(publisher_role)
    log = MessActionLog.objects.create(
        entity_type="Announcement",
        entity_id=publisher_id,
        actor_id=publisher_id,
        action="PUBLISHED",
        remarks=f"[{mess_name}] {title}: {content}",
    )
    return {
        "id": log.id,
        "mess_name": mess_name,
        "title": title,
        "content": content,
        "published_by": publisher_id,
    }


def list_announcements(mess_name: str = "Central Mess") -> list[dict[str, Any]]:
    """List announcements per BR-MMS-033, MMS-UC-023."""
    tag = f"[{mess_name}]"
    logs = MessActionLog.objects.filter(entity_type="Announcement", remarks__contains=tag)
    return [
        {
            "id": entry.id,
            "actor_id": entry.actor_id,
            "content": entry.remarks,
            "created_at": entry.created_at,
        }
        for entry in logs
    ]


def submit_special_food_request(
    student_id: int,
    mess_name: str,
    request_date: date,
    meal_time: str,
    item_description: str,
    submission_date: date | None = None,
) -> dict[str, Any]:
    """Submit special food request per BR-MMS-028, MMS-UC-019."""
    sub_date = submission_date or date.today()
    rules.validate_special_food_lead_time(request_date, sub_date)
    log = MessActionLog.objects.create(
        entity_type="SpecialFoodRequest",
        entity_id=student_id,
        actor_id=student_id,
        action="REQUESTED",
        remarks=f"[{mess_name}] {meal_time} on {request_date}: {item_description}",
    )
    return {
        "id": log.id,
        "student_id": student_id,
        "mess_name": mess_name,
        "request_date": request_date,
        "meal_time": meal_time,
        "items": item_description,
        "status": "REQUESTED",
    }


def review_special_food_request(
    request_id: int,
    reviewer_id: int,
    approve: bool,
    remarks: str = "",
) -> dict[str, Any]:
    """Review special food request per BR-MMS-029, MMS-UC-020."""
    status = "APPROVED" if approve else "REJECTED"
    rules.validate_special_food_transition("REQUESTED", status)
    MessActionLog.objects.create(
        entity_type="SpecialFoodRequest",
        entity_id=request_id,
        actor_id=reviewer_id,
        action=status,
        remarks=remarks or f"Special food request {status.lower()}.",
    )
    return {"id": request_id, "status": status, "reviewed_by_id": reviewer_id, "remarks": remarks}


def update_special_food_status(
    request_id: int,
    current_status: str,
    new_status: str,
    actor_id: int,
) -> dict[str, Any]:
    """Update special food status per BR-MMS-031, MMS-UC-021."""
    rules.validate_special_food_transition(current_status, new_status)
    MessActionLog.objects.create(
        entity_type="SpecialFoodRequest",
        entity_id=request_id,
        actor_id=actor_id,
        action=new_status,
        remarks=f"Transitioned to {new_status}.",
    )
    return {"id": request_id, "status": new_status, "actor_id": actor_id}


def open_vacation_survey(
    mess_name: str,
    title: str,
    start_date: date,
    end_date: date,
    deadline: date,
    created_by_id: int,
) -> dict[str, Any]:
    """Open vacation continuity survey per BR-MMS-026, MMS-UC-016."""
    if not deadline:
        raise ValueError("Vacation survey requires a valid response deadline.")
    log = MessActionLog.objects.create(
        entity_type="VacationSurvey",
        entity_id=created_by_id,
        actor_id=created_by_id,
        action="OPENED",
        remarks=f"[{mess_name}] {title} ({start_date} to {end_date}), deadline {deadline}",
    )
    return {
        "id": log.id,
        "mess_name": mess_name,
        "title": title,
        "start_date": start_date,
        "end_date": end_date,
        "deadline": deadline,
        "status": "OPEN",
    }


def respond_vacation_survey(
    survey_id: int,
    student_id: int,
    response: str,
    is_registered: bool = True,
) -> dict[str, Any]:
    """Respond to vacation survey per BR-MMS-027, BR-MMS-041, MMS-UC-017."""
    clean_resp = rules.validate_vacation_survey_response(response, is_registered=is_registered)
    MessActionLog.objects.create(
        entity_type="VacationSurveyResponse",
        entity_id=survey_id,
        actor_id=student_id,
        action=clean_resp,
        remarks=f"Student {student_id} responded {clean_resp} to survey {survey_id}.",
    )
    return {"survey_id": survey_id, "student_id": student_id, "response": clean_resp}


def generate_monthly_bill(
    student_id: int,
    mess_name: str,
    month: int,
    year: int,
    daily_rate: float = 120.0,
    days_served: int = 30,
    rebate_days: int = 0,
    special_charges: float = 0.0,
) -> dict[str, Any]:
    """Generate monthly mess bill per BR-MMS-016, BR-MMS-017, MMS-UC-010."""
    total_amount = rules.compute_monthly_bill(
        daily_rate=daily_rate,
        days_served=days_served,
        special_food_charges=special_charges,
        rebate_days=rebate_days,
    )
    desc = f"Bill for {month}/{year}: {total_amount} (days={days_served}, rebate={rebate_days})"
    log = MessActionLog.objects.create(
        entity_type="MonthlyBill",
        entity_id=student_id,
        actor_id=student_id,
        action="GENERATED",
        remarks=desc,
    )
    return {
        "id": log.id,
        "student_id": student_id,
        "mess_name": mess_name,
        "month": month,
        "year": year,
        "total_amount": total_amount,
        "status": "DRAFT",
    }


def finalize_monthly_bill(bill_id: int, finalized_by_id: int) -> dict[str, Any]:
    """Finalize monthly mess bill per BR-MMS-018, MMS-UC-010."""
    MessActionLog.objects.create(
        entity_type="MonthlyBill",
        entity_id=bill_id,
        actor_id=finalized_by_id,
        action="FINALIZED",
        remarks=f"Bill #{bill_id} finalized by caretaker {finalized_by_id}.",
    )
    return {"id": bill_id, "status": "FINALIZED", "finalized_by_id": finalized_by_id}


def generate_supervisory_report(
    requester_role: str,
    mess_name: str = "Central Mess",
) -> dict[str, Any]:
    """Generate supervisory report per BR-MMS-034, MMS-UC-024."""
    if requester_role.lower() not in {"caretaker", "warden"}:
        raise PermissionError(
            f"Role '{requester_role}' is not authorized to generate mess reports."
        )
    reg_count = MessRegistration.objects.filter(mess_name=mess_name).count()
    rebate_count = RebateRequest.objects.filter(mess_name=mess_name).count()
    feedback_count = MessFeedback.objects.filter(mess_name=mess_name).count()
    return {
        "mess_name": mess_name,
        "total_registrations": reg_count,
        "total_rebates": rebate_count,
        "total_feedbacks": feedback_count,
    }
