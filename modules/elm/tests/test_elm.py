import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import HolidayCalendar, LeaveBalance
from modules.elm.services import apply_leave, cancel_leave, ensure_default_balances, review_leave

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kwargs):
    stub_iam(make_session(**kwargs))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock_token")
    return client


def test_ensure_default_balances():
    balances = ensure_default_balances(user_id=101)
    assert len(balances) > 0
    cl = LeaveBalance.objects.get(user_id=101, leave_type="CL")
    assert cl.balance == 8


def test_apply_leave_service():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    app = apply_leave(
        user_id=101,
        leave_type="CL",
        start_date=today,
        end_date=tomorrow,
        reason="Personal work",
    )
    assert app.status == "PENDING"
    assert app.user_id == 101


def test_cancel_leave_service():
    today = datetime.date.today()
    app = apply_leave(
        user_id=101,
        leave_type="CL",
        start_date=today,
        end_date=today,
        reason="Doctor visit",
    )
    cancelled = cancel_leave(application_id=app.id, user_id=101)
    assert cancelled.status == "CANCELLED"


def test_review_leave_approval_deducts_balance():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    ensure_default_balances(user_id=202)
    initial_cl = LeaveBalance.objects.get(user_id=202, leave_type="CL").balance

    app = apply_leave(
        user_id=202,
        leave_type="CL",
        start_date=today,
        end_date=tomorrow,  # 2 days
        reason="Family function",
    )

    reviewed = review_leave(
        application_id=app.id,
        reviewer_user_id=999,
        action="APPROVED",
        remarks="Approved by HOD",
    )
    assert reviewed.status == "APPROVED"
    assert reviewed.reviewed_by_user_id == 999

    final_cl = LeaveBalance.objects.get(user_id=202, leave_type="CL").balance
    assert final_cl == initial_cl - 2


def test_api_my_leaves_and_apply(stub_iam):
    client = _client(
        stub_iam,
        user_id=303,
        modules=("elm",),
        permissions=("elm.leave.view_self", "elm.leave.create", "elm.balance.view"),
    )

    # Fetch balances
    resp = client.get("/api/v1/elm/balances/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 4

    # Apply leave
    today = datetime.date.today()
    apply_resp = client.post(
        "/api/v1/elm/applications/",
        {
            "leave_type": "CL",
            "start_date": str(today),
            "end_date": str(today),
            "reason": "Test API application",
        },
        format="json",
    )
    assert apply_resp.status_code == 201
    app_id = apply_resp.json()["id"]

    # View my leaves
    list_resp = client.get("/api/v1/elm/applications/")
    assert list_resp.status_code == 200
    assert any(item["id"] == app_id for item in list_resp.json())


def test_api_approvals_permission_enforcement(stub_iam):
    # Applicant without review permission
    applicant_client = _client(
        stub_iam,
        user_id=404,
        modules=("elm",),
        permissions=("elm.leave.view_self", "elm.leave.create"),
    )
    resp = applicant_client.get("/api/v1/elm/approvals/")
    assert resp.status_code == 403

    # Reviewer with review permission
    reviewer_client = _client(
        stub_iam,
        user_id=505,
        modules=("elm",),
        permissions=("elm.leave.view_self", "elm.leave.review"),
    )
    resp2 = reviewer_client.get("/api/v1/elm/approvals/")
    assert resp2.status_code == 200


def test_api_holiday_calendar(stub_iam):
    HolidayCalendar.objects.create(
        date=datetime.date(2026, 12, 25),
        description="Christmas Day",
        is_rh=False,
    )
    client = _client(
        stub_iam,
        user_id=606,
        modules=("elm",),
        permissions=("elm.holiday.view",),
    )
    resp = client.get("/api/v1/elm/holidays/")
    assert resp.status_code == 200
    assert any(h["description"] == "Christmas Day" for h in resp.json())
