"""
Spec-based tests for IWD module — Workflow strategy.
Student 2 (Ashmi): spec-driven, written from WF_DESIGN.json.
No production code is modified here.
"""
import pytest
from rest_framework.test import APIClient

from modules.iwd.domain.rules import RequestStatus, can_transition
from modules.iwd.models import InventoryItem, WorkRequest, WorkRequestLog


# ---------------------------------------------------------------------------
# TC_WF_01  source_id: BW-IWD-01 - Complaint Intake and Assessment Path
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_01_complaint_intake_to_submission():
    """TC_WF_01 | source_id: BW-IWD-01 - Complaint Intake and Assessment Path
    Verify complaint intake path: create work request (draft) then submit.
    """
    client = APIClient()
    payload = {
        "title": "Flooding in basement parking",
        "description": "Rain water flooding in basement parking area; drainage blocked.",
        "location": "Basement Parking, Block A",
        "category": "civil",
        "priority": "urgent",
        "estimated_cost": "15000.00",
    }
    resp_create = client.post(
        "/api/v1/iwd/requests/",
        payload,
        format="json",
        HTTP_X_USER="security_guard_01",
    )
    assert resp_create.status_code == 201
    pk = resp_create.data["id"]
    assert resp_create.data["status"] == "draft"

    resp_submit = client.post(
        f"/api/v1/iwd/requests/{pk}/submit/",
        HTTP_X_USER="security_guard_01",
    )
    assert resp_submit.status_code == 200
    assert resp_submit.data["status"] == "submitted"


# ---------------------------------------------------------------------------
# TC_WF_02  source_id: BW-IWD-02 - Low-Cost Estimate Approval Path
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_02_low_cost_estimate_approval_path():
    """TC_WF_02 | source_id: BW-IWD-02 - Low-Cost Estimate Approval Path
    Verify full workflow for low-cost estimate: submitted -> review -> approve -> in_progress.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Replace broken door lock in office",
        description="Office room 105 door lock broken; needs replacement.",
        location="Admin Block, Office 105",
        category="carpentry",
        priority="medium",
        status="submitted",
        requester_username="admin_staff_01",
        estimated_cost=1200,
    )
    resp_review = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/review/",
        HTTP_X_USER="supervisor_05",
    )
    assert resp_review.data["status"] == "under_review"

    resp_approve = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/approve/",
        {"assigned_to": "eng_carpenter_2"},
        format="json",
        HTTP_X_USER="supervisor_05",
    )
    assert resp_approve.data["status"] == "approved"

    resp_start = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/start/",
        HTTP_X_USER="eng_carpenter_2",
    )
    assert resp_start.data["status"] == "in_progress"


# ---------------------------------------------------------------------------
# TC_WF_03  source_id: BW-IWD-02 / BW-IWD-12 - Rejected Low-Cost Estimate Path
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_03_low_cost_rejected_path():
    """TC_WF_03 | source_id: BW-IWD-02 / BW-IWD-12 - Rejected Low-Cost Estimate Path
    Verify rejection path: submitted -> review -> rejected.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Install additional shelving in storeroom",
        description="Need extra shelves in ground floor storeroom.",
        location="Ground Floor Storeroom, Block B",
        category="carpentry",
        priority="low",
        status="submitted",
        requester_username="store_keeper",
        estimated_cost=5000,
    )
    resp_review = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/review/",
        HTTP_X_USER="supervisor_06",
    )
    assert resp_review.data["status"] == "under_review"

    resp_reject = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/reject/",
        {"note": "Space audit required first; rejected pending assessment."},
        format="json",
        HTTP_X_USER="supervisor_06",
    )
    assert resp_reject.data["status"] == "rejected"


# ---------------------------------------------------------------------------
# TC_WF_04  source_id: BW-IWD-03 / BW-IWD-04 - Hold for Review Path
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_04_work_placed_on_hold():
    """TC_WF_04 | source_id: BW-IWD-03 / BW-IWD-04 - Hold for Review Path
    Verify in-progress work can be placed on hold when issue arises.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Roof waterproofing in mechanical workshop",
        description="Workshop roof is leaking heavily during monsoon.",
        location="Mechanical Workshop, Block G",
        category="civil",
        priority="high",
        status="in_progress",
        requester_username="hod_mech",
        estimated_cost=120000,
        assigned_to="eng_civil_3",
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/hold/",
        {"note": "Material shortage; waiting for cement supply."},
        format="json",
        HTTP_X_USER="eng_civil_3",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "on_hold"


# ---------------------------------------------------------------------------
# TC_WF_05  source_id: BW-IWD-03 - Resume from Hold Path
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_05_resume_work_from_hold():
    """TC_WF_05 | source_id: BW-IWD-03 - Resume from Hold Path
    Verify on-hold work request can be resumed by transitioning to in_progress.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Rewire electrical panel in block H",
        description="Electrical panel wiring is outdated and poses fire hazard.",
        location="Block H, Electrical Room",
        category="electrical",
        priority="urgent",
        status="on_hold",
        requester_username="hod_cse",
        estimated_cost=85000,
        assigned_to="eng_electrical_6",
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/start/",
        HTTP_X_USER="eng_electrical_6",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "in_progress"


# ---------------------------------------------------------------------------
# TC_WF_06  source_id: BW-IWD-06 - Stock Available - Material Issue Workflow
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_06_adequate_stock_no_low_stock_flag():
    """TC_WF_06 | source_id: BW-IWD-06 - Stock Available - Material Issue Workflow
    Verify inventory items with adequate stock do not show low-stock flag.
    """
    item = InventoryItem.objects.create(
        name="Steel Rods 12mm",
        unit="pieces",
        quantity_available=100,
        minimum_stock=20,
    )
    assert item.is_low_stock is False


# ---------------------------------------------------------------------------
# TC_WF_07  source_id: BW-IWD-09 - Work Execution and Verification Success Path
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_07_complete_to_close_success_path():
    """TC_WF_07 | source_id: BW-IWD-09 - Work Execution and Verification Success Path
    Verify the full success path: in_progress -> completed -> closed.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Fix drainage system near boys hostel",
        description="Drainage pipes clogged near boys hostel block B causing overflow.",
        location="Boys Hostel, Block B",
        category="plumbing",
        priority="urgent",
        status="in_progress",
        requester_username="hostel_warden_01",
        estimated_cost=22000,
        assigned_to="eng_plumbing_4",
    )
    resp_complete = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/complete/",
        {"actual_cost": "20500.00", "remarks": "Drainage pipes cleaned and replaced."},
        format="json",
        HTTP_X_USER="eng_plumbing_4",
    )
    assert resp_complete.status_code == 200
    assert resp_complete.data["status"] == "completed"

    resp_close = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/close/",
        HTTP_X_USER="supervisor_07",
    )
    assert resp_close.status_code == 200
    assert resp_close.data["status"] == "closed"


# ---------------------------------------------------------------------------
# TC_WF_08  source_id: CW-IWD-01 - Estimate Approval Routing Guard Check
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_08_illegal_transition_guard_draft_to_complete():
    """TC_WF_08 | source_id: CW-IWD-01 - Estimate Approval Routing Guard Check
    Verify that skipping workflow steps (draft -> complete) is refused.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Install CCTV at main gate",
        description="Security enhancement: install CCTV camera at main entrance.",
        location="Main Gate, Entrance",
        category="electrical",
        priority="high",
        status="draft",
        requester_username="security_head_01",
        estimated_cost=30000,
    )
    # Attempt illegal transition: draft -> complete
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/complete/",
        HTTP_X_USER="eng_electrical_7",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# TC_WF_09  source_id: CW-IWD-03 - Work Completion and Verification Boundary
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_09_closed_request_cannot_be_reopened():
    """TC_WF_09 | source_id: CW-IWD-03 - Work Completion and Verification Boundary
    Verify closed request cannot be transitioned further (terminal state).
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Repair water tank on rooftop block A",
        description="Rooftop water tank has cracks; repaired successfully.",
        location="Block A, Rooftop",
        category="civil",
        priority="medium",
        status="closed",
        requester_username="facility_head",
        estimated_cost=18000,
    )
    # Attempt to submit (illegal from closed)
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/submit/",
        HTTP_X_USER="facility_head",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# TC_WF_10  source_id: BW-IWD-15 - Urgent Fast-Track Review Path
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_wf_10_urgent_request_fast_track_review():
    """TC_WF_10 | source_id: BW-IWD-15 - Urgent Fast-Track Review Path
    Verify urgent requests flow through submit -> review -> approve quickly.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Emergency gas pipe leak repair",
        description="Gas pipeline leak detected in chemistry building; immediate repair required.",
        location="Chemistry Building, Lab 3",
        category="plumbing",
        priority="urgent",
        status="submitted",
        requester_username="hod_chemistry",
        estimated_cost=8000,
    )
    resp_review = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/review/",
        HTTP_X_USER="supervisor_08",
    )
    assert resp_review.status_code == 200
    assert resp_review.data["status"] == "under_review"

    resp_approve = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/approve/",
        {"assigned_to": "eng_plumbing_5"},
        format="json",
        HTTP_X_USER="director_01",
    )
    assert resp_approve.status_code == 200
    assert resp_approve.data["status"] == "approved"
