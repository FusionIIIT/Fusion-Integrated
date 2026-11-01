from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from modules.iwd.models import Complaint, Estimate, InventoryItem, BillAndSettlement, ComplaintStatus, EstimateStatus


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_complaint_lifecycle(api_client):
    # Submit complaint
    res = api_client.post(
        "/api/v1/iwd/complaints/",
        {
            "title": "Broken Switchboard in Lab 201",
            "description": "Switchboard sparking",
            "category": "ELECTRICAL",
            "location": "Core Lab 201",
            "complainant_user_id": "emp_01",
        },
        format="json",
    )
    assert res.status_code == 201
    complaint_id = res.data["id"]
    assert res.data["status"] == ComplaintStatus.ASSIGNED

    # Engineer assessment
    res = api_client.post(f"/api/v1/iwd/complaints/{complaint_id}/assess/", {"assessment_notes": "Wiring needs replacement"}, format="json")
    assert res.status_code == 200

    # Engineer submits low-cost estimate
    res = api_client.post(
        "/api/v1/iwd/estimates/",
        {
            "complaint": complaint_id,
            "engineer_id": "eng_default_01",
            "total_cost": "15000.00",
        },
        format="json",
    )
    assert res.status_code == 201
    estimate_id = res.data["id"]
    assert res.data["cost_band"] == "LOW"
    assert res.data["status"] == EstimateStatus.LOW_COST_PENDING

    # Low-cost approve
    res = api_client.post(f"/api/v1/iwd/estimates/{estimate_id}/approve/", {"approved_by": "iwd_admin"}, format="json")
    assert res.status_code == 200
    assert res.data["status"] == "approved"

    # Material issue
    item = InventoryItem.objects.create(name="Copper Wire", quantity_in_stock=100)
    res = api_client.post(
        f"/api/v1/iwd/inventory/{item.id}/issue/",
        {"quantity": 10, "complaint_id": complaint_id, "recorded_by": "iwd_admin"},
        format="json",
    )
    assert res.status_code == 200
    assert res.data["remaining_stock"] == 90

    # Verification passed
    res = api_client.post(
        "/api/v1/iwd/verifications/",
        {
            "complaint": complaint_id,
            "verified_by": "dept_head_01",
            "passed": True,
            "remarks": "Completed satisfactorily",
        },
        format="json",
    )
    assert res.status_code == 201

    complaint = Complaint.objects.get(pk=complaint_id)
    assert complaint.status == ComplaintStatus.RESOLVED

    # Feedback submitted
    res = api_client.post(
        "/api/v1/iwd/feedback/",
        {
            "complaint": complaint_id,
            "user_id": "emp_01",
            "rating": 5,
            "comments": "Quick repair, thank you!",
        },
        format="json",
    )
    assert res.status_code == 201

