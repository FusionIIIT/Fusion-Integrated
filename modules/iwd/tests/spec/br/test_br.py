"""
Spec-based tests for IWD module — Business Rules strategy.
Student 2 (Ashmi): spec-driven, written from BR_DESIGN.json.
No production code is modified here.
"""
import pytest
from rest_framework.test import APIClient

from modules.iwd.domain.rules import (
    IWDDomainError,
    Priority,
    RequestStatus,
    WorkCategory,
    can_transition,
    compute_priority_score,
    requires_budget_allocation,
    requires_director_approval,
    validate_transition,
)
from modules.iwd.models import InventoryItem, WorkRequest, WorkRequestLog


# ---------------------------------------------------------------------------
# TC_BR_01  source_id: BR-IWD-001 - Active-role authorization
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_01_requester_username_recorded():
    """TC_BR_01 | source_id: BR-IWD-001 - Active-role authorization
    Ensure work request creation records the requester identity (X-User header).
    """
    client = APIClient()
    payload = {
        "title": "Repair lab door lock",
        "description": "The lock on computer lab 3 door is broken and needs replacement.",
        "location": "Block A, Lab 3",
        "category": "repair",
        "priority": "medium",
        "estimated_cost": "1500.00",
    }
    resp = client.post(
        "/api/v1/iwd/requests/",
        payload,
        format="json",
        HTTP_X_USER="faculty_01",
    )
    assert resp.status_code == 201
    assert resp.data["requester_username"] == "faculty_01"


# ---------------------------------------------------------------------------
# TC_BR_02  source_id: BR-IWD-002 - Automatic engineer assignment
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_02_engineer_assignment_on_approve():
    """TC_BR_02 | source_id: BR-IWD-002 - Automatic engineer assignment
    Verify assigned_to is populated when approve action designates engineer.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Fix electrical fault in block B",
        description="Tripping MCB in electrical panel needs professional repair.",
        location="Block B, Electrical Room",
        category="electrical",
        priority="high",
        status="under_review",
        requester_username="staff_01",
        estimated_cost=8000,
    )
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/approve/",
        {"assigned_to": "eng_electrical_1"},
        format="json",
        HTTP_X_USER="director_01",
    )
    assert resp.status_code == 200
    wr.refresh_from_db()
    assert wr.assigned_to == "eng_electrical_1"


# ---------------------------------------------------------------------------
# TC_BR_03  source_id: BR-IWD-003 - Cost-band routing (< Rs. 25,000 low-cost)
# ---------------------------------------------------------------------------
def test_br_03_low_cost_no_budget_allocation():
    """TC_BR_03 | source_id: BR-IWD-003 - Cost-band routing (< Rs. 25,000 low-cost band)
    Verify low-cost repairs (< 25,000) do not require formal budget allocation.
    """
    result = requires_budget_allocation(WorkCategory.REPAIR, 24000)
    assert result is False


# ---------------------------------------------------------------------------
# TC_BR_04  source_id: BR-IWD-003 - Cost-band routing (> Rs. 1,00,000 high-cost)
# ---------------------------------------------------------------------------
def test_br_04_high_cost_requires_director_approval():
    """TC_BR_04 | source_id: BR-IWD-003 - Cost-band routing (> Rs. 1,00,000 high-cost threshold)
    Verify estimate > Rs. 1,00,000 requires Director approval.
    """
    result = requires_director_approval(125000.00)
    assert result is True


# ---------------------------------------------------------------------------
# TC_BR_05  source_id: BR-IWD-003 - Cost-band routing (<= Rs. 1,00,000 boundary)
# ---------------------------------------------------------------------------
def test_br_05_boundary_no_director_approval():
    """TC_BR_05 | source_id: BR-IWD-003 - Cost-band routing (<= Rs. 1,00,000 boundary)
    Verify estimate exactly Rs. 1,00,000 does NOT require Director escalation.
    """
    result = requires_director_approval(100000.00)
    assert result is False


# ---------------------------------------------------------------------------
# TC_BR_06  source_id: BR-IWD-007 - High-cost bidding (> Rs. 5,00,000 capital budget)
# ---------------------------------------------------------------------------
def test_br_06_high_cost_budget_allocation():
    """TC_BR_06 | source_id: BR-IWD-007 - High-cost bidding authorization (> Rs. 5,00,000 capital budget rule)
    Verify civil works over Rs. 5,00,000 require formal budget allocation.
    """
    result = requires_budget_allocation(WorkCategory.CIVIL, 600000.00)
    assert result is True


# ---------------------------------------------------------------------------
# TC_BR_07  source_id: BR-IWD-007 - New construction budget rule
# ---------------------------------------------------------------------------
def test_br_07_new_construction_always_budget():
    """TC_BR_07 | source_id: BR-IWD-007 - New construction budget rule
    Verify new construction always requires budget allocation regardless of cost.
    """
    result = requires_budget_allocation(WorkCategory.NEW_CONSTRUCTION, 50000.00)
    assert result is True


# ---------------------------------------------------------------------------
# TC_BR_08  source_id: BR-IWD-009 - Rejection reason and resubmission
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_08_rejection_records_note():
    """TC_BR_08 | source_id: BR-IWD-009 - Rejection reason and resubmission
    Verify rejection transitions cleanly and records mandatory reason note.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Replace hostel corridor lights",
        description="Multiple tube lights in hostel block corridor have failed.",
        location="Hostel Block C, Corridor",
        category="electrical",
        priority="medium",
        status="under_review",
        requester_username="warden_01",
        estimated_cost=3000,
    )
    note_text = "Scope unclear; revise specification"
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/reject/",
        {"note": note_text},
        format="json",
        HTTP_X_USER="supervisor_01",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"
    log_entry = WorkRequestLog.objects.filter(work_request=wr, to_status="rejected").last()
    assert log_entry is not None
    assert note_text in log_entry.note


# ---------------------------------------------------------------------------
# TC_BR_09  source_id: BR-IWD-010 - Inventory low-stock rule
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_09_inventory_low_stock_flag():
    """TC_BR_09 | source_id: BR-IWD-010 - Inventory low-stock rule
    Verify inventory item triggers low-stock indicator when qty <= minimum_stock.
    """
    item = InventoryItem.objects.create(
        name="PVC Pipe 1-inch",
        unit="meters",
        quantity_available=5,
        minimum_stock=10,
    )
    assert item.is_low_stock is True


# ---------------------------------------------------------------------------
# TC_BR_10  source_id: BR-IWD-010 - Inventory adequate stock rule
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_10_inventory_adequate_stock():
    """TC_BR_10 | source_id: BR-IWD-010 - Inventory adequate stock rule
    Verify inventory item does not alert when quantity > minimum_stock.
    """
    item = InventoryItem.objects.create(
        name="Electrical Wire 2.5mm",
        unit="meters",
        quantity_available=25,
        minimum_stock=10,
    )
    assert item.is_low_stock is False


# ---------------------------------------------------------------------------
# TC_BR_11  source_id: BR-IWD-012 - Urgent priority scoring acceleration
# ---------------------------------------------------------------------------
def test_br_11_urgent_higher_score_than_low():
    """TC_BR_11 | source_id: BR-IWD-012 - Urgent priority scoring acceleration
    Verify urgent priority ticket score is strictly greater than low priority.
    """
    score_urgent = compute_priority_score(Priority.URGENT, None)
    score_low = compute_priority_score(Priority.LOW, None)
    assert score_urgent > score_low


# ---------------------------------------------------------------------------
# TC_BR_12  source_id: BR-IWD-013 - Audit logging of decisions
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_br_12_audit_log_on_state_change():
    """TC_BR_12 | source_id: BR-IWD-013 - Audit logging of decisions
    Verify every state change creates an audit log entry.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(
        title="Repair water cooler in library",
        description="Water cooler stopped working, needs compressor check.",
        location="Central Library, Ground Floor",
        category="electrical",
        priority="low",
        status="draft",
        requester_username="librarian_01",
        estimated_cost=2000,
    )
    log_count_before = WorkRequestLog.objects.filter(work_request=wr).count()
    resp = client.post(
        f"/api/v1/iwd/requests/{wr.pk}/submit/",
        HTTP_X_USER="librarian_01",
    )
    assert resp.status_code == 200
    log_count_after = WorkRequestLog.objects.filter(work_request=wr).count()
    assert log_count_after > log_count_before
    last_log = WorkRequestLog.objects.filter(work_request=wr).order_by("-changed_at").first()
    assert last_log.from_status == "draft"
    assert last_log.to_status == "submitted"


# ---------------------------------------------------------------------------
# TC_BR_13  source_id: BR-IWD-014 - State transition legality validation
# ---------------------------------------------------------------------------
def test_br_13_illegal_transition_raises_error():
    """TC_BR_13 | source_id: BR-IWD-014 - State transition legality validation
    Verify illegal transition (submitted -> completed) raises IWDDomainError.
    """
    with pytest.raises(IWDDomainError):
        validate_transition(RequestStatus.SUBMITTED, RequestStatus.COMPLETED)


# ---------------------------------------------------------------------------
# TC_BR_14  source_id: BR-IWD-014 - Closed state is terminal
# ---------------------------------------------------------------------------
def test_br_14_closed_state_terminal():
    """TC_BR_14 | source_id: BR-IWD-014 - Closed state is terminal
    Verify closed state has no legal outgoing transitions to any target.
    """
    for target in RequestStatus:
        if target != RequestStatus.CLOSED:
            assert can_transition(RequestStatus.CLOSED, target) is False
