"""Business services for the Mess Management System (MMS)."""

from datetime import date
from typing import Optional
from django.db import transaction
from modules.mms.domain import rules
from modules.mms.domain.constants import RebateStatus, RegistrationStatus
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
    mess_name: str,
    role: str,
    employee_id: int,
    assigned_by_id: int,
) -> MessRoleAssignment:
    rules.validate_role_assignment(role, employee_id)

    # Deactivate existing role of same type for this mess (BR-MMS-003, BR-MMS-004)
    MessRoleAssignment.objects.filter(
        mess_name=mess_name,
        role=role,
        is_active=True,
    ).update(is_active=False)

    assignment = MessRoleAssignment.objects.create(
        mess_name=mess_name,
        role=role,
        employee_id=employee_id,
        is_active=True,
    )

    MessActionLog.objects.create(
        action_by_id=assigned_by_id,
        action_type="ASSIGN_ROLE",
        target_id=assignment.id,
        details=f"Assigned {role} to employee {employee_id} for {mess_name}",
    )
    return assignment


@transaction.atomic
def open_registration_window(
    semester: str,
    start_date: date,
    end_date: date,
    created_by_id: int,
) -> RegistrationWindow:
    if start_date > end_date:
        raise ValueError("Window start date cannot be after end date.")

    window = RegistrationWindow.objects.create(
        semester=semester,
        start_date=start_date,
        end_date=end_date,
        is_open=True,
        created_by_id=created_by_id,
    )

    MessActionLog.objects.create(
        action_by_id=created_by_id,
        action_type="OPEN_WINDOW",
        target_id=window.id,
        details=f"Opened window for {semester} ({start_date} to {end_date})",
    )
    return window


@transaction.atomic
def submit_registration(
    student_id: int,
    mess_name: str,
    window_id: int,
) -> MessRegistration:
    window = RegistrationWindow.objects.get(id=window_id)
    today = date.today()

    rules.validate_registration_window(
        window_start=window.start_date,
        window_end=window.end_date,
        request_date=today,
        is_open=window.is_open,
    )

    existing = MessRegistration.objects.filter(
        student_id=student_id,
        window=window,
        status__in=[RegistrationStatus.PENDING.value, RegistrationStatus.REGISTERED.value],
    ).first()
    if existing:
        raise ValueError("Student already has an active or pending registration for this window.")

    reg = MessRegistration.objects.create(
        student_id=student_id,
        mess_name=mess_name,
        window=window,
        status=RegistrationStatus.PENDING.value,
    )
    return reg


@transaction.atomic
def review_registration(
    registration_id: int,
    reviewer_id: int,
    approve: bool,
    rejection_reason: str = "",
) -> MessRegistration:
    reg = MessRegistration.objects.get(id=registration_id)
    if approve:
        reg.status = RegistrationStatus.REGISTERED.value
        reg.rejection_reason = ""
    else:
        reg.status = RegistrationStatus.REJECTED.value
        reg.rejection_reason = rejection_reason

    reg.reviewer_id = reviewer_id
    reg.save()

    MessActionLog.objects.create(
        action_by_id=reviewer_id,
        action_type="REVIEW_REGISTRATION",
        target_id=reg.id,
        details=f"Status changed to {reg.status}",
    )
    return reg


@transaction.atomic
def update_menu_item(
    mess_name: str,
    day_of_week: str,
    meal_time: str,
    menu_description: str,
    updated_by_id: int,
) -> DailyMenuItem:
    item, _ = DailyMenuItem.objects.update_or_create(
        mess_name=mess_name,
        day_of_week=day_of_week,
        meal_time=meal_time,
        defaults={
            "menu_description": menu_description,
            "last_updated_by_id": updated_by_id,
        },
    )
    return item


@transaction.atomic
def submit_rebate_request(
    student_id: int,
    mess_name: str,
    start_date: date,
    end_date: date,
    reason: str = "",
) -> RebateRequest:
    today = date.today()
    duration = rules.validate_rebate_request(start_date, end_date, submission_date=today)

    existing_rebates = list(
        RebateRequest.objects.filter(student_id=student_id).values(
            "id", "start_date", "end_date", "status"
        )
    )
    rules.check_rebate_overlap(existing_rebates, start_date, end_date)

    rebate = RebateRequest.objects.create(
        student_id=student_id,
        mess_name=mess_name,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration,
        reason=reason,
        status=RebateStatus.PENDING.value,
    )
    return rebate


@transaction.atomic
def review_rebate_request(
    rebate_id: int,
    reviewer_id: int,
    approve: bool,
    review_notes: str = "",
) -> RebateRequest:
    rebate = RebateRequest.objects.get(id=rebate_id)
    if approve:
        rebate.status = RebateStatus.APPROVED.value
    else:
        rebate.status = RebateStatus.REJECTED.value

    rebate.reviewer_id = reviewer_id
    rebate.review_notes = review_notes
    rebate.save()

    MessActionLog.objects.create(
        action_by_id=reviewer_id,
        action_type="REVIEW_REBATE",
        target_id=rebate.id,
        details=f"Rebate #{rebate.id} marked as {rebate.status}",
    )
    return rebate


@transaction.atomic
def submit_feedback(
    student_id: int,
    mess_name: str,
    category: str,
    comment: str,
) -> MessFeedback:
    feedback = MessFeedback.objects.create(
        student_id=student_id,
        mess_name=mess_name,
        category=category,
        comment=comment,
    )
    return feedback

