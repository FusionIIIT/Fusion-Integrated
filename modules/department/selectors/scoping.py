"""Role scope, decided in one place.

Every list and detail view starts from a queryset built here. Ownership is
enforced by narrowing the queryset, never by fetching a row and then checking
it — so a row you may not see is a 404, not a 403. A 403 would confirm it
exists, which for department data is itself a disclosure.
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.department.domain import roles as role_domain
from modules.department.models import Department
from modules.department.selectors import role_assignments
from modules.directory import contracts as directory

# Permission codes.
P_VIEW_DEPARTMENTS = "department.department.view"


def member_department_codes(actor) -> list[str]:
    """Returns department codes the actor is a member of."""
    user_data = directory.get_users([actor.user_id])
    if not user_data:
        return []

    user = user_data.get(actor.user_id)
    if not user:
        return []

    role_kind_val = role_domain.role_kind(actor.active_role)

    if user.kind == "student" and role_kind_val == "student":
        # Students match by discipline
        discipline = user.discipline
        if not discipline:
            return []
        # Case-insensitive match against Department.code or Department.name
        return list(Department.objects.filter(
            Q(code__iexact=discipline) | Q(name__iexact=discipline),
            is_active=True
        ).values_list("code", flat=True))
    if user.kind == "faculty" and role_kind_val in ("faculty", "institute_admin", "hod", "dept_admin"):
        # Faculty match by department
        department = user.department
        if not department:
            return []
        # Case-insensitive match against Department.code or Department.name
        return list(Department.objects.filter(
            Q(code__iexact=department) | Q(name__iexact=department),
            is_active=True
        ).values_list("code", flat=True))
    return []


def visible_departments(actor) -> QuerySet[Department]:
    """Returns active departments the actor is a member of or sees all."""
    role_kind_val = role_domain.role_kind(actor.active_role)

    if role_kind_val == "institute_admin":
        return Department.objects.filter(is_active=True)

    if role_kind_val in ("hod", "dept_admin"):
        # HOD/Dept_Admin sees only departments they currently hold the role for
        dept_ids = role_assignments.held_department_ids(actor.user_id, role_kind_val, now=None)
        return Department.objects.filter(
            is_active=True,
            id__in=dept_ids
        )

    codes = member_department_codes(actor)
    if not codes:
        return Department.objects.none()

    # Filter by codes found via membership
    return Department.objects.filter(
        is_active=True,
        code__in=codes
    )


def department_ids_for_role(actor, kind) -> set[int]:
    """Returns department IDs where the actor currently holds the specified role kind."""
    role_kind_val = role_domain.role_kind(actor.active_role)
    if role_kind_val != kind:
        return set()

    # Use the selector to find department IDs where the actor holds this role
    dept_ids = role_assignments.held_department_ids(actor.user_id, kind, now=None)
    return set(dept_ids)
