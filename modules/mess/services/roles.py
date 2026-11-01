from modules.mess.models import MessRoleAssignment, MessRole
from modules.mess.services._audit import record_transition, queue_notification
from django.db import transaction
from datetime import datetime

@transaction.atomic
def assign_role(actor_user_id, role, employee_user_id, starts_at, ends_at):
    # Load existing MessRoleAssignment rows of the same role
    existing_assignments = MessRoleAssignment.objects.filter(role=role)

    # Call can_assign from modules.mess.domain.roles_rules with a list of (role, starts_at, ends_at) tuples
    can_assign = MessRole.can_assign(role, starts_at, ends_at)

    if not can_assign:
        raise ValueError("Cannot assign role. There is already an active holder for this role.")

    # Create and return the row with assigned_by_user_id=actor_user_id
    assignment = MessRoleAssignment(role=role, assigned_by_user_id=actor_user_id, employee_user_id=employee_user_id, starts_at=starts_at, ends_at=ends_at)
    assignment.save()

    return assignment

def get_active_assignee(role, now):
    # Returns the employee_user_id of the active assignment for that role or None
    assignment = MessRoleAssignment.objects.filter(role=role, ends_at__gt=now).first()

    if assignment:
        return assignment.employee_user_id
    else:
        return None
