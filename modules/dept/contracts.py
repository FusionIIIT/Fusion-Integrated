"""Public contracts for the Department module.

External modules must communicate through these functions rather than
importing dept internals directly (ADR-0013 / ADR-0001).
All getters are plural.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from modules.dept.models.department import Department
from modules.dept.models.roles import DepartmentRoleAssignment


def get_department_details(department_codes: Sequence[str]) -> dict[str, dict[str, Any]]:
    """Return department metadata and authoritative Headship for given department codes."""
    depts = Department.objects.filter(code__in=department_codes)
    active_hods = {
        ra.department.code: ra.user_id
        for ra in DepartmentRoleAssignment.objects.filter(
            department__code__in=department_codes,
            role_name="HOD",
            status="ACTIVE",
        )
    }

    results = {}
    for d in depts:
        results[d.code] = {
            "code": d.code,
            "name": d.name,
            "description": d.description,
            "core_policies": d.core_policies,
            "head_of_department_id": active_hods.get(d.code),
        }
    return results


def get_active_department_heads(department_codes: Sequence[str]) -> dict[str, str]:
    """Return mapping of department code to active HOD user_id."""
    return {
        ra.department.code: ra.user_id
        for ra in DepartmentRoleAssignment.objects.filter(
            department__code__in=department_codes,
            role_name="HOD",
            status="ACTIVE",
        )
    }


def get_active_department_admins(department_codes: Sequence[str]) -> dict[str, str]:
    """Return mapping of department code to active Dept_Admin user_id."""
    return {
        ra.department.code: ra.user_id
        for ra in DepartmentRoleAssignment.objects.filter(
            department__code__in=department_codes,
            role_name="DEPT_ADMIN",
            status="ACTIVE",
        )
    }
