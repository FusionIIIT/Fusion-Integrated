from django.utils import timezone

from modules.department.models.role_assignments import DepartmentRoleAssignment


def current_holder(department, role, now=None):
    """Returns the DepartmentRoleAssignment in effect for a given department and role."""
    if now is None:
        now = timezone.now()
    return DepartmentRoleAssignment.objects.filter(
        department=department,
        role=role,
        valid_from__lte=now,
        valid_to__gt=now
    ).first()


def headship_user_ids(department_ids, now=None):
    """Returns a list of user IDs of HOD assignments in effect for the given departments."""
    if now is None:
        now = timezone.now()
    return DepartmentRoleAssignment.objects.filter(
        department__in=department_ids,
        role='hod',
        valid_from__lte=now,
        valid_to__gt=now
    ).values_list('user_id', flat=True).distinct().order_by('user_id')


def held_department_ids(user_id, role, now=None):
    """Returns a set of department IDs where a user has an assignment in effect for a given role."""
    if now is None:
        now = timezone.now()
    return set(DepartmentRoleAssignment.objects.filter(
        user_id=user_id,
        role=role,
        valid_from__lte=now,
        valid_to__gt=now
    ).values_list('department_id', flat=True).distinct())
