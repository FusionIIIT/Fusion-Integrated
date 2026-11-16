from types import SimpleNamespace

import pytest

from modules.iwd import services
from modules.iwd.models import (
    IwdComplaint,
    IwdInventoryItem,
    IwdInventoryMovement,
    IwdNotification,
)


def actor(user_id):
    return SimpleNamespace(user_id=user_id)


@pytest.mark.django_db
def test_cost_band_boundaries_are_inclusive_only_for_mid_range():
    assert services.cost_band("24999.99") == "low"
    assert services.cost_band("25000") == "mid"
    assert services.cost_band("250000") == "mid"
    assert services.cost_band("250000.01") == "high"


@pytest.mark.django_db
def test_complaint_is_assigned_by_lowest_workload_and_notifies_both_users():
    IwdComplaint.objects.create(
        reporter_user_id=99,
        title="Existing",
        description="Existing issue",
        location="A",
        engineer_user_id=11,
        state="assigned",
    )
    complaint = services.submit_complaint(
        actor=actor(7),
        title="Broken light",
        description="The corridor light is broken.",
        location="Block A",
        issue_category="electrical",
        metadata={"engineer_user_ids": [11, 12]},
    )

    assert complaint.state == "assigned"
    assert complaint.engineer_user_id == 12
    assert IwdNotification.objects.filter(
        complaint=complaint, recipient_user_id__in=[7, 12], event="complaint_submitted"
    ).count() == 2


@pytest.mark.django_db
def test_full_verified_billing_and_settlement_lifecycle():
    engineer = actor(12)
    complaint = services.submit_complaint(
        actor=actor(7),
        title="Water leakage",
        description="Leak in the north corridor.",
        location="Block B",
        issue_category="civil",
        metadata={"engineer_user_id": 12},
    )
    services.assess(complaint=complaint, actor=engineer, assessment={"repair": "replace pipe"})
    services.estimate(
        complaint=complaint,
        actor=engineer,
        total_cost=20000,
        estimated_time="2 days",
        materials=[{"sku": "PIPE-1", "quantity": "2"}],
    )
    services.decide(complaint=complaint, actor=actor(20), outcome="approve")
    item = IwdInventoryItem.objects.create(name="Pipe", sku="PIPE-1", quantity=2)
    services.check_stock(
        complaint=complaint,
        actor=actor(20),
        materials=[{"sku": item.sku, "quantity": "2"}],
    )
    services.execute_work(
        complaint=complaint,
        actor=engineer,
        progress="Repair complete",
        complete=True,
    )
    services.verify_work(complaint=complaint, actor=actor(20), outcome="approved")
    bill = services.submit_bill(
        complaint=complaint,
        actor=engineer,
        invoice_number="INV-1",
        amount=20000,
        supporting_records={"completion_report": "report-1"},
    )
    services.audit_bill(bill=bill, actor=actor(30), outcome="validated")
    services.approve_payment(bill=bill, actor=actor(40), approved=True)
    services.record_settlement(bill=bill, actor=actor(50), status="paid")

    complaint.refresh_from_db()
    bill.refresh_from_db()
    assert complaint.state == "settled"
    assert bill.state == "settled"
    assert IwdInventoryMovement.objects.filter(item=item, complaint=complaint).count() == 1
    assert complaint.audit_events.filter(action="UC-IWD-101 verify work").exists()


@pytest.mark.django_db
def test_rejection_reason_is_retained_and_resubmission_recomputes_route():
    complaint = services.submit_complaint(
        actor=actor(7),
        title="Damaged door",
        description="The door does not close.",
        location="Admin block",
        metadata={"engineer_user_id": 12},
    )
    services.assess(complaint=complaint, actor=actor(12), assessment={"repair": "replace hinge"})
    services.estimate(complaint=complaint, actor=actor(12), total_cost=10000)
    services.decide(
        complaint=complaint,
        actor=actor(20),
        outcome="reject",
        reason="Provide a clearer material breakdown.",
    )
    complaint.refresh_from_db()
    assert complaint.rejection_reason == "Provide a clearer material breakdown."
    services.modify_and_resubmit(
        complaint=complaint,
        actor=actor(12),
        total_cost=30000,
        details={"materials": "hinge"},
    )

    complaint.refresh_from_db()
    assert complaint.state == "committee_review"
    assert complaint.estimate.cost_band == "mid"
