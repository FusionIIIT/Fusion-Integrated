"""
Spec-based tests for IWD module — Functional Requirements strategy.
Student 2 (Ashmi): spec-driven, written from FR_DESIGN.json.
No production code is modified here.
"""
import pytest
from rest_framework.test import APIClient

from modules.iwd.models import Contractor, InventoryItem, WorkRequest, WorkRequestLog


# ---------------------------------------------------------------------------
# TC_FR_01  source_id: CFR-IWD-01 (AFR-IWD-001, AFR-IWD-006)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_01_create_work_request_happy_path():
    """TC_FR_01 | source_id: CFR-IWD-01 (AFR-IWD-001, AFR-IWD-006)
    Verify a valid work request can be created and starts in draft status.
    """
    client = APIClient()
    payload = {
        "title": "Fix broken pipe in hostel block A",
        "description": "Water pipe burst near bathroom causing flooding on ground floor.",
        "location": "Hostel Block A, Ground Floor",
        "category": "plumbing",
        "priority": "urgent",
        "estimated_cost": "5000.00",
    }
    resp = client.post(
        "/api/v1/iwd/requests/",
        payload,
        format="json",
        HTTP_X_USER="student_01",
    )
    assert resp.status_code == 201
    assert resp.data["status"] == "draft"
    assert resp.data["title"] == payload["title"]
    assert resp.data["requester_username"] == "student_01"


# ---------------------------------------------------------------------------
# TC_FR_02  source_id: CFR-IWD-01 (AFR-IWD-002, AFR-IWD-003, AFR-IWD-004)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_02_create_work_request_validation_failure():
    """TC_FR_02 | source_id: CFR-IWD-01 (AFR-IWD-002, AFR-IWD-003, AFR-IWD-004)
    Verify that missing required fields (title, description, location) return 400.
    """
    client = APIClient()
    payload = {
        "category": "repair",
        "priority": "low",
    }
    resp = client.post("/api/v1/iwd/requests/", payload, format="json")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# TC_FR_03  source_id: CFR-IWD-02 (AFR-IWD-008)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_03_submit_work_request():
    """TC_FR_03 | source_id: CFR-IWD-02 (AFR-IWD-008)
    Verify draft work request can be submitted, changing status to submitted.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Replace broken AC unit in faculty room",
        description="Split AC unit in faculty room 201 has stopped cooling completely.",
        location="Faculty Block, Room 201",
        category="electrical",
        priority="high",
        status="draft",
        requester_username="faculty_02",
        estimated_cost=15000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/submit/",
        HTTP_X_USER="faculty_02",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "submitted"


# ---------------------------------------------------------------------------
# TC_FR_04  source_id: CFR-IWD-02 (AFR-IWD-007, AFR-IWD-009)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_04_list_work_requests():
    """TC_FR_04 | source_id: CFR-IWD-02 (AFR-IWD-007, AFR-IWD-009)
    Verify that work requests can be listed and each has required fields.
    """
    client = APIClient()
    WorkRequest.objects.create(
        title="Repair leaking roof in library",
        description="Water seepage through roof during rainy season damages books.",
        location="Central Library, First Floor",
        category="civil",
        priority="high",
        status="submitted",
        requester_username="librarian_02",
        estimated_cost=50000,
    )
    resp = client.get("/api/v1/iwd/requests/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1
    first = resp.data[0]
    assert "id" in first
    assert "title" in first
    assert "status" in first


# ---------------------------------------------------------------------------
# TC_FR_05  source_id: CFR-IWD-03 (AFR-IWD-010, AFR-IWD-013)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_05_review_work_request():
    """TC_FR_05 | source_id: CFR-IWD-03 (AFR-IWD-010, AFR-IWD-013)
    Verify submitted work request can be taken under review.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Repair sports ground boundary wall",
        description="Section of boundary wall collapsed after heavy rain.",
        location="Sports Ground, North Side",
        category="civil",
        priority="medium",
        status="submitted",
        requester_username="sports_officer",
        estimated_cost=30000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/review/",
        HTTP_X_USER="supervisor_01",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "under_review"


# ---------------------------------------------------------------------------
# TC_FR_06  source_id: CFR-IWD-04 (AFR-IWD-014, AFR-IWD-015)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_06_approve_work_request():
    """TC_FR_06 | source_id: CFR-IWD-04 (AFR-IWD-014, AFR-IWD-015)
    Verify work request under review can be approved.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Install new water purifier in canteen",
        description="Old purifier is non-functional; new one required for safe drinking water.",
        location="Main Canteen, Ground Floor",
        category="plumbing",
        priority="high",
        status="under_review",
        requester_username="canteen_manager",
        estimated_cost=12000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/approve/",
        {"assigned_to": "eng_plumbing_1"},
        format="json",
        HTTP_X_USER="director_01",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"


# ---------------------------------------------------------------------------
# TC_FR_07  source_id: CFR-IWD-05 (AFR-IWD-016)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_07_reject_work_request():
    """TC_FR_07 | source_id: CFR-IWD-05 (AFR-IWD-016)
    Verify work request can be rejected from under_review status.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Paint administrative building exterior",
        description="Exterior paint of admin building is peeling off.",
        location="Admin Building, All Floors",
        category="civil",
        priority="low",
        status="under_review",
        requester_username="admin_01",
        estimated_cost=80000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/reject/",
        {"note": "Budget not allocated for current quarter."},
        format="json",
        HTTP_X_USER="director_01",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"


# ---------------------------------------------------------------------------
# TC_FR_08  source_id: CFR-IWD-06 (AFR-IWD-019, AFR-IWD-020)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_08_start_work_in_progress():
    """TC_FR_08 | source_id: CFR-IWD-06 (AFR-IWD-019, AFR-IWD-020)
    Verify approved work request can be started, moving to in_progress.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Repair generator room door",
        description="Generator room door lock is broken; security risk.",
        location="Generator Room, Block D",
        category="carpentry",
        priority="urgent",
        status="approved",
        requester_username="security_01",
        estimated_cost=4000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/start/",
        HTTP_X_USER="eng_carpenter_1",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "in_progress"


# ---------------------------------------------------------------------------
# TC_FR_09  source_id: CFR-IWD-07 (AFR-IWD-022, AFR-IWD-023)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_09_complete_work_request():
    """TC_FR_09 | source_id: CFR-IWD-07 (AFR-IWD-022, AFR-IWD-023)
    Verify in-progress work request can be completed.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Fix projector in seminar hall",
        description="Projector lamp is dead; needs replacement for upcoming seminar.",
        location="Seminar Hall, Block C",
        category="electrical",
        priority="high",
        status="in_progress",
        requester_username="faculty_03",
        estimated_cost=6000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/complete/",
        {"actual_cost": "5800.00", "remarks": "Lamp replaced successfully."},
        format="json",
        HTTP_X_USER="eng_electrical_2",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "completed"


# ---------------------------------------------------------------------------
# TC_FR_10  source_id: CFR-IWD-08 (AFR-IWD-024, AFR-IWD-026)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_10_close_completed_request():
    """TC_FR_10 | source_id: CFR-IWD-08 (AFR-IWD-024, AFR-IWD-026)
    Verify completed work request can be closed.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Replace roof fan in classroom",
        description="Ceiling fan motor burnt; replaced by maintenance team.",
        location="Classroom 102, Block B",
        category="electrical",
        priority="medium",
        status="completed",
        requester_username="faculty_04",
        estimated_cost=2500,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/close/",
        HTTP_X_USER="supervisor_01",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "closed"


# ---------------------------------------------------------------------------
# TC_FR_11  source_id: CFR-IWD-09 (AFR-IWD-027, AFR-IWD-028)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_11_put_on_hold():
    """TC_FR_11 | source_id: CFR-IWD-09 (AFR-IWD-027, AFR-IWD-028)
    Verify in-progress work request can be put on hold.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Repair swimming pool filtration system",
        description="Pool filter is malfunctioning; water quality degraded.",
        location="Swimming Pool, Sports Complex",
        category="plumbing",
        priority="medium",
        status="in_progress",
        requester_username="sports_coach",
        estimated_cost=25000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/hold/",
        {"note": "Waiting for spare parts delivery."},
        format="json",
        HTTP_X_USER="eng_plumbing_2",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "on_hold"


# ---------------------------------------------------------------------------
# TC_FR_12  source_id: CFR-IWD-10 (AFR-IWD-032, AFR-IWD-033)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_12_list_contractors():
    """TC_FR_12 | source_id: CFR-IWD-10 (AFR-IWD-032, AFR-IWD-033)
    Verify contractors can be created and listed.
    """
    client = APIClient()
    Contractor.objects.create(
        name="BuildRight Construction",
        contact_person="Ramesh Kumar",
        phone="9876543210",
        specialization="civil",
    )
    resp = client.get("/api/v1/iwd/contractors/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1


# ---------------------------------------------------------------------------
# TC_FR_13  source_id: CFR-IWD-11 (AFR-IWD-035, AFR-IWD-037)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_13_inventory_item_create_and_list():
    """TC_FR_13 | source_id: CFR-IWD-11 (AFR-IWD-035, AFR-IWD-037)
    Verify inventory items can be created and listed.
    """
    client = APIClient()
    payload = {
        "name": "Portland Cement 50kg",
        "unit": "bags",
        "quantity_available": 100,
        "minimum_stock": 20,
    }
    resp_create = client.post("/api/v1/iwd/inventory/", payload, format="json")
    assert resp_create.status_code == 201
    resp_list = client.get("/api/v1/iwd/inventory/")
    assert resp_list.status_code == 200
    assert len(resp_list.data) >= 1


# ---------------------------------------------------------------------------
# TC_FR_14  source_id: CFR-IWD-12 (AFR-IWD-038, AFR-IWD-039)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_14_work_request_audit_log_accessible():
    """TC_FR_14 | source_id: CFR-IWD-12 (AFR-IWD-038, AFR-IWD-039)
    Verify audit log entries are accessible for a work request.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Fix water pump in hostel block D",
        description="Motor pump is overheating; needs immediate repair.",
        location="Hostel Block D, Pump Room",
        category="plumbing",
        priority="urgent",
        status="draft",
        requester_username="warden_02",
        estimated_cost=10000,
    )
    WorkRequestLog.objects.create(
        work_request=wr,
        from_status="",
        to_status="draft",
        actor_username="warden_02",
        note="Request created.",
    )
    resp = client.get(f"/api/v1/iwd/requests/{wr.pk}/logs/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1


# ---------------------------------------------------------------------------
# TC_FR_15  source_id: CFR-IWD-13 (AFR-IWD-040, AFR-IWD-041)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_15_work_request_detail_retrieve():
    """TC_FR_15 | source_id: CFR-IWD-13 (AFR-IWD-040, AFR-IWD-041)
    Verify individual work request details can be retrieved by ID.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Replace broken windows in lecture hall",
        description="Several windows in lecture hall 101 are cracked.",
        location="Lecture Hall 101, Block A",
        category="civil",
        priority="medium",
        status="draft",
        requester_username="faculty_05",
        estimated_cost=8000,
    )
    resp = client.get(f"/api/v1/iwd/requests/{wr.pk}/")
    assert resp.status_code == 200
    assert resp.data["id"] == wr.pk
    assert resp.data["title"] == wr.title


# ---------------------------------------------------------------------------
# TC_FR_16  source_id: CFR-IWD-16 (AFR-IWD-054, AFR-IWD-056)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_16_invalid_status_transition_refused():
    """TC_FR_16 | source_id: CFR-IWD-16 (AFR-IWD-054, AFR-IWD-056)
    Verify illegal status transition is refused with an error response.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Fix broken bench in amphitheater",
        description="Wooden bench seating collapsed; hazard to students.",
        location="Amphitheater, Block E",
        category="carpentry",
        priority="medium",
        status="draft",
        requester_username="admin_02",
        estimated_cost=3000,
    )
    # Attempting to approve directly from draft (illegal transition)
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/approve/",
        HTTP_X_USER="director_01",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# TC_FR_17  source_id: CFR-IWD-16 (AFR-IWD-055, AFR-IWD-057)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_fr_17_closed_request_no_further_transitions():
    """TC_FR_17 | source_id: CFR-IWD-16 (AFR-IWD-055, AFR-IWD-057)
    Verify closed work request cannot be transitioned to any other status.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Repaint parking lot lines",
        description="Parking lot lane markings are faded; repaint required.",
        location="Parking Lot, Main Gate",
        category="civil",
        priority="low",
        status="closed",
        requester_username="admin_03",
        estimated_cost=2000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/submit/",
        HTTP_X_USER="admin_03",
    )
    assert resp.status_code == 400
