import pytest
from datetime import date
from decimal import Decimal
from rest_framework.test import APIClient
from modules.elm.models import LeaveBalance, LeaveRequest
from conftest import make_session

@pytest.fixture
def auth_client(stub_iam):
    client = APIClient()
    session = make_session(
        user_id=101,
        modules=("elm",),
        permissions=(
            "elm.leave.view_self",
            "elm.leave.apply",
            "elm.leave.review",
            "elm.policy.manage",
        ),
        kind="faculty",
        roles=("faculty",),
    )
    stub_iam(session=session)
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client

@pytest.mark.django_db
def test_api_catalog(auth_client):
    res = auth_client.get("/api/v1/elm/catalog")
    assert res.status_code == 200
    assert "CL" in res.data["entitlements"]

@pytest.mark.django_db
def test_api_leave_balances(auth_client):
    LeaveBalance.objects.create(
        user_id=101, category="CL", year=date.today().year,
        credited=Decimal("8.00"), availed=Decimal("0.00"), balance=Decimal("8.00")
    )
    res = auth_client.get("/api/v1/elm/balances")
    assert res.status_code == 200
    assert len(res.data) == 1
    assert res.data[0]["category"] == "CL"

@pytest.mark.django_db
def test_api_apply_and_withdraw_leave(auth_client):
    LeaveBalance.objects.create(
        user_id=101, category="CL", year=2026,
        credited=Decimal("8.00"), availed=Decimal("0.00"), balance=Decimal("8.00")
    )
    payload = {
        "category": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-02",
        "purpose": "Personal errand",
    }
    res = auth_client.post("/api/v1/elm/requests", payload, format="json")
    assert res.status_code == 201
    req_id = res.data["id"]
    assert res.data["status"] == "under_review"

    # Withdraw
    res_w = auth_client.post(f"/api/v1/elm/requests/{req_id}/withdraw")
    assert res_w.status_code == 200
    assert res_w.data["status"] == "withdrawn"

@pytest.mark.django_db
def test_api_substitute_and_review(auth_client, stub_iam):
    LeaveBalance.objects.create(
        user_id=101, category="CL", year=2026,
        credited=Decimal("8.00"), availed=Decimal("0.00"), balance=Decimal("8.00")
    )
    payload = {
        "category": "CL",
        "start_date": "2026-11-05",
        "end_date": "2026-11-05",
        "purpose": "Personal errand",
        "substitute_id": 102,
    }
    res = auth_client.post("/api/v1/elm/requests", payload, format="json")
    assert res.status_code == 201
    req_id = res.data["id"]
    assert res.data["status"] == "awaiting_substitute"

    # Substitute (user_id=102) accepts
    sub_session = make_session(
        user_id=102,
        modules=("elm",),
        permissions=("elm.leave.view_self",),
        kind="faculty",
        roles=("faculty",),
    )
    stub_iam(session=sub_session)
    res_sub = auth_client.post(f"/api/v1/elm/tasks/substitute/{req_id}/respond", {"action": "accept"}, format="json")
    assert res_sub.status_code == 200
    assert res_sub.data["status"] == "accepted"

    # Review approval by reviewer
    reviewer_session = make_session(
        user_id=200,
        modules=("elm",),
        permissions=("elm.leave.review",),
        kind="faculty",
        roles=("faculty",),
    )
    stub_iam(session=reviewer_session)
    res_rev = auth_client.post(f"/api/v1/elm/tasks/review/{req_id}/decision", {"action": "approve"}, format="json")
    assert res_rev.status_code == 200
    assert res_rev.data["status"] == "sanctioned"

@pytest.mark.django_db
def test_api_extend_and_print(auth_client):
    LeaveBalance.objects.create(
        user_id=101, category="EL", year=2026,
        credited=Decimal("30.00"), availed=Decimal("5.00"), balance=Decimal("25.00")
    )
    req = LeaveRequest.objects.create(
        user_id=101, category="EL", start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 5), leave_days=Decimal("5.00"),
        purpose="Annual leave", status="sanctioned"
    )
    # Extend
    res_ext = auth_client.post(f"/api/v1/elm/requests/{req.id}/extend", {"new_end_date": "2026-11-07"}, format="json")
    assert res_ext.status_code == 200
    assert res_ext.data["end_date"] == "2026-11-07"

    # Print
    res_prn = auth_client.get(f"/api/v1/elm/requests/{req.id}/print")
    assert res_prn.status_code == 200
    assert res_prn.data["applicant_id"] == 101

@pytest.mark.django_db
def test_api_resumption_workflow(auth_client):
    LeaveBalance.objects.create(
        user_id=101, category="EL", year=2026,
        credited=Decimal("30.00"), availed=Decimal("5.00"), balance=Decimal("25.00")
    )
    req = LeaveRequest.objects.create(
        user_id=101, category="EL", start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 6), leave_days=Decimal("5.00"),
        purpose="Annual leave", status="sanctioned"
    )
    # Submit resumption
    res_sub = auth_client.post(f"/api/v1/elm/requests/{req.id}/resumption", {"resumption_date": "2026-11-05"}, format="json")
    assert res_sub.status_code == 200
    assert res_sub.data["resumption_status"] == "pending"

    # Review resumption
    res_rev = auth_client.post(f"/api/v1/elm/tasks/resumption/{req.id}/review", {"remarks": "Approved early return"}, format="json")
    assert res_rev.status_code == 200
    assert res_rev.data["resumption_status"] == "completed"

@pytest.mark.django_db
def test_api_offline_record(auth_client):
    LeaveBalance.objects.create(
        user_id=102, category="CL", year=2026,
        credited=Decimal("8.00"), availed=Decimal("0.00"), balance=Decimal("8.00")
    )
    payload = {
        "user_id": 102,
        "category": "CL",
        "start_date": "2026-11-10",
        "end_date": "2026-11-10",
        "sanction_reference": "OFF/2026/01",
        "purpose": "Director manual sanction",
    }
    res = auth_client.post("/api/v1/elm/admin/offline-record", payload, format="json")
    assert res.status_code == 201
    assert res.data["is_offline_recorded"] is True
