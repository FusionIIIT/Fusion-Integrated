"""API integration tests for leave applications and balances."""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import (
    HolidayCalendar,
    LeaveAccount,
    LeaveApplication,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("elm",))
    stub_iam(make_session(modules=modules, **kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")
    return c


def test_leave_balances_view(stub_iam):
    LeaveAccount.objects.create(
        user_id=101,
        year=2026,
        category="CL",
        credited=Decimal("8.00"),
        carried_forward=Decimal("0.00"),
        availed=Decimal("2.00"),
        balance=Decimal("6.00"),
    )

    c = _client(
        stub_iam,
        user_id=101,
        permissions=("elm.leave.view_self",),
    )
    resp = c.get("/api/v1/elm/balances?year=2026")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 101
    assert data["year"] == 2026
    assert data["balances"]["CL"] == "6.00"


def test_apply_leave_success(stub_iam, user_ref):
    # Setup published holiday calendar
    HolidayCalendar.objects.create(year=2026, is_published=True)

    # Initial CL balance
    LeaveAccount.objects.create(
        user_id=101,
        year=2026,
        category="CL",
        credited=Decimal("8.00"),
        balance=Decimal("8.00"),
    )

    stub_iam(
        make_session(
            user_id=101,
            kind="faculty",
            roles=("faculty",),
            permissions=("elm.leave.apply", "elm.leave.view_self"),
            modules=("elm",),
        ),
        users={101: user_ref(101, name="Prof. Raman", kind="faculty")},
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")

    payload = {
        "category": "CL",
        "start_date": "2026-10-12",  # Monday
        "end_date": "2026-10-14",    # Wednesday (3 working days)
        "purpose": "Personal errand",
    }
    resp = c.post("/api/v1/elm/applications", data=payload, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == 101
    assert data["category"] == "CL"
    assert Decimal(data["chargeable_days"]) == Decimal("3.00")
    assert data["status"] == "awaiting_unit_head"


def test_apply_leave_permission_denied(stub_iam):
    c = _client(
        stub_iam,
        user_id=101,
        permissions=("elm.leave.view_self",),  # lacking elm.leave.apply
    )
    resp = c.post(
        "/api/v1/elm/applications",
        data={"category": "CL", "start_date": "2026-10-12", "end_date": "2026-10-13", "purpose": "Test"},
        format="json",
    )
    assert resp.status_code == 403


def test_withdraw_leave(stub_iam):
    app = LeaveApplication.objects.create(
        user_id=101,
        category="CL",
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 14),
        chargeable_days=Decimal("3.00"),
        purpose="Family visit",
        status="awaiting_unit_head",
    )

    c = _client(
        stub_iam,
        user_id=101,
        permissions=("elm.leave.withdraw", "elm.leave.view_self"),
    )
    resp = c.post(
        f"/api/v1/elm/applications/{app.id}/withdraw",
        data={"reason": "Plans cancelled"},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == "withdrawn"
    assert app.withdrawn_reason == "Plans cancelled"


def test_export_leave_record(stub_iam, user_ref):
    app = LeaveApplication.objects.create(
        user_id=101,
        category="CL",
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 14),
        chargeable_days=Decimal("3.00"),
        purpose="Conference",
        status="approved",
        final_decision="approve",
    )

    stub_iam(
        make_session(
            user_id=101,
            permissions=("elm.leave.view_self",),
            modules=("elm",),
        ),
        users={101: user_ref(101, name="Dr. Mehta")},
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")

    resp = c.get(f"/api/v1/elm/applications/{app.id}/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_type"] == "ELM_LEAVE_APPLICATION_RECORD"
    assert data["application_id"] == app.id
    assert data["applicant"]["name"] == "Dr. Mehta"
    assert data["leave_details"]["status"] == "approved"
