"""Integration tests for ELM REST API endpoints."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.domain.state_machine import LeaveStatus, SubstituteStatus
from modules.elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    VacationCalendar,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clean_tables():
    LeaveApplication.objects.all().delete()
    LeaveBalance.objects.all().delete()
    HolidayCalendar.objects.all().delete()
    VacationCalendar.objects.all().delete()


def as_user(stub_iam, *, user_id, kind="faculty", roles=(), permissions=()):
    active_role = roles[0] if roles else ("faculty" if kind == "faculty" else "staff")
    session = make_session(
        user_id=user_id,
        kind=kind,
        roles=roles,
        active_role=active_role,
        modules=("elm",),
        permissions=permissions,
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def test_apply_leave_via_api(stub_iam):
    c = as_user(
        stub_iam,
        user_id=101,
        kind="faculty",
        permissions=("elm.application.create", "elm.application.view_self"),
    )
    payload = {
        "category": "cl",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "half": "full",
        "purpose": "Personal errand",
        "department": "CSE",
    }
    resp = c.post("/api/v1/leave/applications", payload, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "cl"
    assert data["status"] == LeaveStatus.SUBMITTED.value
    assert data["chargeable_days"] == "2.0"
    assert data["user_id"] == 101


def test_my_balances_api(stub_iam):
    c = as_user(
        stub_iam,
        user_id=101,
        kind="faculty",
        permissions=(
            "elm.application.create",
            "elm.application.view_self",
            "elm.balance.view_self",
        ),
    )
    # Apply to trigger initial balance creation
    c.post(
        "/api/v1/leave/applications",
        {
            "category": "cl",
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "half": "first_half",
            "purpose": "Doctor appointment",
        },
        format="json",
    )
    resp = c.get("/api/v1/leave/balances?year=2026")
    assert resp.status_code == 200
    results = resp.json()["results"]
    bals = {b["category"]: b for b in results}
    assert "cl" in bals
    assert Decimal(bals["cl"]["entitled"]) == Decimal("8.0")
    assert Decimal(bals["cl"]["available"]) == Decimal("8.0")


def test_substitute_workflow_api(stub_iam):
    # Applicant 101 applies with substitute 102
    c_applicant = as_user(
        stub_iam,
        user_id=101,
        kind="faculty",
        permissions=("elm.application.create", "elm.application.view_self"),
    )
    payload = {
        "category": "cl",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "half": "full",
        "purpose": "Conference",
        "substitute_user_id": 102,
        "department": "CSE",
    }
    resp = c_applicant.post("/api/v1/leave/applications", payload, format="json")
    assert resp.status_code == 201
    app_id = resp.json()["id"]

    # Substitute 102 checks substitute inbox
    c_sub = as_user(
        stub_iam,
        user_id=102,
        kind="faculty",
        permissions=("elm.substitute.respond",),
    )
    sub_inbox = c_sub.get("/api/v1/leave/substitute-inbox").json()
    assert len(sub_inbox["results"]) == 1
    assert sub_inbox["results"][0]["id"] == app_id

    # Substitute 102 accepts nomination
    resp_act = c_sub.post(
        f"/api/v1/leave/substitute/{app_id}/respond",
        {"accept": True},
        format="json",
    )
    assert resp_act.status_code == 200
    assert resp_act.json()["substitute_status"] == SubstituteStatus.ACCEPTED.value


def test_recommendation_and_approval_workflow_api(stub_iam):
    # Staff 102 applies for EL (requires higher sanction)
    c_applicant = as_user(
        stub_iam,
        user_id=102,
        kind="staff",
        permissions=("elm.application.create", "elm.application.view_self"),
    )
    app = c_applicant.post(
        "/api/v1/leave/applications",
        {
            "category": "el",
            "start_date": "2026-11-02",
            "end_date": "2026-11-05",
            "half": "full",
            "purpose": "Home renovation",
            "department": "Accounts",
        },
        format="json",
    ).json()
    app_id = app["id"]

    # Unit Head (Registrar/HOD) recommends
    c_recommender = as_user(
        stub_iam,
        user_id=201,
        kind="staff",
        roles=("Deputy Registrar",),
        permissions=("elm.application.recommend", "elm.application.view"),
    )
    rec_resp = c_recommender.post(
        f"/api/v1/leave/applications/{app_id}/recommend",
        {"recommended": True, "note": "Duties assigned to junior assistant."},
        format="json",
    )
    assert rec_resp.status_code == 200
    assert rec_resp.json()["status"] == LeaveStatus.FORWARDED.value

    # Sanctioning Authority (Registrar) approves
    c_approver = as_user(
        stub_iam,
        user_id=301,
        kind="staff",
        roles=("Registrar",),
        permissions=("elm.application.decide", "elm.application.view"),
    )
    dec_resp = c_approver.post(
        f"/api/v1/leave/applications/{app_id}/decide",
        {"approve": True, "note": "Sanctioned."},
        format="json",
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == LeaveStatus.APPROVED.value


def test_cancellation_workflow_api(stub_iam):
    c_applicant = as_user(
        stub_iam,
        user_id=101,
        kind="faculty",
        permissions=(
            "elm.application.create",
            "elm.application.view_self",
            "elm.application.cancel",
        ),
    )
    app = c_applicant.post(
        "/api/v1/leave/applications",
        {
            "category": "cl",
            "start_date": "2026-11-10",
            "end_date": "2026-11-11",
            "half": "full",
            "purpose": "Trip",
            "department": "CSE",
        },
        format="json",
    ).json()
    app_id = app["id"]

    # Direct approve by HOD
    c_hod = as_user(
        stub_iam,
        user_id=201,
        roles=("HOD (CSE)",),
        permissions=("elm.application.decide", "elm.application.view"),
    )
    c_hod.post(f"/api/v1/leave/applications/{app_id}/decide", {"approve": True}, format="json")

    # Switch back to applicant to request cancellation before leave start
    c_applicant = as_user(
        stub_iam,
        user_id=101,
        kind="faculty",
        permissions=(
            "elm.application.create",
            "elm.application.view_self",
            "elm.application.cancel",
        ),
    )
    cancel_req = c_applicant.post(
        f"/api/v1/leave/applications/{app_id}/cancel",
        {"reason": "Event cancelled by organizers."},
        format="json",
    )
    assert cancel_req.status_code == 200
    assert cancel_req.json()["status"] == LeaveStatus.CANCELLATION_REQUESTED.value

    # Switch to HOD to decide cancellation
    c_hod = as_user(
        stub_iam,
        user_id=201,
        roles=("HOD (CSE)",),
        permissions=("elm.application.decide", "elm.application.view"),
    )
    dec_cancel = c_hod.post(
        f"/api/v1/leave/applications/{app_id}/decide-cancellation",
        {"approve": True, "note": "Cancellation accepted."},
        format="json",
    )
    assert dec_cancel.status_code == 200
    assert dec_cancel.json()["status"] == LeaveStatus.CANCELLED.value


def test_duty_resumption_api(stub_iam):
    c_applicant = as_user(
        stub_iam,
        user_id=102,
        kind="staff",
        permissions=(
            "elm.application.create",
            "elm.application.view_self",
            "elm.application.resume",
        ),
    )
    app = c_applicant.post(
        "/api/v1/leave/applications",
        {
            "category": "el",
            "start_date": "2026-11-02",
            "end_date": "2026-11-06",  # 5 continuous days
            "half": "full",
            "purpose": "Vacation",
            "department": "Accounts",
        },
        format="json",
    ).json()
    app_id = app["id"]

    # Recommend and approve
    c_admin = as_user(
        stub_iam,
        user_id=300,
        roles=("Registrar",),
        permissions=(
            "elm.application.recommend",
            "elm.application.decide",
            "elm.application.view",
        ),
    )
    c_admin.post(
        f"/api/v1/leave/applications/{app_id}/recommend",
        {"recommended": True},
        format="json",
    )
    c_admin.post(
        f"/api/v1/leave/applications/{app_id}/decide",
        {"approve": True},
        format="json",
    )

    # Applicant reports early resumption (resumes on 2026-11-05 instead of 2026-11-07)
    c_applicant = as_user(
        stub_iam,
        user_id=102,
        kind="staff",
        permissions=(
            "elm.application.create",
            "elm.application.view_self",
            "elm.application.resume",
        ),
    )
    res_resp = c_applicant.post(
        f"/api/v1/leave/applications/{app_id}/resume",
        {"actual_resumption_date": "2026-11-05", "note": "Returned a day early."},
        format="json",
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == LeaveStatus.RESUMPTION_REQUESTED.value

    # Review resumption by Admin
    c_admin = as_user(
        stub_iam,
        user_id=300,
        roles=("Registrar",),
        permissions=(
            "elm.application.recommend",
            "elm.application.decide",
            "elm.application.view",
        ),
    )
    rev_resp = c_admin.post(
        f"/api/v1/leave/applications/{app_id}/review-resumption",
        {"note": "Resumption verified and adjusted."},
        format="json",
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["status"] == LeaveStatus.RESUMED.value
    assert rev_resp.json()["chargeable_days"] == "3.0"


def test_offline_leave_recording_api(stub_iam):
    c_admin = as_user(
        stub_iam,
        user_id=900,
        roles=("Registrar",),
        permissions=("elm.admin.offline", "elm.application.view"),
    )
    payload = {
        "user_id": 101,
        "kind": "faculty",
        "category": "cl",
        "start_date": "2026-10-05",
        "end_date": "2026-10-06",
        "half": "full",
        "purpose": "Medical emergency paper sanction",
        "department": "CSE",
        "sanction_reference": "IIITJ/LEAVE/2026/89",
    }
    resp = c_admin.post("/api/v1/leave/offline", payload, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == LeaveStatus.APPROVED.value
    assert data["is_offline_record"] is True
    assert data["offline_sanction_reference"] == "IIITJ/LEAVE/2026/89"


def test_printable_leave_slip_api(stub_iam):
    c = as_user(
        stub_iam,
        user_id=101,
        kind="faculty",
        permissions=("elm.application.create", "elm.application.view_self"),
    )
    app = c.post(
        "/api/v1/leave/applications",
        {
            "category": "cl",
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "half": "full",
            "purpose": "Official meeting",
            "department": "CSE",
        },
        format="json",
    ).json()
    app_id = app["id"]

    resp = c.get(f"/api/v1/leave/applications/{app_id}/printable")
    assert resp.status_code == 200
    slip = resp.json()
    assert slip["application"]["id"] == app_id
    assert slip["document_title"] == "EMPLOYEE LEAVE APPLICATION SLIP"
    assert "generated_at" in slip
