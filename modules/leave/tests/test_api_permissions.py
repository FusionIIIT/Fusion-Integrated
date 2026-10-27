"""API permission tests exercising real middleware and IAM-grant enforcement."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import LeaveApplication

pytestmark = pytest.mark.django_db


def client_for(stub_iam, *, user_id, permissions):
    stub_iam(
        make_session(
            user_id=user_id, kind="staff", active_role="staff", roles=("staff",),
            modules=("leave",), permissions=permissions,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_create_grant_is_sufficient_for_application_post(stub_iam):
    client = client_for(
        stub_iam, user_id=101, permissions=("leave.application.create",),
    )
    response = client.post("/api/v1/leave/applications", {}, format="json")
    # The deliberately incomplete form should reach validation, not fail as
    # forbidden merely because the employee has no view permission.
    assert response.status_code == 400
    assert client.get("/api/v1/leave/applications").status_code == 403


def test_substitute_can_act_on_explicitly_assigned_request(stub_iam):
    row = LeaveApplication.objects.create(
        applicant_user_id=101, substitute_user_id=202, unit_head_user_id=303,
        leave_type="CL", request_kind="new", start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1), requested_days=Decimal("1"),
        status="awaiting_substitute_response", purpose="Leave",
    )
    client = client_for(
        stub_iam, user_id=202, permissions=("leave.substitute.update",),
    )
    response = client.post(
        f"/api/v1/leave/applications/{row.pk}/action",
        {"event": "accept_substitute"}, format="json",
    )
    assert response.status_code == 200
    row.refresh_from_db()
    assert row.status == "awaiting_unit_head_review"


def test_unassigned_substitute_cannot_view_or_act_on_request(stub_iam):
    row = LeaveApplication.objects.create(
        applicant_user_id=101, substitute_user_id=202, unit_head_user_id=303,
        leave_type="CL", request_kind="new", start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1), requested_days=Decimal("1"),
        status="awaiting_substitute_response", purpose="Leave",
    )
    client = client_for(
        stub_iam, user_id=999, permissions=("leave.substitute.update",),
    )
    response = client.post(
        f"/api/v1/leave/applications/{row.pk}/action",
        {"event": "accept_substitute"}, format="json",
    )
    assert response.status_code == 404
    row.refresh_from_db()
    assert row.status == "awaiting_substitute_response"
