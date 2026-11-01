"""Tests for data scoping and isolation between employees."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import LeaveRequest, LtcRequest

pytestmark = pytest.mark.django_db


def test_employee_sees_only_own_leaves(stub_iam, user_ref):
    LeaveRequest.objects.create(
        user_id=101,
        leave_type="casual",
        start_date="2026-03-01",
        end_date="2026-03-02",
        duration_days=1.0,
        justification="Personal",
        status="pending",
    )
    LeaveRequest.objects.create(
        user_id=102,
        leave_type="medical",
        start_date="2026-03-05",
        end_date="2026-03-06",
        duration_days=1.0,
        justification="Flu",
        status="pending",
    )

    stub_iam(
        make_session(
            user_id=101,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.leave.view_self",),
        ),
        users={101: user_ref(101, name="Dr. One", kind="faculty")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    resp = client.get("/api/v1/hreis/leaves/")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["user_id"] == 101


def test_employee_cannot_view_another_employees_ltc(stub_iam, user_ref):
    ltc_b = LtcRequest.objects.create(
        user_id=102,
        request_type="advance",
        block_year="2026-2029",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date="2026-04-01",
        travel_end_date="2026-04-05",
        estimated_amount=12000.0,
        status="submitted",
    )

    stub_iam(
        make_session(
            user_id=101,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.ltc.view_self",),
        ),
        users={101: user_ref(101, name="Dr. One", kind="faculty")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    # Scoping should hide record of user 102 from user 101 -> 404
    resp = client.get(f"/api/v1/hreis/ltc/{ltc_b.id}/")
    assert resp.status_code == 404
