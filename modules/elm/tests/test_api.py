"""API integration tests for Leave Management (ELM)."""
from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveCategory
from modules.elm.services import applications as svc

pytestmark = pytest.mark.django_db


@pytest.fixture
def categories():
    svc.ensure_leave_categories()
    return {c.code: c for c in LeaveCategory.objects.all()}


def _auth_client(
    stub_iam,
    user_id=1001,
    permissions=("elm.leave.view_self", "elm.leave.apply", "elm.leave.withdraw"),
    kind="staff",
):
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            modules=("elm",),
            permissions=permissions,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def test_unauthenticated_request_rejected():
    client = APIClient()
    res = client.get("/api/v1/elm/categories")
    assert res.status_code in (401, 403)


def test_list_categories(stub_iam, categories):
    client = _auth_client(stub_iam, user_id=1001)
    res = client.get("/api/v1/elm/categories")
    assert res.status_code == 200
    codes = [c["code"] for c in res.json()]
    assert "CL" in codes
    assert "EL" in codes


def test_list_balances(stub_iam, categories):
    client = _auth_client(stub_iam, user_id=1001)
    res = client.get("/api/v1/elm/balances")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 5
    cl_row = next(b for b in data if b["category"]["code"] == "CL")
    assert float(cl_row["balance"]) == 8.0


def test_apply_leave_success(stub_iam, categories):
    client = _auth_client(stub_iam, user_id=1001)
    payload = {
        "category_code": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "reason": "Personal errands",
        "half_day": "none",
    }
    res = client.post("/api/v1/elm/applications", data=payload, format="json")
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "submitted"
    assert float(body["days_count"]) == 2.0


def test_apply_overlapping_returns_409(stub_iam, categories):
    client = _auth_client(stub_iam, user_id=1001)
    payload = {
        "category_code": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "reason": "Personal errands",
    }
    res1 = client.post("/api/v1/elm/applications", data=payload, format="json")
    assert res1.status_code == 201

    # Apply overlapping interval
    res2 = client.post("/api/v1/elm/applications", data=payload, format="json")
    assert res2.status_code == 409


def test_someone_elses_application_is_404_not_403(stub_iam, categories):
    # User 1001 creates application
    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Private reason",
    )

    # User 2002 attempts to view it
    client = _auth_client(stub_iam, user_id=2002)
    res = client.get(f"/api/v1/elm/applications/{app.id}")
    assert res.status_code == 404


def test_applicant_can_withdraw(stub_iam, categories):
    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Doctor",
    )
    client = _auth_client(stub_iam, user_id=1001)
    res = client.post(
        f"/api/v1/elm/applications/{app.id}/withdraw",
        data={"remarks": "Not needed"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["status"] == "withdrawn"


def test_substitute_consent_api(stub_iam, categories):
    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Meeting",
        substitute_id=2002,
    )
    assert app.status == "pending_substitute"

    # Substitute 2002 accepts
    client = _auth_client(
        stub_iam,
        user_id=2002,
        permissions=("elm.leave.view_self", "elm.leave.substitute_respond"),
    )
    res = client.post(
        f"/api/v1/elm/applications/{app.id}/substitute",
        data={"action": "accept", "remarks": "Covering duties"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["status"] == "submitted"
    assert res.json()["substitute_status"] == "accepted"


def test_unit_head_transition_via_api(stub_iam, categories):
    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Leave",
    )
    # Unit head approves
    client = _auth_client(
        stub_iam,
        user_id=9001,
        permissions=(
            "elm.leave.view_self",
            "elm.leave.review_unit_head",
            "elm.leave.sanction",
        ),
    )
    res = client.post(
        f"/api/v1/elm/applications/{app.id}/transition",
        data={"action": "approve", "remarks": "Approved by HOD"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["status"] == "approved"
