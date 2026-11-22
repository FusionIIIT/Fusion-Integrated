"""Integration tests for ELM workflows, reviews, and administration."""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.domain.constants import (
    ApplicationStatus,
    ExtensionStatus,
    ResumptionStatus,
    SubstituteStatus,
)
from modules.elm.models import (
    ApprovalHierarchy,
    HolidayCalendar,
    LeaveAccount,
    LeaveApplication,
    LeaveExtension,
    LeaveResumption,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("elm",))
    stub_iam(make_session(modules=modules, **kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")
    return c


def test_substitute_accept_and_decline_flow(stub_iam):
    app = LeaveApplication.objects.create(
        user_id=101,
        category="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 4),
        chargeable_days=Decimal("3.00"),
        purpose="Visiting family",
        requires_substitute=True,
        substitute_user_id=202,
        substitute_status=SubstituteStatus.PENDING.value,
        status=ApplicationStatus.AWAITING_SUBSTITUTE.value,
    )

    # 1. Substitute responds ACCEPT
    c_sub = _client(
        stub_iam,
        user_id=202,
        permissions=("elm.substitute.respond",),
    )
    resp = c_sub.post(
        f"/api/v1/elm/substitute/requests/{app.id}/respond",
        data={"accepted": True, "remarks": "Will cover duties"},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ApplicationStatus.AWAITING_UNIT_HEAD.value
    assert app.substitute_status == SubstituteStatus.ACCEPTED.value


def test_substitute_decline_and_replace_flow(stub_iam, user_ref):
    app = LeaveApplication.objects.create(
        user_id=101,
        category="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 4),
        chargeable_days=Decimal("3.00"),
        purpose="Visiting family",
        requires_substitute=True,
        substitute_user_id=202,
        substitute_status=SubstituteStatus.PENDING.value,
        status=ApplicationStatus.AWAITING_SUBSTITUTE.value,
    )

    # 1. Substitute declines
    c_sub = _client(
        stub_iam,
        user_id=202,
        permissions=("elm.substitute.respond",),
    )
    resp_dec = c_sub.post(
        f"/api/v1/elm/substitute/requests/{app.id}/respond",
        data={"accepted": False, "remarks": "Busy with exams"},
        format="json",
    )
    assert resp_dec.status_code == 200
    app.refresh_from_db()
    assert app.status == ApplicationStatus.APPLICANT_ACTION_REQUIRED.value
    assert app.substitute_status == SubstituteStatus.DECLINED.value

    # 2. Applicant replaces substitute
    stub_iam(
        make_session(
            user_id=101,
            permissions=("elm.leave.apply",),
            modules=("elm",),
        ),
        users={303: user_ref(303, name="Dr. Sen", kind="faculty")},
    )
    c_app = APIClient()
    c_app.credentials(HTTP_AUTHORIZATION="Token test-token")

    resp_rep = c_app.post(
        f"/api/v1/elm/applications/{app.id}/substitute-replace",
        data={"new_substitute_user_id": 303},
        format="json",
    )
    assert resp_rep.status_code == 200
    app.refresh_from_db()
    assert app.status == ApplicationStatus.AWAITING_SUBSTITUTE.value
    assert app.substitute_user_id == 303
    assert app.substitute_status == SubstituteStatus.PENDING.value


def test_unit_head_approval_cl_debits_balance(stub_iam):
    """BR-EL-016: Unit Head approval of CL is final decision and debits balance."""
    acc = LeaveAccount.objects.create(
        user_id=101,
        year=2026,
        category="CL",
        credited=Decimal("8.00"),
        availed=Decimal("0.00"),
        balance=Decimal("8.00"),
    )
    app = LeaveApplication.objects.create(
        user_id=101,
        category="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 4),
        chargeable_days=Decimal("3.00"),
        purpose="Urgent work",
        status=ApplicationStatus.AWAITING_UNIT_HEAD.value,
        unit_head_user_id=505,
    )

    c_uh = _client(
        stub_iam,
        user_id=505,
        permissions=("elm.review.unit_head",),
    )
    resp = c_uh.post(
        f"/api/v1/elm/reviews/unit-head/{app.id}/decision",
        data={"outcome": "approve", "remarks": "Approved by HOD"},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ApplicationStatus.APPROVED.value
    assert app.final_decision == "approve"

    # Verify balance was debited
    acc.refresh_from_db()
    assert acc.balance == Decimal("5.00")
    assert acc.availed == Decimal("3.00")


def test_higher_sanction_full_workflow(stub_iam):
    """EL workflow: Unit Head recommends -> Establishment forwards -> Sanctioning Authority approves."""
    acc = LeaveAccount.objects.create(
        user_id=101,
        year=2026,
        category="EL",
        credited=Decimal("30.00"),
        availed=Decimal("0.00"),
        balance=Decimal("30.00"),
    )
    app = LeaveApplication.objects.create(
        user_id=101,
        category="EL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 6),
        chargeable_days=Decimal("5.00"),
        purpose="Vacation with family",
        status=ApplicationStatus.AWAITING_UNIT_HEAD.value,
        unit_head_user_id=505,
        establishment_user_id=606,
        sanctioning_authority_user_id=707,
        sanctioning_authority_role="Dean",
    )

    # 1. Unit Head recommends
    c_uh = _client(stub_iam, user_id=505, permissions=("elm.review.unit_head",))
    r1 = c_uh.post(
        f"/api/v1/elm/reviews/unit-head/{app.id}/decision",
        data={"outcome": "recommended", "remarks": "Recommended"},
        format="json",
    )
    assert r1.status_code == 200
    app.refresh_from_db()
    assert app.status == ApplicationStatus.AWAITING_ESTABLISHMENT.value

    # 2. Establishment forwards
    c_estt = _client(stub_iam, user_id=606, permissions=("elm.review.establishment",))
    r2 = c_estt.post(
        f"/api/v1/elm/reviews/establishment/{app.id}/forward",
        data={"remarks": "Verified records, forwarded"},
        format="json",
    )
    assert r2.status_code == 200
    app.refresh_from_db()
    assert app.status == ApplicationStatus.AWAITING_FINAL_DECISION.value

    # 3. Sanctioning Authority approves
    c_dean = _client(stub_iam, user_id=707, permissions=("elm.sanction.decide",))
    r3 = c_dean.post(
        f"/api/v1/elm/reviews/sanction/{app.id}/decision",
        data={"decision": "approve", "remarks": "Sanctioned"},
        format="json",
    )
    assert r3.status_code == 200
    app.refresh_from_db()
    assert app.status == ApplicationStatus.APPROVED.value

    # Balance debited upon final sanction
    acc.refresh_from_db()
    assert acc.balance == Decimal("25.00")
    assert acc.availed == Decimal("5.00")


def test_cancellation_workflow_restores_balance(stub_iam):
    """CW-EL-02: Pre-start cancellation restores balance upon approval."""
    acc = LeaveAccount.objects.create(
        user_id=101,
        year=2026,
        category="CL",
        credited=Decimal("8.00"),
        availed=Decimal("2.00"),
        balance=Decimal("6.00"),
    )
    app = LeaveApplication.objects.create(
        user_id=101,
        category="CL",
        start_date=date(2026, 12, 1),  # future start date
        end_date=date(2026, 12, 2),
        chargeable_days=Decimal("2.00"),
        purpose="Seminar",
        status=ApplicationStatus.APPROVED.value,
        unit_head_user_id=505,
    )

    # 1. Applicant requests cancellation
    c_app = _client(stub_iam, user_id=101, permissions=("elm.leave.cancel",))
    r_req = c_app.post(
        f"/api/v1/elm/applications/{app.id}/cancel",
        data={"reason": "Seminar cancelled"},
        format="json",
    )
    assert r_req.status_code == 200
    app.refresh_from_db()
    assert app.status == ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD.value

    # 2. Unit Head approves cancellation
    c_uh = _client(stub_iam, user_id=505, permissions=("elm.review.unit_head",))
    r_uh = c_uh.post(
        f"/api/v1/elm/cancellations/{app.id}/unit-head-review",
        data={"outcome": "approve", "remarks": "Cancellation accepted"},
        format="json",
    )
    assert r_uh.status_code == 200
    app.refresh_from_db()
    assert app.status == ApplicationStatus.CANCELLED.value

    # Balance restored!
    acc.refresh_from_db()
    assert acc.balance == Decimal("8.00")
    assert acc.availed == Decimal("0.00")


def test_admin_offline_leave_entry(stub_iam, user_ref):
    """BR-EL-029: Paper-sanctioned leave recorded directly as Approved without triggering approval."""
    HolidayCalendar.objects.create(year=2026, is_published=True)
    LeaveAccount.objects.create(
        user_id=101,
        year=2026,
        category="CL",
        credited=Decimal("8.00"),
        availed=Decimal("0.00"),
        balance=Decimal("8.00"),
    )

    stub_iam(
        make_session(user_id=999, permissions=("elm.admin.manage",), modules=("elm",)),
        users={101: user_ref(101, name="Staff John", kind="staff")},
    )
    c_admin = APIClient()
    c_admin.credentials(HTTP_AUTHORIZATION="Token test-token")

    payload = {
        "employee_user_id": 101,
        "category": "CL",
        "start_date": "2026-10-12",
        "end_date": "2026-10-13",
        "purpose": "Medical emergency paper sanction",
        "offline_reference_no": "OFFLINE/2026/089",
        "offline_sanction_date": "2026-10-10",
        "offline_sanctioning_authority": "Registrar",
    }
    resp = c_admin.post("/api/v1/elm/admin/offline-leaves", data=payload, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "approved"
    assert data["is_offline_record"] is True
    assert data["offline_reference_no"] == "OFFLINE/2026/089"

    # Balance debited
    acc = LeaveAccount.objects.get(user_id=101, year=2026, category="CL")
    assert acc.balance == Decimal("6.00")
    assert acc.availed == Decimal("2.00")


def test_admin_year_end_and_sla_endpoints(stub_iam):
    """Test administrative year-end and SLA execution endpoints."""
    c_admin = _client(stub_iam, user_id=999, permissions=("elm.admin.manage",))

    # SLA processing
    r_sla = c_admin.post("/api/v1/elm/admin/process-sla")
    assert r_sla.status_code == 200
    assert "reminders_sent" in r_sla.json()

    # Year-end processing
    r_ye = c_admin.post("/api/v1/elm/admin/year-end-process", data={"year": 2026}, format="json")
    assert r_ye.status_code == 201
    assert r_ye.json()["year"] == 2026
