"""
Spec-based tests for IWD module — Use Cases strategy.
Student 2 (Ashmi): spec-driven, written from UC_DESIGN.json.
No production code is modified here.
"""
import pytest
from rest_framework.test import APIClient

from modules.iwd.models import Contractor, InventoryItem, WorkRequest, WorkRequestLog


# ---------------------------------------------------------------------------
# TC_UC_01  source_id: UC-IWD-001 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_01_submit_new_work_request_main_flow():
    """TC_UC_01 | source_id: UC-IWD-001 Main Flow
    Cover the main success flow of submitting a new work request.
    """
    client = APIClient()
    payload = {
        "title": "Fix leaking pipe in hostel bathroom",
        "description": "Water pipe leaking under sink in hostel bathroom block B room 10.",
        "location": "Hostel Block B, Room 10",
        "category": "plumbing",
        "priority": "high",
        "estimated_cost": "3500.00",
    }
    resp = client.post(
        "/api/v1/iwd/requests/",
        payload,
        format="json",
        HTTP_X_USER="student_hostel_01",
    )
    assert resp.status_code == 201
    assert resp.data["status"] == "draft"
    assert resp.data["requester_username"] == "student_hostel_01"


# ---------------------------------------------------------------------------
# TC_UC_02  source_id: UC-IWD-001 Alternative A1 (Validation Error)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_02_submit_work_request_validation_error():
    """TC_UC_02 | source_id: UC-IWD-001 Alternative A1 (Validation Error)
    Verify that invalid/missing required data returns 400 Bad Request.
    """
    client = APIClient()
    # Missing title, description, location
    resp = client.post(
        "/api/v1/iwd/requests/",
        {"category": "civil", "priority": "low"},
        format="json",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# TC_UC_03  source_id: UC-IWD-005 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_03_supervisor_reviews_submitted_request():
    """TC_UC_03 | source_id: UC-IWD-005 Main Flow
    Cover main success flow of supervisor reviewing a submitted request.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Replace broken benches in garden",
        description="Garden benches near the main entrance are broken and unsafe.",
        location="Main Garden, Entrance",
        category="carpentry",
        priority="medium",
        status="submitted",
        requester_username="maintenance_01",
        estimated_cost=8000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/review/",
        HTTP_X_USER="supervisor_02",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "under_review"


# ---------------------------------------------------------------------------
# TC_UC_04  source_id: UC-IWD-015 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_04_director_approves_request():
    """TC_UC_04 | source_id: UC-IWD-015 Main Flow
    Cover main success flow of director approving a work request.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Construct new cycle stand",
        description="New bicycle parking area required near student hostels.",
        location="Hostel Zone, Near Block A",
        category="civil",
        priority="low",
        status="under_review",
        requester_username="student_council",
        estimated_cost=45000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/approve/",
        {"assigned_to": "eng_civil_1"},
        format="json",
        HTTP_X_USER="director_01",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"


# ---------------------------------------------------------------------------
# TC_UC_05  source_id: UC-IWD-021 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_05_engineer_starts_assigned_work():
    """TC_UC_05 | source_id: UC-IWD-021 Main Flow
    Cover main success flow of engineer starting work on an approved request.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Fix water supply pipeline block C",
        description="Main supply pipe cracked near block C junction.",
        location="Block C, Water Junction",
        category="plumbing",
        priority="urgent",
        status="approved",
        requester_username="facility_mgr",
        estimated_cost=20000,
        assigned_to="eng_plumbing_3",
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/start/",
        HTTP_X_USER="eng_plumbing_3",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "in_progress"


# ---------------------------------------------------------------------------
# TC_UC_06  source_id: UC-IWD-025 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_06_engineer_completes_work():
    """TC_UC_06 | source_id: UC-IWD-025 Main Flow
    Cover main success flow of engineer marking work as completed.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Replace streetlights in campus",
        description="Multiple streetlights in campus are non-functional.",
        location="Campus Main Road",
        category="electrical",
        priority="high",
        status="in_progress",
        requester_username="security_head",
        estimated_cost=35000,
        assigned_to="eng_electrical_3",
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/complete/",
        {"actual_cost": "32000.00", "remarks": "All streetlights replaced successfully."},
        format="json",
        HTTP_X_USER="eng_electrical_3",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "completed"


# ---------------------------------------------------------------------------
# TC_UC_07  source_id: UC-IWD-031 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_07_supervisor_closes_completed_request():
    """TC_UC_07 | source_id: UC-IWD-031 Main Flow
    Cover main success flow of supervisor closing a completed work request.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Repair basketball court surface",
        description="Basketball court surface has cracks and needs resurfacing.",
        location="Sports Complex, Court 1",
        category="civil",
        priority="medium",
        status="completed",
        requester_username="sports_officer_01",
        estimated_cost=90000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/close/",
        HTTP_X_USER="supervisor_03",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "closed"


# ---------------------------------------------------------------------------
# TC_UC_08  source_id: UC-IWD-031 Alternative A1 (Rejection)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_08_director_rejects_under_review_request():
    """TC_UC_08 | source_id: UC-IWD-031 Alternative A1 (Rejection)
    Cover the rejection alternative flow: director rejects a request under review.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Install solar panels on hostel rooftop",
        description="Proposal to install solar panels on hostel block A rooftop.",
        location="Hostel Block A, Rooftop",
        category="electrical",
        priority="low",
        status="under_review",
        requester_username="eco_committee",
        estimated_cost=500000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/reject/",
        {"note": "Requires capital budget approval; defer to next fiscal year."},
        format="json",
        HTTP_X_USER="director_01",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"


# ---------------------------------------------------------------------------
# TC_UC_09  source_id: UC-IWD-061 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_09_hold_in_progress_request():
    """TC_UC_09 | source_id: UC-IWD-061 Main Flow
    Cover main success flow of placing in-progress work on hold.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Repair CCTV cameras in library",
        description="Several CCTV cameras in library are offline.",
        location="Central Library, All Floors",
        category="electrical",
        priority="medium",
        status="in_progress",
        requester_username="security_02",
        estimated_cost=18000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/hold/",
        {"note": "Waiting for CCTV module delivery from vendor."},
        format="json",
        HTTP_X_USER="eng_electrical_4",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "on_hold"


# ---------------------------------------------------------------------------
# TC_UC_10  source_id: UC-IWD-071 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_10_resume_from_hold():
    """TC_UC_10 | source_id: UC-IWD-071 Main Flow
    Cover main success flow of resuming work from on-hold status.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Repair auditorium stage lighting",
        description="Stage lighting system in auditorium is partially functional.",
        location="Auditorium, Main Stage",
        category="electrical",
        priority="high",
        status="on_hold",
        requester_username="cultural_dept",
        estimated_cost=40000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/start/",
        HTTP_X_USER="eng_electrical_5",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "in_progress"


# ---------------------------------------------------------------------------
# TC_UC_11  source_id: UC-IWD-081 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_11_add_contractor():
    """TC_UC_11 | source_id: UC-IWD-081 Main Flow
    Cover main success flow of adding a contractor to the system.
    """
    client = APIClient()
    payload = {
        "name": "Elite Electrical Works",
        "contact_person": "Suresh Sharma",
        "phone": "9876543211",
        "specialization": "electrical",
    }
    resp = client.post("/api/v1/iwd/contractors/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == payload["name"]


# ---------------------------------------------------------------------------
# TC_UC_12  source_id: UC-IWD-091 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_12_add_inventory_item():
    """TC_UC_12 | source_id: UC-IWD-091 Main Flow
    Cover main success flow of adding an inventory item.
    """
    client = APIClient()
    payload = {
        "name": "GI Pipe 3/4 inch",
        "unit": "meters",
        "quantity_available": 50,
        "minimum_stock": 10,
    }
    resp = client.post("/api/v1/iwd/inventory/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == payload["name"]


# ---------------------------------------------------------------------------
# TC_UC_13  source_id: UC-IWD-101 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_13_view_work_request_logs():
    """TC_UC_13 | source_id: UC-IWD-101 Main Flow
    Cover main success flow of viewing audit logs for a work request.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Repair chemistry lab exhaust fan",
        description="Exhaust fan in chem lab is non-functional; safety hazard.",
        location="Chemistry Lab, Block F",
        category="electrical",
        priority="urgent",
        status="submitted",
        requester_username="chem_faculty",
        estimated_cost=5000,
    )
    WorkRequestLog.objects.create(
        work_request=wr,
        from_status="draft",
        to_status="submitted",
        actor_username="chem_faculty",
        note="Submitted for review.",
    )
    resp = client.get(f"/api/v1/iwd/requests/{wr.pk}/logs/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1


# ---------------------------------------------------------------------------
# TC_UC_14  source_id: UC-IWD-111 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_14_view_low_stock_inventory():
    """TC_UC_14 | source_id: UC-IWD-111 Main Flow
    Cover main success flow of viewing inventory items with low stock.
    """
    client = APIClient()
    InventoryItem.objects.create(
        name="Welding Rods",
        unit="kg",
        quantity_available=2,
        minimum_stock=5,
    )
    InventoryItem.objects.create(
        name="Copper Wire 1.5mm",
        unit="meters",
        quantity_available=200,
        minimum_stock=50,
    )
    resp = client.get("/api/v1/iwd/inventory/")
    assert resp.status_code == 200
    items = resp.data
    low_stock = [i for i in items if i.get("is_low_stock") is True]
    assert len(low_stock) >= 1


# ---------------------------------------------------------------------------
# TC_UC_15  source_id: UC-IWD-151 Main Flow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_uc_15_work_request_full_lifecycle():
    """TC_UC_15 | source_id: UC-IWD-151 Main Flow
    Cover the complete lifecycle from draft to closed in one integration flow.
    """
    client = APIClient()
    # Create
    payload = {
        "title": "Repair damaged road inside campus",
        "description": "Several potholes on internal campus road pose accident risk.",
        "location": "Internal Campus Road, Near Canteen",
        "category": "civil",
        "priority": "high",
        "estimated_cost": "75000.00",
    }
    resp = client.post(
        "/api/v1/iwd/requests/",
        payload,
        format="json",
        HTTP_X_USER="safety_officer",
    )
    assert resp.status_code == 201
    pk = resp.data["id"]

    # Submit
    resp = client.post(f"/api/v1/iwd/requests/{pk}/submit/", HTTP_X_USER="safety_officer")
    assert resp.data["status"] == "submitted"

    # Review
    resp = client.post(f"/api/v1/iwd/requests/{pk}/review/", HTTP_X_USER="supervisor_04")
    assert resp.data["status"] == "under_review"

    # Approve
    resp = client.post(
        f"/api/v1/iwd/requests/{pk}/approve/",
        {"assigned_to": "eng_civil_2"},
        format="json",
        HTTP_X_USER="director_01",
    )
    assert resp.data["status"] == "approved"

    # Start
    resp = client.post(f"/api/v1/iwd/requests/{pk}/start/", HTTP_X_USER="eng_civil_2")
    assert resp.data["status"] == "in_progress"

    # Complete
    resp = client.post(
        f"/api/v1/iwd/requests/{pk}/complete/",
        {"actual_cost": "72000.00"},
        format="json",
        HTTP_X_USER="eng_civil_2",
    )
    assert resp.data["status"] == "completed"

    # Close
    resp = client.post(f"/api/v1/iwd/requests/{pk}/close/", HTTP_X_USER="supervisor_04")
    assert resp.data["status"] == "closed"
