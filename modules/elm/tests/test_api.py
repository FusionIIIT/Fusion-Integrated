from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveBalance, LeaveEvent, LeaveRequest
from modules.elm.tests.test_submission import pending_context, seed

pytestmark = pytest.mark.django_db


def api_as(stub_iam, user_id, permissions):
    stub_iam(make_session(user_id=user_id, kind="staff", modules=("elm",), permissions=permissions))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_anonymous_requests_are_denied():
    response = APIClient().get("/api/v1/elm/requests/")
    assert response.status_code == 401


def test_api_submission_protects_server_fields(stub_iam):
    leave_type, _applicant = seed()
    client = api_as(stub_iam, 101, ("elm.leave_requests.view", "elm.leave_requests.apply"))
    response = client.post(
        "/api/v1/elm/requests/",
        {
            "leave_type": leave_type.pk,
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "purpose": "Family",
            "employee": 999,
            "status": "APPROVED",
            "route": [999],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["employee"] == 101
    assert response.data["status"] == "PENDING"
    assert response.data["route"] == [201]


def test_api_assigned_authority_approval(stub_iam):
    _client, request_id, leave_type = created_request(stub_iam)
    authority_client = api_as(
        stub_iam, 201, ("elm.leave_requests.view", "elm.leave_requests.approve")
    )
    response = authority_client.post(
        f"/api/v1/elm/requests/{request_id}/decide/", data={"decision": "APPROVE"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["status"] == "APPROVED"
    assert LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026).balance == 7


def test_api_pending_request_cannot_be_patched(stub_iam):
    client, request_id, _leave_type = created_request(stub_iam)
    response = client.patch(
        f"/api/v1/elm/requests/{request_id}/", data={"status": "APPROVED"}, format="json"
    )
    assert response.status_code == 405
    assert LeaveRequest.objects.get(pk=request_id).status == "PENDING"


def created_request(stub_iam):
    leave_type, _applicant = seed()
    client = api_as(stub_iam, 101, ("elm.leave_requests.view", "elm.leave_requests.apply"))
    response = client.post(
        "/api/v1/elm/requests/",
        {
            "leave_type": leave_type.pk,
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "purpose": "Family",
            "employee": 999,
            "status": "APPROVED",
            "route": [999],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return (client, response.data["id"], leave_type)


pytestmark = pytest.mark.django_db


def test_balance_employee_scope_and_write_denial(stub_iam):
    _req, _applicant, _authority, leave_type = pending_context()
    other = LeaveBalance.objects.create(employee=301, leave_type=leave_type, year=2026, balance=5)
    client = api_as(stub_iam, 101, ("elm.leave_balances.view",))

    response = client.get("/api/v1/elm/balances/")
    assert response.status_code == 200
    results = response.data["results"]
    assert len(results) == 1
    assert results[0]["employee"] == 101

    response = client.get(f"/api/v1/elm/balances/{other.pk}/")
    assert response.status_code == 404

    response = client.post(
        "/api/v1/elm/balances/",
        {"employee": 999, "leave_type": leave_type.pk, "balance": 999, "year": 2026},
    )
    assert response.status_code == 405

    response = client.patch(
        f"/api/v1/elm/balances/{LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026).pk}/",
        {"balance": 999},
    )
    assert response.status_code == 405

    response = client.post(
        f"/api/v1/elm/balances/{LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026).pk}/adjust/",
        {"balance": "999", "reason": "x", "evidence": "y"},
    )
    assert response.status_code == 403

    balance = LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026)
    assert balance.balance == Decimal("8")


def test_balance_admin_adjustment_requires_evidence_and_audits_delta(stub_iam):
    _req, _applicant, _authority, leave_type = pending_context()
    row = LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026)
    client = api_as(stub_iam, 201, ("elm.leave_balances.view", "elm.leave_balances.manage"))

    response = client.post(f"/api/v1/elm/balances/{row.pk}/adjust/", {"balance": "6"})
    assert response.status_code == 400

    response = client.post(
        f"/api/v1/elm/balances/{row.pk}/adjust/",
        {
            "balance": "6",
            "reason": "Paper record correction",
            "evidence": "PAPER-42",
            "employee": 999,
        },
    )
    assert response.status_code == 200

    row.refresh_from_db()
    assert row.balance == Decimal("6")
    assert row.employee == 101

    event = LeaveEvent.objects.filter(
        employee=101,
        actor=201,
        action="BALANCE_CORRECTED",
        delta=Decimal("-2"),
        details__evidence="PAPER-42",
    ).exists()
    assert event

    response = client.post(
        f"/api/v1/elm/balances/{row.pk}/adjust/",
        {"balance": "-1", "reason": "Invalid adjustment", "evidence": "INVALID-123"},
    )
    assert response.status_code == 400

    row.refresh_from_db()
    assert row.balance == Decimal("6")


def test_balance_adjustment_accepts_numeric_zero(stub_iam):
    _req, _applicant, _authority, leave_type = pending_context()
    row = LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026)
    client = api_as(stub_iam, 201, ("elm.leave_balances.manage",))
    response = client.post(
        f"/api/v1/elm/balances/{row.pk}/adjust/",
        {"balance": 0, "reason": "Reconciled record", "evidence": "ORDER-ZERO"},
        format="json",
    )
    assert response.status_code == 200
    row.refresh_from_db()
    assert row.balance == Decimal("0")
    assert LeaveEvent.objects.filter(
        employee=101, action="BALANCE_CORRECTED", delta=Decimal("-8")
    ).exists()
