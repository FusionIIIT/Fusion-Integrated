"""Privilege escalation and role separation tests for IWD (BR-IWD-001, BR-IWD-018)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.iwd.models import Complaint, Estimate

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_dean_cannot_verify_work(stub_iam):
    """Verify Dean role cannot perform Department Head physical verification (BR-IWD-018)."""
    complaint = Complaint.objects.create(
        requester_user_id=1,
        category="Civil",
        location="Hostel 1",
        status="Verification Pending",
    )
    client = _client(
        stub_iam,
        user_id=200,
        active_role="iwd_dean",
        roles=("iwd_dean",),
        modules=("iwd",),
        permissions=("iwd.complaint.view",),
    )
    res = client.post(
        f"/api/v1/iwd/complaints/{complaint.id}/verify/",
        {"verified": True, "remarks": "Dean attempt"},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_dean_cannot_review_estimate(stub_iam):
    """Verify Dean role cannot approve mid-range estimates (BR-IWD-001, BR-IWD-018)."""
    complaint = Complaint.objects.create(
        requester_user_id=1,
        category="Civil",
        location="Hostel 1",
        status="Department Head Review Pending",
    )
    Estimate.objects.create(
        complaint=complaint,
        total_cost=50000,
        cost_band="MID",
        engineer_user_id=10,
    )
    client = _client(
        stub_iam,
        user_id=200,
        active_role="iwd_dean",
        roles=("iwd_dean",),
        modules=("iwd",),
        permissions=("iwd.complaint.view",),
    )
    res = client.post(
        f"/api/v1/iwd/complaints/{complaint.id}/review-mid-range/",
        {"action": "approve", "remarks": "Dean attempt"},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_complainant_cannot_create_estimate(stub_iam):
    """Verify standard requester cannot create repair estimates."""
    complaint = Complaint.objects.create(
        requester_user_id=10,
        category="Civil",
        location="Hostel 1",
        status="Assigned",
    )
    client = _client(
        stub_iam,
        user_id=10,
        active_role="student",
        roles=("student",),
        modules=("iwd",),
        permissions=("iwd.complaint.create", "iwd.complaint.view"),
    )
    res = client.post(
        f"/api/v1/iwd/complaints/{complaint.id}/estimates/",
        {"total_cost": "10000.00", "estimated_time_days": 3, "materials_details": "Cement"},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_engineer_cannot_verify_own_work(stub_iam):
    """Verify engineer cannot verify repair quality without verification permission."""
    complaint = Complaint.objects.create(
        requester_user_id=1,
        assigned_engineer_id=101,
        category="Civil",
        location="Hostel 1",
        status="Verification Pending",
    )
    client = _client(
        stub_iam,
        user_id=101,
        active_role="iwd_engineer",
        roles=("iwd_engineer",),
        modules=("iwd",),
        permissions=(
            "iwd.complaint.view",
            "iwd.complaint.update",
            "iwd.estimate.create",
        ),
    )
    res = client.post(
        f"/api/v1/iwd/complaints/{complaint.id}/verify/",
        {"verified": True, "remarks": "Self verification attempt"},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_regular_user_cannot_issue_stock(stub_iam):
    """Verify regular user cannot issue inventory items."""
    complaint = Complaint.objects.create(
        requester_user_id=1,
        category="Civil",
        location="Hostel 1",
        status="Estimate Approved",
    )
    client = _client(
        stub_iam,
        user_id=1,
        active_role="student",
        roles=("student",),
        modules=("iwd",),
        permissions=("iwd.complaint.view",),
    )
    res = client.post(
        f"/api/v1/iwd/complaints/{complaint.id}/issue-material/",
        {"item_id": 1, "quantity": 5},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
