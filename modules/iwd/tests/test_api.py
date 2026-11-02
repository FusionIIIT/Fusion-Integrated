"""API endpoint tests for the IWD module."""
import pytest
from rest_framework.test import APIClient

from modules.iwd.models import Contractor, InventoryItem, WorkRequest, WorkRequestLog


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def work_request(db):
    return WorkRequest.objects.create(
        title="Fix broken window in lab",
        description="Window pane is cracked and needs immediate replacement.",
        location="Computer Lab 2, Block B",
        category="repair",
        priority="high",
        status="draft",
        requester_username="prof_sharma",
        estimated_cost=5000,
    )


@pytest.mark.django_db
def test_create_work_request(api):
    payload = {
        "title": "Repair leaking pipe in hostel",
        "description": "Water pipe is leaking near the washroom of hostel block C.",
        "location": "Hostel Block C, Ground Floor",
        "category": "plumbing",
        "priority": "urgent",
        "estimated_cost": "2500.00",
    }
    resp = api.post("/api/v1/iwd/requests/", payload, format="json",
                    HTTP_X_USER="maintenance_staff")
    assert resp.status_code == 201
    assert resp.data["title"] == payload["title"]
    assert resp.data["status"] == "draft"


@pytest.mark.django_db
def test_list_work_requests(api, work_request):
    resp = api.get("/api/v1/iwd/requests/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1


@pytest.mark.django_db
def test_submit_work_request(api, work_request):
    resp = api.post(f"/api/v1/iwd/requests/{work_request.pk}/submit/",
                    HTTP_X_USER="prof_sharma")
    assert resp.status_code == 200
    assert resp.data["status"] == "submitted"


@pytest.mark.django_db
def test_cannot_skip_to_approved_from_draft(api, work_request):
    resp = api.post(f"/api/v1/iwd/requests/{work_request.pk}/approve/",
                    HTTP_X_USER="supervisor")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_full_workflow_happy_path(api, work_request):
    steps = [
        ("submit", "submitted"),
        ("review", "under_review"),
        ("approve", "approved"),
        ("start", "in_progress"),
        ("complete", "completed"),
        ("close", "closed"),
    ]
    for action, expected_status in steps:
        resp = api.post(f"/api/v1/iwd/requests/{work_request.pk}/{action}/",
                        HTTP_X_USER="supervisor")
        assert resp.status_code == 200, f"Action '{action}' failed: {resp.data}"
        assert resp.data["status"] == expected_status


@pytest.mark.django_db
def test_reject_from_submitted(api, work_request):
    api.post(f"/api/v1/iwd/requests/{work_request.pk}/submit/", HTTP_X_USER="requester")
    resp = api.post(f"/api/v1/iwd/requests/{work_request.pk}/reject/",
                    {"note": "Insufficient budget."}, format="json",
                    HTTP_X_USER="supervisor")
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"


@pytest.mark.django_db
def test_work_request_history_logs(api, work_request):
    api.post(f"/api/v1/iwd/requests/{work_request.pk}/submit/", HTTP_X_USER="prof_sharma")
    resp = api.get(f"/api/v1/iwd/requests/{work_request.pk}/history/")
    assert resp.status_code == 200
    statuses = [log["to_status"] for log in resp.data]
    assert "submitted" in statuses


@pytest.mark.django_db
def test_create_contractor(api):
    payload = {
        "name": "Singh Civil Works",
        "registration_number": "REG-2024-001",
        "contact_person": "Rajinder Singh",
        "phone": "9876543210",
        "email": "singh.civil@example.com",
        "specialization": "Civil and masonry work",
    }
    resp = api.post("/api/v1/iwd/contractors/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == "Singh Civil Works"


@pytest.mark.django_db
def test_list_contractors(api, db):
    Contractor.objects.create(
        name="Patel Electricals", registration_number="REG-2024-002",
        contact_person="Ramesh Patel", phone="9123456780",
        email="patel.elec@example.com",
    )
    resp = api.get("/api/v1/iwd/contractors/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1


@pytest.mark.django_db
def test_create_inventory_item(api):
    payload = {
        "name": "Cement Bags", "unit": "bags",
        "quantity_available": "50.00", "unit_cost": "350.00",
        "minimum_stock": "10.00",
    }
    resp = api.post("/api/v1/iwd/inventory/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == "Cement Bags"


@pytest.mark.django_db
def test_low_stock_endpoint(api, db):
    InventoryItem.objects.create(
        name="Paint Tins", unit="tins",
        quantity_available=2, unit_cost=500, minimum_stock=5,
    )
    resp = api.get("/api/v1/iwd/inventory/low_stock/")
    assert resp.status_code == 200
    names = [i["name"] for i in resp.data]
    assert "Paint Tins" in names
