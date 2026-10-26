"""Security and authorization tests for ELM module."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveApplication, LeaveBalance

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clean_tables():
    LeaveApplication.objects.all().delete()
    LeaveBalance.objects.all().delete()


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


def test_unauthenticated_request_rejected():
    client = APIClient()
    resp = client.get("/api/v1/leave/applications")
    assert resp.status_code == 401


def test_permission_boundaries_for_employee(stub_iam):
    c_emp = as_user(
        stub_iam,
        user_id=101,
        kind="faculty",
        permissions=("elm.application.view_self", "elm.application.create"),
    )
    # Employee cannot access inbox (requires elm.application.decide or recommend)
    resp_inbox = c_emp.get("/api/v1/leave/inbox")
    assert resp_inbox.status_code == 403

    # Employee cannot record offline leave (requires elm.admin.offline)
    resp_offline = c_emp.post(
        "/api/v1/leave/offline",
        {
            "user_id": 101,
            "kind": "faculty",
            "category": "cl",
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "sanction_reference": "ILLEGAL/REF",
        },
        format="json",
    )
    assert resp_offline.status_code == 403


def test_anti_self_approval_and_anti_self_recommendation(stub_iam):
    # User 201 is HOD CSE with elm.application.decide and elm.application.recommend permissions
    c_hod = as_user(
        stub_iam,
        user_id=201,
        roles=("HOD (CSE)",),
        permissions=(
            "elm.application.create",
            "elm.application.view_self",
            "elm.application.recommend",
            "elm.application.decide",
            "elm.application.view",
        ),
    )
    # HOD applies for personal leave
    app = c_hod.post(
        "/api/v1/leave/applications",
        {
            "category": "cl",
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "half": "full",
            "purpose": "Personal work",
            "department": "CSE",
        },
        format="json",
    ).json()
    app_id = app["id"]

    # HOD attempts to approve their own leave -> 409 Conflict (self_decision)
    resp_self_decide = c_hod.post(
        f"/api/v1/leave/applications/{app_id}/decide",
        {"approve": True},
        format="json",
    )
    assert resp_self_decide.status_code == 409
    assert resp_self_decide.json()["error"]["code"] == "self_decision"

    # HOD attempts to recommend their own leave -> 409 Conflict (self_review)
    resp_self_rec = c_hod.post(
        f"/api/v1/leave/applications/{app_id}/recommend",
        {"recommended": True},
        format="json",
    )
    assert resp_self_rec.status_code == 409
    assert resp_self_rec.json()["error"]["code"] == "self_review"


def test_department_isolation_hod_scope(stub_iam):
    # Applicant in ME department applies
    c_me_applicant = as_user(
        stub_iam,
        user_id=105,
        permissions=("elm.application.create", "elm.application.view_self"),
    )
    app = c_me_applicant.post(
        "/api/v1/leave/applications",
        {
            "category": "cl",
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "half": "full",
            "purpose": "ME lab work",
            "department": "ME",
        },
        format="json",
    ).json()
    app_id = app["id"]

    # HOD CSE attempts to decide application of ME applicant
    c_hod_cse = as_user(
        stub_iam,
        user_id=201,
        roles=("HOD (CSE)",),
        permissions=("elm.application.decide", "elm.application.view"),
    )

    # In HOD CSE inbox, ME application should NOT appear
    inbox = c_hod_cse.get("/api/v1/leave/inbox").json()
    inbox_app_ids = [r["id"] for r in inbox["results"]]
    assert app_id not in inbox_app_ids

    # If HOD CSE attempts to approve ME application directly -> 404 Not Found (out of scope)
    resp_decide = c_hod_cse.post(
        f"/api/v1/leave/applications/{app_id}/decide",
        {"approve": True},
        format="json",
    )
    assert resp_decide.status_code == 404
