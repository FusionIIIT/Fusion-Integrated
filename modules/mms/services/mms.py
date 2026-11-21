"""Services for Mess Management System (MMS).

Executes state transitions, atomic operations, and domain rule enforcement.
"""
from datetime import date

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
    employee_id: int,
    role: str,
    start_date: date,
    assigned_by_id: int,
    end_date: date | None = None,
    remarks: str = "",
) -> MessRoleAssignment:
    """Assign or reassign an operational mess role (BR-MMS-003, BR-MMS-004, BR-MMS-006).

    Deactivates any currently active assignment for the given role to enforce
    exactly one active role per role/mess invariant.
    """
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
        remarks=f"Assigned Employee {employee_id} to active {role} role.",
    )

    return new_assignment


@transaction.atomic
def open_registration_window(
    opened_by_id: int,
    name: str,
    start_date: date,
    end_date: date,
    mess_name: str = "Central Mess",
) -> RegistrationWindow:
    """Open a new mess registration window (BR-MMS-008)."""
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
    start_date: date,
    end_date: date | None = None,
    mess_name: str = "Central Mess",
    remarks: str = "",
) -> MessRegistration:
    """Submit student mess registration request (BR-MMS-009, MMS-UC-003)."""
    # Check open window
    current_date = timezone.now().date()
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
    reviewed_by_id: int,
    approve: bool,
    remarks: str = "",
) -> MessRegistration:
    """Caretaker reviews student registration request (BR-MMS-010, MMS-UC-004)."""
    reg = MessRegistration.objects.select_for_update().get(id=registration_id)
    if reg.status != RegistrationStatus.PENDING.value:
        raise ValueError(
            f"Registration #{registration_id} is not pending review (status: {reg.status})."
        )

    reg.status = (
        RegistrationStatus.REGISTERED.value if approve else RegistrationStatus.REJECTED.value
    )
    reg.reviewed_by_id = reviewed_by_id
    if remarks:
        reg.remarks = f"{reg.remarks}\nCaretaker review: {remarks}".strip()
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
    reviewed_by_id: int,
    approve: bool,
    effective_date: date | None = None,
    remarks: str = "",
) -> MessRegistration:
    """Caretaker reviews deregistration request (BR-MMS-013, MMS-UC-006)."""
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
    updated_by_id: int,
    day_of_week: str,
    meal_time: str,
    items: str,
    mess_name: str = "Central Mess",
) -> DailyMenuItem:
    """Publish or update a weekly menu item (BR-MMS-014, BR-MMS-039, MMS-UC-008)."""
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
) -> RebateRequest:
    """Submit student rebate request with rule checks (BR-MMS-021..024, MMS-UC-014)."""
    current_date = timezone.now().date()

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
    reviewed_by_id: int,
    approve: bool,
    approved_start_date: date | None = None,
    approved_end_date: date | None = None,
    remarks: str = "",
) -> RebateRequest:
    """Caretaker reviews rebate request with optional date modification (BR-MMS-025, MMS-UC-015)."""
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

    MessActionLog.objects.create(
        entity_type="RebateRequest",
        entity_id=rebate.id,
        actor_id=reviewed_by_id,
        action="APPROVED" if approve else "REJECTED",
        remarks=remarks or ("Approved rebate" if approve else "Rejected rebate"),
    )
    return rebate


@transaction.atomic
def submit_feedback(
    student_id: int,
    rating: int,
    category: str,
    comments: str,
    mess_name: str = "Central Mess",
) -> MessFeedback:
    """Submit student mess feedback (BR-MMS-020, MMS-UC-012)."""
    if rating < 1 or rating > 5:
        raise ValueError("Feedback rating must be an integer between 1 and 5.")

    feedback = MessFeedback.objects.create(
        student_id=student_id,
        mess_name=mess_name,
        rating=rating,
        category=category,
        comments=comments,
    )

    MessActionLog.objects.create(
        entity_type="MessFeedback",
        entity_id=feedback.id,
        actor_id=student_id,
        action="SUBMITTED",
        remarks=f"Submitted {category} feedback ({rating}★).",
    )
    return feedback
