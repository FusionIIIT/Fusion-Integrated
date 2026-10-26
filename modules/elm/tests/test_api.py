"""API tests for the ELM submission/tracking MVP."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveApplication, LeaveCategory

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, user_id=1001, modules=("elm_leave",)):
    stub_iam(make_session(user_id=user_id, modules=modules))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


def _payload(**overrides):
    return {
        "leave_type": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "reason": "Personal work",
        **overrides,
    }


def test_leave_types_returns_the_synchronized_category_codes(stub_iam):
    response = _client(stub_iam).get("/api/v1/elm/leave-types")

    assert response.status_code == 200
    assert [item["code"] for item in response.json()["results"]] == [
        "CL", "RH", "SCL", "EL", "COL", "VL",
    ]
    assert dict(LeaveCategory.choices)["EL"] == "Earned Leave"


def test_employee_can_submit_a_pending_application_and_cannot_set_owner_or_status(stub_iam):
    response = _client(stub_iam, user_id=1001).post(
        "/api/v1/elm/applications",
        _payload(user_id=9999, status="approved"),
        format="json",
    )

    assert response.status_code == 201, response.json()
    saved = LeaveApplication.objects.get()
    assert saved.user_id == 1001
    assert saved.status == LeaveApplication.Status.PENDING
    assert saved.days_requested == 2
    assert response.json()["days_requested"] == 2
    assert response.json()["leave_type_label"] == "Casual Leave"


def test_employee_lists_only_their_own_applications(stub_iam):
    LeaveApplication.objects.create(
        user_id=1001, leave_type="CL", start_date="2026-11-02",
        end_date="2026-11-02", reason="Mine",
    )
    LeaveApplication.objects.create(
        user_id=2002, leave_type="EL", start_date="2026-11-05",
        end_date="2026-11-05", reason="Not mine",
    )

    response = _client(stub_iam, user_id=1001).get("/api/v1/elm/applications")

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["reason"] == "Mine"
    assert "user_id" not in response.json()["results"][0]


def test_end_date_before_start_is_rejected(stub_iam):
    response = _client(stub_iam).post(
        "/api/v1/elm/applications",
        _payload(start_date="2026-11-04", end_date="2026-11-03"),
        format="json",
    )

    assert response.status_code == 400
    details = response.json()["error"]["details"]
    assert any(item["field"] == "end_date" for item in details)
    assert LeaveApplication.objects.count() == 0


def test_blank_reason_is_rejected(stub_iam):
    response = _client(stub_iam).post(
        "/api/v1/elm/applications", _payload(reason="   "), format="json"
    )

    assert response.status_code == 400
    details = response.json()["error"]["details"]
    assert any(item["field"] == "reason" for item in details)
    assert LeaveApplication.objects.count() == 0


def test_overlapping_pending_leave_is_rejected(stub_iam):
    LeaveApplication.objects.create(
        user_id=1001, leave_type="CL", start_date="2026-11-02",
        end_date="2026-11-04", reason="Existing request",
    )

    response = _client(stub_iam).post(
        "/api/v1/elm/applications",
        _payload(start_date="2026-11-04", end_date="2026-11-05"),
        format="json",
    )

    assert response.status_code == 400
    details = response.json()["error"]["details"]
    assert any(item["field"] == "start_date" for item in details)
    assert LeaveApplication.objects.count() == 1


def test_module_grant_is_required(stub_iam):
    response = _client(stub_iam, modules=()).get("/api/v1/elm/applications")
    assert response.status_code == 403
