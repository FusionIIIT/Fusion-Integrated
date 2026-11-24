"""Department metadata, authoritative headship, and official changes selectors."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from modules.dept.models.department import Department
from modules.dept.models.official_changes import OfficialDetailChangeRequest
from modules.dept.models.roles import DepartmentRoleAssignment


def get_department_with_headship(department_code: str) -> dict[str, Any] | None:
    dept = Department.objects.filter(code=department_code).first()
    if not dept:
        return None

    active_hod = DepartmentRoleAssignment.objects.filter(
        department_id=department_code,
        role_name="HOD",
        status="ACTIVE",
    ).first()

    active_admin = DepartmentRoleAssignment.objects.filter(
        department_id=department_code,
        role_name="DEPT_ADMIN",
        status="ACTIVE",
    ).first()

    return {
        "code": dept.code,
        "name": dept.name,
        "description": dept.description,
        "core_policies": dept.core_policies,
        "head_of_department_id": active_hod.user_id if active_hod else None,
        "department_admin_id": active_admin.user_id if active_admin else None,
        "created_at": dept.created_at,
        "updated_at": dept.updated_at,
    }


def list_pending_official_changes(department_code: str) -> QuerySet[OfficialDetailChangeRequest]:
    return OfficialDetailChangeRequest.objects.filter(
        department_id=department_code,
        status="PENDING",
    ).order_by("-created_at")
