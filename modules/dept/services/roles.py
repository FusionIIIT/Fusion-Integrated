"""Department role tenure and access transition services (CFR-DEPT-016, CW-DEPT-04)."""

from __future__ import annotations

import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.dept.domain.roles import validate_role_tenure
from modules.dept.models.department import Department
from modules.dept.models.roles import DepartmentRoleAssignment


@transaction.atomic
def assign_department_role(
    department_code: str,
    role_name: str,
    user_id: str,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    assigned_by_principal: Any,
) -> DepartmentRoleAssignment:
    validate_role_tenure(role_name, start_date, end_date)

    dept, _ = Department.objects.get_or_create(
        code=department_code,
        defaults={"name": f"Department of {department_code}"},
    )

    now = timezone.now()
    is_immediate = start_date <= now <= end_date
    status = "ACTIVE" if is_immediate else "SCHEDULED"

    if status == "ACTIVE":
        # Revoke outgoing active assignment for this (dept, role) (BR-DEPT-022, BR-DEPT-024)
        DepartmentRoleAssignment.objects.filter(
            department=dept,
            role_name=role_name,
            status="ACTIVE",
        ).update(status="REVOKED", updated_at=now)

    assigner_id = str(
        getattr(assigned_by_principal, "user_id", getattr(assigned_by_principal, "id", "admin"))
    )

    return DepartmentRoleAssignment.objects.create(
        department=dept,
        role_name=role_name,
        user_id=user_id.strip(),
        start_date=start_date,
        end_date=end_date,
        status=status,
        assigned_by_id=assigner_id,
    )


@transaction.atomic
def revoke_department_role(
    assignment_id: str,
    revoked_by_principal: Any,
) -> DepartmentRoleAssignment:
    ra = DepartmentRoleAssignment.objects.select_for_update().get(id=assignment_id)
    ra.status = "REVOKED"
    ra.save(update_fields=["status", "updated_at"])
    return ra


@transaction.atomic
def evaluate_role_transitions() -> int:
    """Scheduled task to activate scheduled roles and expire ended tenures."""
    now = timezone.now()
    count = 0

    # Expire active roles past end_date
    expired = DepartmentRoleAssignment.objects.filter(
        status="ACTIVE",
        end_date__lte=now,
    ).update(status="EXPIRED", updated_at=now)
    count += expired

    # Activate scheduled roles whose start_date has arrived
    to_activate = DepartmentRoleAssignment.objects.filter(
        status="SCHEDULED",
        start_date__lte=now,
        end_date__gt=now,
    )

    for ra in to_activate:
        DepartmentRoleAssignment.objects.filter(
            department=ra.department,
            role_name=ra.role_name,
            status="ACTIVE",
        ).update(status="REVOKED", updated_at=now)

        ra.status = "ACTIVE"
        ra.save(update_fields=["status", "updated_at"])
        count += 1

    return count
