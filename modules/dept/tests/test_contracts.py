"""Tests for cross-module contract API functions (CFR-DEPT-001, CFR-DEPT-016)."""

import datetime

import pytest
from django.utils import timezone

from modules.dept.contracts import (
    get_active_department_admins,
    get_active_department_heads,
    get_department_details,
)
from modules.dept.models import Department, DepartmentRoleAssignment

pytestmark = pytest.mark.django_db


def test_contracts_plural_queries():
    cse = Department.objects.create(
        code="CSE", name="Computer Science", description="CSE Department"
    )
    ece = Department.objects.create(
        code="ECE", name="Electronics", description="ECE Department"
    )

    now = timezone.now()
    start_d = now - datetime.timedelta(days=10)
    end_d = now + datetime.timedelta(days=100)

    DepartmentRoleAssignment.objects.create(
        department=cse,
        role_name="HOD",
        user_id="prof_cse_hod",
        start_date=start_d,
        end_date=end_d,
        status="ACTIVE",
        assigned_by_id="admin_1",
    )
    DepartmentRoleAssignment.objects.create(
        department=cse,
        role_name="DEPT_ADMIN",
        user_id="admin_cse",
        start_date=start_d,
        end_date=end_d,
        status="ACTIVE",
        assigned_by_id="admin_1",
    )
    DepartmentRoleAssignment.objects.create(
        department=ece,
        role_name="HOD",
        user_id="prof_ece_hod",
        start_date=start_d,
        end_date=end_d,
        status="ACTIVE",
        assigned_by_id="admin_1",
    )

    # 1. get_department_details
    details = get_department_details(["CSE", "ECE", "MECH"])
    assert "CSE" in details
    assert details["CSE"]["name"] == "Computer Science"
    assert "ECE" in details
    assert "MECH" not in details

    # 2. get_active_department_heads
    heads = get_active_department_heads(["CSE", "ECE", "MECH"])
    assert heads.get("CSE") == "prof_cse_hod"
    assert heads.get("ECE") == "prof_ece_hod"
    assert "MECH" not in heads

    # 3. get_active_department_admins
    admins = get_active_department_admins(["CSE", "ECE"])
    assert admins.get("CSE") == "admin_cse"
    assert "ECE" not in admins
