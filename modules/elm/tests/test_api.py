"""API tests for Employee Leave Management endpoints."""
import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.domain.state_machine import LeaveCategory
from modules.elm.models import LeaveApplication

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, uid=101, modules=("elm",), permissions=(), kind="staff"):
    stub_iam(make_session(user_id=uid, kind=kind, permissions=permissions, modules=modules))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_unauthenticated_request_is_rejected():
    c = APIClient()
    res = c.get("/api/v1/elm/leave-applications")
    assert res.status_code in (401, 403)


def test_user_without_module_grant_is_forbidden(stub_iam):
    c = _client(
        stub_iam,
        modules=("placement_cell",),  # elm is not granted
        permissions=("elm.leave_application.view_self",),
    )
    res = c.get("/api/v1/elm/leave-applications")
    assert res.status_code == 403


def test_employee_can_apply_for_leave(stub_iam):
    c = _client(
        stub_iam,
        uid=301,
        permissions=("elm.leave_application.apply", "elm.leave_application.view_self"),
    )
    payload = {
        "category": LeaveCategory.CASUAL.value,
        "start_date": "2026-11-10",
        "end_date": "2026-11-12",
        "reason": "Personal work",
    }
    res = c.post("/api/v1/elm/leave-applications", payload, format="json")
    assert res.status_code == 201
    body = res.json()
    assert body["user_id"] == 301
    assert body["status"] == "pending"
    assert body["category"] == "casual"


def test_employee_only_sees_own_applications(stub_iam):
    LeaveApplication.objects.create(
        user_id=101,
        category="casual",
        start_date=datetime.date(2026, 11, 1),
        end_date=datetime.date(2026, 11, 2),
        reason="Mine",
    )
    LeaveApplication.objects.create(
        user_id=999,
        category="medical",
        start_date=datetime.date(2026, 11, 1),
        end_date=datetime.date(2026, 11, 2),
        reason="Other employee",
    )
    c = _client(
        stub_iam,
        uid=101,
        permissions=("elm.leave_application.view_self",),
    )
    res = c.get("/api/v1/elm/leave-applications")
    assert res.status_code == 200
    results = res.json()["results"] if "results" in res.json() else res.json()
    assert len(results) == 1
    assert results[0]["user_id"] == 101


def test_hr_sees_all_applications(stub_iam):
    LeaveApplication.objects.create(
        user_id=101,
        category="casual",
        start_date=datetime.date(2026, 11, 1),
        end_date=datetime.date(2026, 11, 2),
        reason="Emp 1",
    )
    LeaveApplication.objects.create(
        user_id=102,
        category="medical",
        start_date=datetime.date(2026, 11, 1),
        end_date=datetime.date(2026, 11, 2),
        reason="Emp 2",
    )
    c = _client(
        stub_iam,
        uid=500,
        permissions=("elm.leave_application.manage", "elm.leave_application.view_self"),
    )
    res = c.get("/api/v1/elm/leave-applications")
    assert res.status_code == 200
    results = res.json()["results"] if "results" in res.json() else res.json()
    assert len(results) == 2


def test_hr_can_review_application(stub_iam):
    app = LeaveApplication.objects.create(
        user_id=101,
        category="casual",
        start_date=datetime.date(2026, 11, 1),
        end_date=datetime.date(2026, 11, 2),
        reason="Need leave",
    )
    c = _client(
        stub_iam,
        uid=500,
        permissions=("elm.leave_application.manage",),
    )
    res = c.post(
        f"/api/v1/elm/leave-applications/{app.id}/review",
        {"action": "approve", "remarks": "Looks good"},
        format="json",
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "approved"
    assert body["remarks"] == "Looks good"
    assert body["reviewed_by_user_id"] == 500


def test_employee_cannot_review_application(stub_iam):
    app = LeaveApplication.objects.create(
        user_id=101,
        category="casual",
        start_date=datetime.date(2026, 11, 1),
        end_date=datetime.date(2026, 11, 2),
        reason="Need leave",
    )
    c = _client(
        stub_iam,
        uid=101,
        permissions=("elm.leave_application.view_self", "elm.leave_application.apply"),
    )
    res = c.post(
        f"/api/v1/elm/leave-applications/{app.id}/review",
        {"action": "approve", "remarks": "Self-approval"},
        format="json",
    )
    assert res.status_code == 403


def test_detail_view_scoped(stub_iam):
    app = LeaveApplication.objects.create(
        user_id=101,
        category="casual",
        start_date=datetime.date(2026, 11, 1),
        end_date=datetime.date(2026, 11, 2),
        reason="My leave",
    )
    # Own leave -> 200
    c_owner = _client(stub_iam, uid=101, permissions=("elm.leave_application.view_self",))
    assert c_owner.get(f"/api/v1/elm/leave-applications/{app.id}").status_code == 200

    # Foreign leave -> 404 (NotFoundError from selector)
    c_other = _client(stub_iam, uid=999, permissions=("elm.leave_application.view_self",))
    assert c_other.get(f"/api/v1/elm/leave-applications/{app.id}").status_code == 404
