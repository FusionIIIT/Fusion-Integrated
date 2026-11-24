"""Lab and role selectors."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.dept.models.labs import LabResource
from modules.dept.models.roles import DepartmentRoleAssignment


def list_lab_resources(department_code: str) -> QuerySet[LabResource]:
    return LabResource.objects.filter(department_id=department_code).order_by("lab_name")


def list_role_assignments(
    department_code: str,
    active_only: bool = False,
) -> QuerySet[DepartmentRoleAssignment]:
    qs = DepartmentRoleAssignment.objects.filter(department_id=department_code)
    if active_only:
        qs = qs.filter(status="ACTIVE")
    return qs.order_by("-start_date")
