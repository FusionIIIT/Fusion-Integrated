"""Privilege escalation and endpoint permission gating tests."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.iaa.models import ExpenseVoucherRequest, RequestStatus

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def test_unauthenticated_request_fails():
    client = APIClient()
    response = client.get("/api/v1/iaa/requests/")
    assert response.status_code in (401, 403)


def test_missing_module_grant_fails(stub_iam):
    client = _auth_client(
        stub_iam,
        user_id=1001,
        modules=("placement_cell",),
        permissions=("iaa.request.view_self",),
    )
    response = client.get("/api/v1/iaa/requests/")
    assert response.status_code == 403


def test_missing_permission_on_create_fails(stub_iam):
    client = _auth_client(
        stub_iam,
        user_id=1001,
        modules=("iaa",),
        permissions=("iaa.request.view_self",),
    )
    payload = {
        "department": "CSE",
        "request_type": "expense",
        "title": "Books",
        "items": [{"description": "Algorithms", "amount": "100.00"}],
    }
    response = client.post("/api/v1/iaa/requests/", payload, format="json")
    assert response.status_code == 403


def test_create_succeeds_with_proper_permission(stub_iam):
    client = _auth_client(
        stub_iam,
        user_id=1001,
        modules=("iaa",),
        permissions=("iaa.request.view_self", "iaa.request.create"),
    )
    payload = {
        "department": "CSE",
        "request_type": "expense",
        "title": "Lab Monitors",
        "items": [{"description": "Monitor", "amount": "5000.00"}],
    }
    response = client.post("/api/v1/iaa/requests/", payload, format="json")
    assert response.status_code == 201
    assert response.json()["title"] == "Lab Monitors"


def test_approval_decision_requires_approval_permission(stub_iam):
    req = ExpenseVoucherRequest.objects.create(
        user_id=2002,
        department="CSE",
        request_type="expense",
        title="Hardware",
        total_amount=Decimal("1000.00"),
        status=RequestStatus.FINANCE_VALIDATED,
    )
    client = _auth_client(
        stub_iam,
        user_id=1001,
        modules=("iaa",),
        permissions=("iaa.request.view_self",),
    )
    payload = {
        "decision": "approve",
        "remarks": "Approved",
    }
    response = client.post(f"/api/v1/iaa/requests/{req.id}/decide/", payload, format="json")
    assert response.status_code == 403


def test_out_of_scope_record_returns_404_not_403(stub_iam):
    req = ExpenseVoucherRequest.objects.create(
        user_id=2002,
        department="CSE",
        request_type="expense",
        title="Confidential Item",
        total_amount=Decimal("1000.00"),
        status=RequestStatus.SUBMITTED,
    )
    client = _auth_client(
        stub_iam,
        user_id=1001,
        modules=("iaa",),
        permissions=("iaa.request.view_self",),
    )
    response = client.get(f"/api/v1/iaa/requests/{req.id}/")
    assert response.status_code == 404
