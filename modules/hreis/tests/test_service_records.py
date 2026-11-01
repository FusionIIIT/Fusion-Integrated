"""Tests for Employee Service Record endpoints and permissions."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import EmployeeServiceRecord

pytestmark = pytest.mark.django_db


def test_employee_can_view_own_service_record(stub_iam, user_ref):
    EmployeeServiceRecord.objects.create(
        user_id=101,
        employee_id="PF-101",
        category="faculty",
        designation="Assistant Professor",
        department="Computer Science and Engineering",
        appointment_date="2020-01-15",
        leave_balances={"casual": 8.0, "medical": 15.0},
        cpda_balance=300000.0,
    )

    stub_iam(
        make_session(
            user_id=101,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.service_record.view_self",),
        ),
        users={101: user_ref(101, name="Dr. Alice Smith", kind="faculty")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    resp = client.get("/api/v1/hreis/service-records/me/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["employee_id"] == "PF-101"
    assert data["designation"] == "Assistant Professor"
    assert data["leave_balances"]["casual"] == 8.0


def test_regular_employee_cannot_create_service_record(stub_iam, user_ref):
    stub_iam(
        make_session(
            user_id=101,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.service_record.view_self",),
        ),
        users={101: user_ref(101, name="Dr. Alice Smith", kind="faculty")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    resp = client.post(
        "/api/v1/hreis/service-records/",
        {
            "user_id": 102,
            "employee_id": "PF-102",
            "category": "faculty",
            "designation": "Associate Professor",
            "department": "ECE",
            "appointment_date": "2021-01-15",
        },
        format="json",
    )
    assert resp.status_code == 403


def test_hr_admin_can_create_and_manage_service_records(stub_iam, user_ref):
    stub_iam(
        make_session(
            user_id=999,
            kind="staff",
            roles=("hr_admin",),
            modules=("hr_eis",),
            permissions=(
                "hr_eis.service_record.manage",
                "hr_eis.service_record.view_all",
            ),
        ),
        users={999: user_ref(999, name="HR Manager", kind="staff")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    # Create
    resp = client.post(
        "/api/v1/hreis/service-records/",
        {
            "user_id": 102,
            "employee_id": "PF-102",
            "category": "faculty",
            "designation": "Associate Professor",
            "department": "ECE",
            "appointment_date": "2021-01-15",
            "leave_balances": {"casual": 8.0, "medical": 15.0},
            "cpda_balance": 300000.0,
        },
        format="json",
    )
    assert resp.status_code == 201
    rec_id = resp.json()["id"]

    # Read
    resp_get = client.get(f"/api/v1/hreis/service-records/{rec_id}/")
    assert resp_get.status_code == 200
    assert resp_get.json()["employee_id"] == "PF-102"

    # Update
    resp_patch = client.patch(
        f"/api/v1/hreis/service-records/{rec_id}/",
        {"designation": "Professor"},
        format="json",
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["designation"] == "Professor"
