"""Services for Mess Management System (MMS).

Executes state transitions, atomic operations, and domain rule enforcement.
"""
from datetime import date, timedelta

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

    opened_by_id = opened_by_id or created_by_id or kwargs.get("opened_by_id") or kwargs.get("created_by_id") or 1
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
        reg.remarks = f"{reg.remarks}\nCaretaker review: {remarks}".strip() if reg.remarks else remarks
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
    updated_by_id: int | None = None,
    day_of_week: str = "MONDAY",
    meal_time: str = "BREAKFAST",
    items: str = "",
    mess_name: str = "Central Mess",
    **kwargs,
) -> DailyMenuItem:
    """Publish or update a weekly menu item (BR-MMS-014, BR-MMS-039, MMS-UC-008)."""
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
    start_date: date,
    end_date: date,
    reason: str,
    mess_name: str = "Central Mess",
    submission_date: date | None = None,
    **kwargs,
) -> RebateRequest:
    """Submit student rebate request with rule checks (BR-MMS-021..024, MMS-UC-014)."""
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
