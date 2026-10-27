from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import LeaveRequest

pytestmark = pytest.mark.django_db

MODULE = "leave"
CREATE = "leave.request.create"
VIEW = "leave.request.view_self"
DELETE = "leave.request.delete"


def client(stub_iam, *, user_id=1001, permissions=()):
    stub_iam(make_session(user_id=user_id, kind="staff", roles=("staff",),
                          active_role="staff", modules=(MODULE,),
                          permissions=permissions))
    result = APIClient()
    result.credentials(HTTP_AUTHORIZATION="Token abc")
    return result


def payload(**overrides):
    value = {
        "category": "cl", "starts_on": "2026-10-12", "ends_on": "2026-10-12",
        "cl_half": "first", "reason": "Medical appointment",
    }
    value.update(overrides)
    return value


def test_create_list_and_withdraw_own_request(stub_iam):
    c = client(stub_iam, permissions=(CREATE, VIEW, DELETE))
    created = c.post("/api/v1/leave/requests", payload(), format="json")
    assert created.status_code == 201
    request_id = created.json()["id"]
    assert c.get("/api/v1/leave/requests").json()["results"][0]["id"] == request_id
    withdrawn = c.post(f"/api/v1/leave/requests/{request_id}/withdraw")
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"


def test_other_employee_request_is_hidden_and_cannot_be_withdrawn(stub_iam):
    row = LeaveRequest.objects.create(
        user_id=2002, category="cl", starts_on=date(2026, 10, 12),
        ends_on=date(2026, 10, 12), cl_half="full", reason="Private")
    c = client(stub_iam, permissions=(VIEW, DELETE))
    assert c.get("/api/v1/leave/requests").json()["results"] == []
    assert c.post(f"/api/v1/leave/requests/{row.pk}/withdraw").status_code == 404


def test_permission_and_module_grants_are_both_required(stub_iam):
    c = client(stub_iam)
    assert c.post("/api/v1/leave/requests", payload(), format="json").status_code == 403
    stub_iam(make_session(user_id=1001, kind="staff", roles=("staff",),
                          active_role="staff", modules=(), permissions=(CREATE,)))
    assert c.post("/api/v1/leave/requests", payload(), format="json").status_code == 403


def test_same_half_day_is_blocked_but_other_half_is_allowed(stub_iam):
    c = client(stub_iam, permissions=(CREATE,))
    assert c.post("/api/v1/leave/requests", payload(), format="json").status_code == 201
    assert c.post("/api/v1/leave/requests", payload(), format="json").status_code == 409
    assert c.post("/api/v1/leave/requests", payload(cl_half="second"),
                  format="json").status_code == 201


def test_approved_request_also_blocks_an_overlapping_application(stub_iam):
    LeaveRequest.objects.create(
        user_id=1001, category="cl", starts_on=date(2026, 10, 12),
        ends_on=date(2026, 10, 12), cl_half="full", reason="Approved",
        status=LeaveRequest.STATUS_APPROVED,
    )
    c = client(stub_iam, permissions=(CREATE,))
    assert c.post("/api/v1/leave/requests", payload(cl_half="full"),
                  format="json").status_code == 409


def test_station_leave_details_are_required(stub_iam):
    c = client(stub_iam, permissions=(CREATE,))
    response = c.post("/api/v1/leave/requests", payload(station_leave=True), format="json")
    assert response.status_code == 400
    assert "station_leave_details" in response.json()


def test_withdrawal_is_terminal(stub_iam):
    c = client(stub_iam, permissions=(CREATE, DELETE))
    request_id = c.post("/api/v1/leave/requests", payload(), format="json").json()["id"]
    assert c.post(f"/api/v1/leave/requests/{request_id}/withdraw").status_code == 200
    assert c.post(f"/api/v1/leave/requests/{request_id}/withdraw").status_code == 409
