"""Integration tests for IWD REST API endpoints."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.iwd.domain.state_machine import IWDState
from modules.iwd.models import Complaint

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_complaint_create_and_list(stub_iam):
    """Test complaint creation and listing through REST API."""
    client = _client(
        stub_iam,
        user_id=42,
        active_role="student",
        roles=("student",),
        modules=("iwd",),
        permissions=("iwd.complaint.create", "iwd.complaint.view"),
    )
    res = client.post(
        "/api/v1/iwd/complaints/",
        {
            "category": "Civil",
            "location": "Hostel 3 Room 12",
            "remarks": "Broken latch",
            "urgency": "Low",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["category"] == "Civil"
    assert data["status"] == IWDState.ASSIGNED

    res_list = client.get("/api/v1/iwd/complaints/")
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.json()) >= 1


def test_complaint_detail_and_assess(stub_iam):
    """Test viewing detail and technical assessment of complaint."""
    complaint = Complaint.objects.create(
        requester_user_id=1,
        assigned_engineer_id=101,
        category="Electrical",
        location="Lab 1",
        status=IWDState.ASSIGNED,
    )
    client = _client(
        stub_iam,
        user_id=101,
        active_role="iwd_engineer",
        roles=("iwd_engineer",),
        modules=("iwd",),
        permissions=("iwd.complaint.view", "iwd.complaint.update"),
    )
    res = client.get(f"/api/v1/iwd/complaints/{complaint.id}/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["id"] == complaint.id

    res_assess = client.post(
        f"/api/v1/iwd/complaints/{complaint.id}/assess/",
        {"assessment_details": "Burnt MCB breaker"},
        format="json",
    )
    assert res_assess.status_code == status.HTTP_200_OK
    assert res_assess.json()["status"] == IWDState.ASSESSED


def test_estimate_submit_and_review_low(stub_iam):
    """Test estimate preparation and low-cost approval endpoints."""
    complaint = Complaint.objects.create(
        requester_user_id=1,
        assigned_engineer_id=101,
        category="Civil",
        location="Hostel 1",
        status=IWDState.ASSESSED,
    )
    client_eng = _client(
        stub_iam,
        user_id=101,
        active_role="iwd_engineer",
        roles=("iwd_engineer",),
        modules=("iwd",),
        permissions=("iwd.complaint.view", "iwd.estimate.create"),
    )
    res_est = client_eng.post(
        f"/api/v1/iwd/complaints/{complaint.id}/estimates/",
        {"total_cost": "5000.00", "estimated_time_days": 1, "materials_details": "Cement"},
        format="json",
    )
    assert res_est.status_code == status.HTTP_201_CREATED
    assert res_est.json()["cost_band"] == "LOW"

    # Admin approves low-cost
    client_admin = _client(
        stub_iam,
        user_id=201,
        active_role="iwd_admin",
        roles=("iwd_admin",),
        modules=("iwd",),
        permissions=("iwd.complaint.view", "iwd.estimate.review"),
    )
    res_app = client_admin.post(
        f"/api/v1/iwd/complaints/{complaint.id}/review-low-cost/",
        {"approve": True, "reason": "Approved by admin"},
        format="json",
    )
    assert res_app.status_code == status.HTTP_200_OK


def test_inventory_api(stub_iam):
    """Test inventory item creation and listing endpoints."""
    client = _client(
        stub_iam,
        user_id=201,
        active_role="iwd_admin",
        roles=("iwd_admin",),
        modules=("iwd",),
        permissions=("iwd.complaint.view", "iwd.inventory.manage"),
    )
    res_create = client.post(
        "/api/v1/iwd/inventory/",
        {
            "name": "Copper Wire 2.5mm",
            "category": "Electrical",
            "stock_quantity": 100,
            "unit": "meters",
            "unit_price": "25.00",
        },
        format="json",
    )
    assert res_create.status_code == status.HTTP_201_CREATED

    res_list = client.get("/api/v1/iwd/inventory/")
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.json()) >= 1
