"""Controlled setup for leave policy, balances, and reporting scope."""

from django.db import transaction

from modules.leave.models import LeaveBalance, LeaveManagerAssignment, LeaveType


@transaction.atomic
def save_leave_type(*, values, leave_type_id=None):
    if leave_type_id is None:
        return LeaveType.objects.create(**values)
    leave_type = LeaveType.objects.select_for_update().filter(pk=leave_type_id).first()
    if leave_type is None:
        return None
    for field, value in values.items():
        setattr(leave_type, field, value)
    leave_type.save(update_fields=[*values, "updated_at"])
    return leave_type


@transaction.atomic
def set_balance(*, values):
    balance, _ = LeaveBalance.objects.update_or_create(
        user_id=values["user_id"], leave_type=values["leave_type"],
        year=values["year"], defaults={
            "allocated_days": values["allocated_days"],
            "carried_days": values["carried_days"],
        })
    return balance


@transaction.atomic
def assign_manager(*, manager_user_id, employee_user_id, assigned_by_user_id):
    assignment, created = LeaveManagerAssignment.objects.get_or_create(
        manager_user_id=manager_user_id, employee_user_id=employee_user_id,
        defaults={"assigned_by_user_id": assigned_by_user_id},
    )
    return assignment, created
