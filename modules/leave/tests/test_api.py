"""API endpoint tests for Leave Management."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeavePolicyConfig,
    SubstituteRequest,
)


def _client_for(
    stub_iam,
    user_id=1,
    permissions=(),
    kind="staff",
    roles=("staff",),
    users=None,
):
    stub_iam(
        session=make_session(
            user_id=user_id,
            permissions=permissions,
            modules=("leave",),
            kind=kind,
            roles=roles,
            active_role=roles[0],
        ),
        users=users,
    )
    api_client = APIClient()
    api_client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return api_client


@pytest.fixture
def client(stub_iam):
    return _client_for(
        stub_iam,
        user_id=1,
        permissions=(
            "leave.application.view_self",
            "leave.application.create",
            "leave.application.withdraw",
            "leave.application.cancel",
            "leave.application.extend",
            "leave.application.resume",
        ),
    )


@pytest.mark.django_db
def test_balances_endpoint(client):
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    resp = client.get("/api/v1/leave/balances/?year=2026")
    assert resp.status_code == 200
    assert "balance" in resp.data
    assert resp.data["balance"]["cl_balance"] == "8.0"


@pytest.mark.django_db
def test_apply_leave_endpoint(client):
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    LeavePolicyConfig.objects.create(
        key="route.CL",
        value={"unit_head_user_id": 201},
    )
    payload = {
        "category": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "purpose": "Personal errand",
        "half_day_type": "full",
    }
    resp = client.post("/api/v1/leave/applications/", data=payload, format="json")
    assert resp.status_code == 201
    assert resp.data["category"] == "CL"
    assert resp.data["days_count"] == "2.0"


@pytest.mark.django_db
def test_application_detail_and_withdraw_endpoint(client):
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    LeavePolicyConfig.objects.create(
        key="route.CL",
        value={"unit_head_user_id": 201},
    )
    payload = {
        "category": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "purpose": "Personal errand",
    }
    create_resp = client.post("/api/v1/leave/applications/", data=payload, format="json")
    app_id = create_resp.data["id"]

    # Detail GET
    detail_resp = client.get(f"/api/v1/leave/applications/{app_id}/")
    assert detail_resp.status_code == 200
    assert detail_resp.data["status"] == "under_review"

    # Withdraw DELETE
    del_resp = client.delete(f"/api/v1/leave/applications/{app_id}/?reason=Plans+changed")
    assert del_resp.status_code == 200
    assert del_resp.data["status"] == "withdrawn"


@pytest.mark.django_db
def test_export_and_printable_endpoints(client):
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    LeavePolicyConfig.objects.create(
        key="route.CL",
        value={"unit_head_user_id": 201},
    )
    payload = {
        "category": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "purpose": "Official errand",
    }
    create_resp = client.post("/api/v1/leave/applications/", data=payload, format="json")
    app_id = create_resp.data["id"]

    # Export CSV
    export_resp = client.get(f"/api/v1/leave/applications/{app_id}/export/")
    assert export_resp.status_code == 200
    assert export_resp["Content-Type"].startswith("text/csv")
    assert f"id,{app_id}" in export_resp.content.decode("utf-8")

    # Printable HTML
    print_resp = client.get(f"/api/v1/leave/applications/{app_id}/print/")
    assert print_resp.status_code == 200
    assert print_resp["Content-Type"].startswith("text/html")
    assert "Employee Leave Application" in print_resp.content.decode("utf-8")


@pytest.mark.django_db
def test_substitute_response_and_renominate_flow(stub_iam, user_ref):
    applicant_id = 1
    substitute_id = 2
    new_substitute_id = 3

    users_dict = {
        applicant_id: user_ref(applicant_id, kind="staff"),
        substitute_id: user_ref(substitute_id, kind="staff"),
        new_substitute_id: user_ref(new_substitute_id, kind="faculty"),
    }

    LeaveBalance.objects.create(user_id=applicant_id, year=2026, el_balance=Decimal("30.0"))
    LeavePolicyConfig.objects.create(
        key="route.EL",
        value={"unit_head_user_id": 201, "sanctioning_authority_user_id": 301},
    )

    app_client = _client_for(
        stub_iam,
        user_id=applicant_id,
        permissions=(
            "leave.application.view_self",
            "leave.application.create",
            "leave.substitute.respond",
        ),
        users=users_dict,
    )
    apply_payload = {
        "category": "EL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-06",
        "purpose": "Vacation",
        "substitute_user_id": substitute_id,
        "responsibilities": "Desk coverage",
    }
    res = app_client.post("/api/v1/leave/applications/", data=apply_payload, format="json")
    assert res.status_code == 201
    app_id = res.data["id"]
    sub_req = SubstituteRequest.objects.get(application_id=app_id)

    # Substitute declines
    sub_client = _client_for(
        stub_iam,
        user_id=substitute_id,
        permissions=("leave.substitute.respond",),
        users=users_dict,
    )
    decl_resp = sub_client.post(
        f"/api/v1/leave/substitutes/{sub_req.pk}/respond/",
        data={"decision": "declined", "remarks": "Unavailable"},
        format="json",
    )
    assert decl_resp.status_code == 200
    assert decl_resp.data["status"] == "declined"

    app = LeaveApplication.objects.get(pk=app_id)
    assert app.status == "applicant_action_required"

    # Applicant renominates
    _client_for(
        stub_iam,
        user_id=applicant_id,
        permissions=(
            "leave.application.view_self",
            "leave.application.create",
            "leave.substitute.respond",
        ),
        users=users_dict,
    )
    renom_resp = app_client.post(
        f"/api/v1/leave/applications/{app_id}/renominate-substitute/",
        data={"substitute_user_id": new_substitute_id, "responsibilities": "Take over"},
        format="json",
    )
    assert renom_resp.status_code == 200
    assert renom_resp.data["substitute_user_id"] == new_substitute_id

    app.refresh_from_db()
    assert app.status == "substitute_pending"


@pytest.mark.django_db
def test_unit_head_review_and_assignment_authorization(stub_iam):
    applicant_id = 1
    unit_head_id = 201
    other_user_id = 999

    LeaveBalance.objects.create(user_id=applicant_id, year=2026, cl_balance=Decimal("8.0"))
    LeavePolicyConfig.objects.create(
        key="route.CL",
        value={"unit_head_user_id": unit_head_id},
    )

    app_client = _client_for(
        stub_iam,
        user_id=applicant_id,
        permissions=("leave.application.create", "leave.application.view_self"),
    )
    res = app_client.post(
        "/api/v1/leave/applications/",
        data={
            "category": "CL",
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "purpose": "Appointment",
        },
        format="json",
    )
    app_id = res.data["id"]

    # Other reviewer (not assigned as unit_head_user_id) attempts review -> 403 PermissionDenied
    unassigned_client = _client_for(
        stub_iam,
        user_id=other_user_id,
        permissions=("leave.application.review",),
    )
    unassigned_resp = unassigned_client.post(
        f"/api/v1/leave/approvals/{app_id}/unit-head-review/",
        data={"recommended": True, "remarks": "Unauthorized review"},
        format="json",
    )
    assert unassigned_resp.status_code == 403

    # Assigned unit head reviews -> 200 OK (CL is finalized by Unit Head)
    assigned_client = _client_for(
        stub_iam,
        user_id=unit_head_id,
        permissions=("leave.application.review",),
    )
    review_resp = assigned_client.post(
        f"/api/v1/leave/approvals/{app_id}/unit-head-review/",
        data={"recommended": True, "remarks": "Approved by HOD"},
        format="json",
    )
    assert review_resp.status_code == 200
    assert review_resp.data["status"] == "approved"


@pytest.mark.django_db
def test_higher_sanction_approval_pipeline_via_api(stub_iam):
    applicant_id = 1
    unit_head_id = 201
    establishment_id = 202
    sanctioner_id = 301

    LeaveBalance.objects.create(user_id=applicant_id, year=2026, el_balance=Decimal("30.0"))
    LeavePolicyConfig.objects.create(
        key="route.EL",
        value={
            "unit_head_user_id": unit_head_id,
            "establishment_user_id": establishment_id,
            "sanctioning_authority_user_id": sanctioner_id,
        },
    )

    app_client = _client_for(
        stub_iam,
        user_id=applicant_id,
        permissions=("leave.application.create", "leave.application.view_self"),
    )
    res = app_client.post(
        "/api/v1/leave/applications/",
        data={
            "category": "EL",
            "start_date": "2026-11-02",
            "end_date": "2026-11-06",
            "purpose": "Personal EL",
        },
        format="json",
    )
    app_id = res.data["id"]

    # Sanctioner attempts to sanction before Unit Head review -> 403 PermissionDenied
    sanctioner_client = _client_for(
        stub_iam,
        user_id=sanctioner_id,
        permissions=("leave.application.sanction",),
    )
    premature_resp = sanctioner_client.post(
        f"/api/v1/leave/approvals/{app_id}/sanction/",
        data={"decision": "approved", "remarks": "Too early"},
        format="json",
    )
    assert premature_resp.status_code == 403

    # Step 1: Unit Head reviews and recommends
    uh_client = _client_for(
        stub_iam,
        user_id=unit_head_id,
        permissions=("leave.application.review",),
    )
    uh_resp = uh_client.post(
        f"/api/v1/leave/approvals/{app_id}/unit-head-review/",
        data={"recommended": True, "remarks": "Forwarded to Estt"},
        format="json",
    )
    assert uh_resp.status_code == 200
    assert uh_resp.data["status"] == "under_review"

    # Step 2: Establishment forwards to Sanctioning Authority
    estt_client = _client_for(
        stub_iam,
        user_id=establishment_id,
        permissions=("leave.application.review",),
    )
    estt_resp = estt_client.post(
        f"/api/v1/leave/approvals/{app_id}/forward/",
        data={"remarks": "Verified service records"},
        format="json",
    )
    assert estt_resp.status_code == 200

    # Step 3: Sanctioning authority approves (switch active session to sanctioner_id)
    _client_for(
        stub_iam,
        user_id=sanctioner_id,
        permissions=("leave.application.sanction",),
    )
    sanction_resp = sanctioner_client.post(
        f"/api/v1/leave/approvals/{app_id}/sanction/",
        data={"decision": "approved", "remarks": "Sanctioned by Dean"},
        format="json",
    )
    assert sanction_resp.status_code == 200
    assert sanction_resp.data["status"] == "approved"


@pytest.mark.django_db
def test_calendar_and_holiday_endpoints(stub_iam):
    calendar_viewer = _client_for(
        stub_iam,
        user_id=1,
        permissions=("leave.calendar.view",),
    )
    HolidayCalendar.objects.create(
        date=date(2026, 1, 26),
        name="Republic Day",
        kind="closed",
        year=2026,
        is_published=True,
    )
    resp = calendar_viewer.get("/api/v1/leave/calendar/?year=2026")
    assert resp.status_code == 200
    assert len(resp.data["holidays"]) == 1
    assert resp.data["holidays"][0]["name"] == "Republic Day"


@pytest.mark.django_db
def test_permission_denied_without_required_permission(stub_iam):
    # User has module grant but no specific leave permissions
    unauthorized_client = _client_for(
        stub_iam,
        user_id=1,
        permissions=(),
    )
    resp = unauthorized_client.get("/api/v1/leave/balances/?year=2026")
    assert resp.status_code == 403
