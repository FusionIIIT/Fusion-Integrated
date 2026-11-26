"""Service layer for managing department role assignments."""
import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.department.models import Department, DepartmentRoleAssignment
from modules.department.services.authz import require
from modules.directory import contracts as directory

ASSIGN = "department.role_assignment.assign"

@transaction.atomic
def record_assignment(*, actor, department_id, role, user_id, valid_from, valid_to):
    """Records a new department role assignment."""
    require(actor, ASSIGN)

    department = Department.objects.select_for_update().filter(pk=department_id).first()
    if not department:
        raise NotFoundError("No such department.")

    person = directory.get_users([user_id]).get(user_id)
    if person is None or person.kind not in ("faculty", "staff"):
        raise ConflictError("The user provided is not a faculty or staff employee.", code="not_an_employee")

    if valid_to <= valid_from:
        raise ConflictError("The end date must be after the start date.", code="bad_interval")

    now = timezone.now()
    if valid_from < now - datetime.timedelta(minutes=5):
        raise ConflictError("The start date cannot be more than 5 minutes in the past.", code="backdated")

    # Check for overlaps in the future
    overlaps_future = DepartmentRoleAssignment.objects.filter(
        department=department,
        role=role,
        valid_from__gte=valid_from
    ).exists()
    if overlaps_future:
        raise ConflictError("This assignment overlaps with an existing future assignment for this role in this department.", code="overlaps_future")

    # Handle overlaps in the past/present (clipping)
    # Find existing assignments that overlap and need to be truncated
    overlapping_assignments = DepartmentRoleAssignment.objects.filter(
        department=department,
        role=role,
        valid_from__lte=valid_from,
        valid_to__gt=valid_from
    ).select_for_update()

    for assignment in overlapping_assignments:
        if assignment.valid_to > valid_from:
            assignment.valid_to = valid_from
            assignment.save(update_fields=["valid_to", "updated_at"])

    # Create and return the new row
    new_assignment = DepartmentRoleAssignment.objects.create(
        department=department,
        role=role,
        user_id=user_id,
        valid_from=valid_from,
        valid_to=valid_to,
        assigned_by_user_id=actor.user_id
    )
    return new_assignment


def apply_due_transitions(*, now=None):
    """Applies transitions for role assignments that are currently active."""
    if now is None:
        now = timezone.now()

    count = DepartmentRoleAssignment.objects.filter(
        valid_from__lte=now,
        valid_to__gt=now,
        transition_applied_at__isnull=True
    ).update(transition_applied_at=now)

    return count
