"""Integration tests for end-to-end IWD workflows and lifecycles."""

from decimal import Decimal

import pytest

from modules.iwd.domain.state_machine import IWDState
from modules.iwd.models import InventoryItem
from modules.iwd.services import (
    approvals,
    complaints,
    estimates,
    execution,
    feedback,
    inventory,
    settlement,
    verification,
)
from modules.iwd.services.verification import MaxReworkExceededError

pytestmark = pytest.mark.django_db


def test_full_low_cost_lifecycle():
    """Verify entire happy path from intake to settlement for low-cost repair."""
    # 1. Intake
    c = complaints.submit_complaint(
        requester_user_id=10,
        category="Civil",
        location="Hall 3 Room 101",
        remarks="Leaking tap",
    )
    assert c.status == IWDState.ASSIGNED
    assert c.assigned_engineer_id is not None

    # 2. Assessment
    c = complaints.assess_complaint(
        complaint_id=c.id,
        engineer_user_id=c.assigned_engineer_id,
        assessment_details="Needs washer replacement",
    )
    assert c.status == IWDState.ASSESSED

    # 3. Estimate
    est = estimates.submit_estimate(
        complaint_id=c.id,
        engineer_user_id=c.assigned_engineer_id,
        total_cost=Decimal("1500.00"),
        estimated_time_days=2,
        materials_details="Rubber washer",
    )
    assert est.cost_band == "LOW"
    c.refresh_from_db()
    assert c.status == IWDState.LOW_COST_REVIEW_PENDING

    # 4. Low-cost approval
    approvals.review_low_cost(
        complaint_id=c.id,
        admin_user_id=200,
        approve=True,
        reason="Low cost approved",
    )
    c.refresh_from_db()
    assert c.status == IWDState.ESTIMATE_APPROVED

    # 5. Inventory check & stock issue
    item = InventoryItem.objects.create(
        name="Rubber Washer",
        category="Civil",
        stock_quantity=10,
        unit="pcs",
        unit_price=Decimal("50.00"),
    )
    c = inventory.check_stock_and_issue(
        complaint_id=c.id,
        item_id=item.id,
        quantity=2,
        user_id=200,
        remarks="Issued 2 washers",
    )
    assert c.status == IWDState.MATERIALS_ISSUED
    item.refresh_from_db()
    assert item.stock_quantity == 8

    # 6. Execution
    c = execution.start_work(complaint_id=c.id, engineer_user_id=c.assigned_engineer_id)
    assert c.status == IWDState.READY_FOR_EXECUTION

    c = execution.mark_work_complete(
        complaint_id=c.id,
        engineer_user_id=c.assigned_engineer_id,
    )
    assert c.status == IWDState.VERIFICATION_PENDING

    # 7. Physical verification by Department Head
    c = verification.verify_work(
        complaint_id=c.id,
        verifier_user_id=300,
        outcome="Approved",
        remarks="Work inspected and verified",
    )
    assert c.status == IWDState.RESOLVED
    assert c.is_resolved is True

    # 8. Settlement flow: bill -> audit -> director -> accounts
    bill = settlement.submit_final_bill(
        complaint_id=c.id,
        engineer_user_id=c.assigned_engineer_id,
        total_amount=Decimal("1500.00"),
    )
    assert bill.total_amount == Decimal("1500.00")
    c.refresh_from_db()
    assert c.status == IWDState.AUDIT_PENDING

    settlement.audit_bill(
        complaint_id=c.id,
        auditor_user_id=400,
        outcome="Validated",
        remarks="Invoice verified",
    )
    c.refresh_from_db()
    assert c.status == IWDState.DIRECTOR_PAYMENT_APPROVAL_PENDING

    settlement.approve_payment(
        complaint_id=c.id,
        director_user_id=500,
    )
    c.refresh_from_db()
    assert c.status == IWDState.ACCOUNTS_SETTLEMENT_PENDING

    settlement.settle_payment(
        complaint_id=c.id,
        accounts_user_id=600,
        settlement_reference="TXN-998877",
    )
    c.refresh_from_db()
    assert c.status == IWDState.SETTLED

    # 9. Feedback
    fb = feedback.submit_feedback(
        complaint_id=c.id,
        employee_user_id=10,
        rating=5,
        comments="Excellent prompt service",
    )
    assert fb.rating == 5


def test_rework_cycle_and_second_rework_prevention():
    """Verify single rework cycle allowed, but further failure raises error (BW-IWD-10)."""
    c = complaints.submit_complaint(
        requester_user_id=11,
        category="Electrical",
        location="Lab 2",
        remarks="Switch faulty",
    )
    c.status = IWDState.VERIFICATION_PENDING
    c.save()

    # First quality failure -> Rework Required
    c = verification.verify_work(
        complaint_id=c.id,
        verifier_user_id=300,
        outcome="Rework",
        remarks="Improper wiring, rework needed",
    )
    assert c.status == IWDState.REWORK_REQUIRED
    assert c.rework_count == 1

    # Engineer executes rework
    c = execution.execute_rework(
        complaint_id=c.id,
        engineer_user_id=c.assigned_engineer_id,
    )
    assert c.status == IWDState.VERIFICATION_PENDING

    # Second failure attempt must raise MaxReworkExceededError
    with pytest.raises(MaxReworkExceededError):
        verification.verify_work(
            complaint_id=c.id,
            verifier_user_id=300,
            outcome="Rework",
            remarks="Still faulty",
        )


def test_mid_cost_rejection_and_resubmission():
    """Verify mid-cost estimate review, rejection, and resubmission route (BR-IWD-009)."""
    c = complaints.submit_complaint(
        requester_user_id=12,
        category="Civil",
        location="Library roof",
        remarks="Major ceiling seepage",
    )
    complaints.assess_complaint(
        complaint_id=c.id,
        engineer_user_id=c.assigned_engineer_id,
        assessment_details="Waterproofing required",
    )
    estimates.submit_estimate(
        complaint_id=c.id,
        engineer_user_id=c.assigned_engineer_id,
        total_cost=Decimal("75000.00"),
        estimated_time_days=10,
        materials_details="Chemical coating",
    )
    c.refresh_from_db()
    assert c.status == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING

    approvals.record_committee_review(
        complaint_id=c.id,
        reviewer_user_id=201,
        approved=True,
        outcome="Committee concurs with estimate",
    )
    c.refresh_from_db()
    assert c.status == IWDState.DEPARTMENT_HEAD_REVIEW_PENDING

    approvals.review_mid_range(
        complaint_id=c.id,
        dept_head_user_id=300,
        decision="reject",
        remarks="Cost estimate is inflated",
    )
    c.refresh_from_db()
    assert c.status == IWDState.REJECTED_MID_RANGE

    # Resubmit with lower cost
    estimates.resubmit_estimate(
        complaint_id=c.id,
        engineer_user_id=c.assigned_engineer_id,
        total_cost=Decimal("60000.00"),
        materials_details="Revised material breakdown",
    )
    c.refresh_from_db()
    assert c.status == IWDState.MID_RANGE_COMMITTEE_REVIEW_PENDING


def test_urgent_escalation_flow():
    """Verify urgent escalation tightens deadline and routes to urgent review (BR-IWD-012)."""
    c = complaints.submit_complaint(
        requester_user_id=13,
        category="Electrical",
        location="Server room",
        remarks="AC failure in datacenter",
        urgency="High",
    )
    c = complaints.flag_urgent(
        complaint_id=c.id,
        engineer_user_id=c.assigned_engineer_id,
        remarks="Server overheating imminent",
    )
    assert c.status == IWDState.URGENT_REVIEW_PENDING
    assert c.is_urgent_escalated is True

    c = complaints.review_urgent(
        complaint_id=c.id,
        reviewer_user_id=300,
        role="iwd_department_head",
        accept=True,
    )
    assert c.status == IWDState.URGENT_PRIORITY_ACTIVE
