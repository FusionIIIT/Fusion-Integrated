"""Role selectors for Super Admin."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.superadmin.models import RoleAssignmentRecord, RoleHandoverRecord
from modules.superadmin.selectors.scoping import visible_roles


def list_roles(
    principal,
    *,
    user_id: int | None = None,
    role_name: str = "",
    status: str = "",
) -> QuerySet[RoleAssignmentRecord]:
    qs = visible_roles(principal)
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if role_name:
        qs = qs.filter(role_name__icontains=role_name)
    if status:
        qs = qs.filter(status=status.upper())
    return qs.order_by("-valid_from")


def get_role_by_id(principal, role_id: int) -> RoleAssignmentRecord | None:
    return visible_roles(principal).filter(pk=role_id).first()


def list_handovers(
    principal, *, role_assignment_id: int | None = None
) -> QuerySet[RoleHandoverRecord]:
    qs = RoleHandoverRecord.objects.all()
    if role_assignment_id is not None:
        qs = qs.filter(role_assignment_id=role_assignment_id)
    return qs.order_by("-effective_date")
