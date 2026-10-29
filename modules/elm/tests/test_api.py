
"""ELM API ownership and access-control tests."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.elm.models import Leave

pytestmark = pytest.mark.django_db


@pytest.fixture
def employees():
    """Create database-backed directory records for leave ownership."""
    employee = UserRef.objects.create(
        user_id=1001,
        username="u1001",
        display_name="Asha Verma",
        kind="faculty",
        email="asha@example.com",
    )
    another_employee = UserRef.objects.create(
        user_id=2002,
        username="u2002",
        display_name="Rohan Shah",
        kind="staff",
        email="rohan@example.com",
    )
    return employee, another_employee


def _client(stub_iam, user_id=1001, permissions=(), modules=("elm",),
            kind="faculty", roles=("faculty",), active_role="faculty"):
    """Create an API client authenticated through the IAM test stub."""
    stub_iam(
        make_session(
            user_id=user_id,
            permissions=permissions,
            modules=modules,
            kind=kind,
            roles=roles,
            active_role=active_role,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


def test_employee_sees_only_own_leave_requests(stub_iam, employees):
    employee, another_employee = employees

    own_leave = Leave.objects.create(
        employee=employee,
        category="CL",
        start_date="2026-11-02",
        end_date="2026-11-03",
        reason="Personal work",
        status="submitted",
    )
    Leave.objects.create(
        employee=another_employee,
        category="CL",
        start_date="2026-11-02",
        end_date="2026-11-03",
        reason="Another employee's leave",
        status="submitted",
    )

    client = _client(
        stub_iam,
        user_id=1001,
        permissions=("elm.leave.view_self",),
    )

    response = client.get("/api/v1/elm/leaves/")

    assert response.status_code == 200
    rows = response.json()["results"]
    assert [row["id"] for row in rows] == [own_leave.id]


def test_employee_cannot_retrieve_another_employees_leave(
    stub_iam, employees
):
    _, another_employee = employees

    leave = Leave.objects.create(
        employee=another_employee,
        category="CL",
        start_date="2026-11-02",
        end_date="2026-11-03",
        reason="Private leave",
        status="submitted",
    )

    client = _client(
        stub_iam,
        user_id=1001,
        permissions=("elm.leave.view_self",),
    )

    response = client.get(f"/api/v1/elm/leaves/{leave.id}/")

    assert response.status_code == 404


def test_employee_cannot_create_leave_for_another_employee(
    stub_iam, employees
):
    employee, another_employee = employees

    client = _client(
        stub_iam,
        user_id=employee.user_id,
        permissions=("elm.leave.create",),
    )

    response = client.post(
        "/api/v1/elm/leaves/",
        {
            "employee_id": another_employee.user_id,
            "category": "CL",
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "reason": "Personal work",
        },
        format="json",
    )

    assert response.status_code == 201

    created_leave = Leave.objects.get(id=response.json()["id"])
    assert created_leave.employee_id == employee.user_id


def test_user_without_elm_module_grant_is_denied(stub_iam):
    client = _client(
        stub_iam,
        user_id=1001,
        permissions=("elm.leave.view_self",),
        modules=(),
    )

    response = client.get("/api/v1/elm/leaves/")

    assert response.status_code == 403
