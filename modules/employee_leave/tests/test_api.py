import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.employee_leave.models import LeaveHoliday, LeavePolicy

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, permissions=()):
    stub_iam(
        make_session(
            user_id=9001,
            kind="staff",
            roles=("leave_administrator",),
            active_role="leave_administrator",
            modules=("employee_leave",),
            permissions=permissions,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


def test_policy_and_calendar_lists_use_fusion_cursor_page_shape(stub_iam):
    LeavePolicy.objects.create(leave_type="CL", leave_year=2026)
    LeaveHoliday.objects.create(
        leave_year=2026, day="2026-10-12", name="Foundation Day", published=True
    )
    client = _client(stub_iam)

    policies = client.get("/api/v1/leave/policies")
    calendar = client.get("/api/v1/leave/calendar")

    assert policies.status_code == 200
    assert set(policies.json()) == {"next", "previous", "results"}
    assert policies.json()["results"][0]["leave_type"] == "CL"
    assert calendar.status_code == 200
    assert set(calendar.json()) == {"next", "previous", "results"}
    assert calendar.json()["results"][0]["name"] == "Foundation Day"


def test_policy_api_rejects_non_vacation_conversion(stub_iam):
    client = _client(
        stub_iam,
        permissions=("employee_leave.configuration.manage",),
    )

    response = client.post(
        "/api/v1/leave/policies",
        {
            "leave_type": "CL",
            "leave_year": 2026,
            "annual_entitlement": "12",
            "carry_forward_limit": "0",
            "year_end_treatment": "convert_to_el",
            "conversion_ratio": "1",
        },
        format="json",
    )

    assert response.status_code == 400
    assert not LeavePolicy.objects.exists()
