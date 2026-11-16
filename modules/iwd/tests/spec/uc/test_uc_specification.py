import pytest

from modules.iwd import services
from modules.iwd.models import IwdFinalBill, IwdNotification
from modules.iwd.tests.spec.conftest import actor, assessed, complaint


@pytest.mark.django_db
def test_uc_001_iwd_001_submit_assign_and_notify():
    """UC-001 / UC-IWD-001 Main Flow."""
    row = complaint()
    assert row.state == "assigned"
    assert IwdNotification.objects.filter(complaint=row, event="complaint_submitted").count() == 2


@pytest.mark.django_db
def test_uc_002_iwd_005_status_and_history_are_readable():
    """UC-002 / UC-IWD-005 Main Flow."""
    row = complaint()
    services.assess(complaint=row, actor=actor(12), assessment={"repair": "replace"})
    assert row.audit_events.exists()
    assert row.state == "assessed"


@pytest.mark.django_db
def test_uc_003_iwd_015_assessment():
    """UC-003 / UC-IWD-015 Main Flow."""
    assert services.assess(
        complaint=complaint(), actor=actor(12), assessment={"repair": "repair"}
    ).state == "assessed"


@pytest.mark.django_db
def test_uc_004_iwd_021_estimate_routing():
    """UC-004 / UC-IWD-021 Main Flow."""
    assert assessed(cost=25000).estimate.cost_band == "mid"


@pytest.mark.django_db
def test_uc_005_iwd_025_urgent_review_does_not_change_cost_route():
    """UC-005 / UC-IWD-025 Main Flow."""
    row = assessed(cost=30000)
    services.flag_urgent(complaint=row, actor=actor(12), remarks="Critical")
    services.review_urgent(complaint=row, actor=actor(22), accepted=True)
    assert row.state == "committee_review"
    assert row.metadata["urgent_priority"] is True


@pytest.mark.django_db
def test_uc_006_iwd_031_low_cost_rejection():
    """UC-006 / UC-IWD-031 Main Flow/A1."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="reject", reason="Revise")
    assert row.state == "rejected" and row.estimate.status == "rejected"


@pytest.mark.django_db
def test_uc_007_iwd_041_committee_then_department_head():
    """UC-007 / UC-IWD-041 Main Flow/A2."""
    row = assessed(cost=30000)
    services.committee_review(complaint=row, actor=actor(21), outcome="feasible")
    assert services.decide(complaint=row, actor=actor(22), outcome="approve").state == "estimate_approved"


@pytest.mark.django_db
def test_uc_008_iwd_051_high_cost_authorizes_bidding():
    """UC-008 / UC-IWD-051 Main Flow."""
    row = assessed(cost=300001)
    services.decide(complaint=row, actor=actor(40), outcome="approve")
    assert row.state == "bidding_authorized"


@pytest.mark.django_db
def test_uc_009_iwd_061_stock_shortage():
    """UC-009 / UC-IWD-061 Main Flow/A1."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    need = services.check_stock(complaint=row, actor=actor(22), materials=[{"sku": "X", "quantity": 1}])
    assert need.complaint_id == row.id


@pytest.mark.django_db
def test_uc_010_iwd_081_compliant_vendor_selection():
    """UC-010 / UC-IWD-081 Main Flow/E1."""
    row = assessed(cost=300001)
    services.decide(complaint=row, actor=actor(40), outcome="approve")
    services.select_vendor(
        complaint=row, actor=actor(41), vendor_name="Approved Vendor", route="approved_list"
    )
    assert row.state == "vendor_selected"
    invalid = assessed(cost=300001)
    services.decide(complaint=invalid, actor=actor(40), outcome="approve")
    with pytest.raises(ValueError, match="approved procurement"):
        services.select_vendor(
            complaint=invalid, actor=actor(41), vendor_name="Bad", route="unknown"
        )


@pytest.mark.django_db
def test_uc_011_iwd_091_execute_work():
    """UC-011 / UC-IWD-091 Main Flow."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    assert services.execute_work(
        complaint=row, actor=actor(12), progress="Complete", complete=True
    ).state == "verification_pending"


@pytest.mark.django_db
def test_uc_012_iwd_101_rework_then_approval():
    """UC-012 / UC-IWD-101 Main Flow/A1."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), progress="First pass", complete=True)
    services.verify_work(complaint=row, actor=actor(22), outcome="rework", remarks="Fix leak")
    services.execute_work(complaint=row, actor=actor(12), progress="Reworked", complete=True)
    assert services.verify_work(
        complaint=row, actor=actor(22), outcome="approved"
    ).state == "resolved"


@pytest.mark.django_db
def test_uc_013_iwd_111_submit_bill():
    """UC-013 / UC-IWD-111 Main Flow/E1."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), progress="Done", complete=True)
    services.verify_work(complaint=row, actor=actor(22), outcome="approved")
    bill = services.submit_bill(
        complaint=row, actor=actor(12), invoice_number="INV", amount=10000,
        supporting_records={"evidence": True},
    )
    assert isinstance(bill, IwdFinalBill)


@pytest.mark.django_db
def test_uc_014_iwd_121_query_blocks_payment():
    """UC-014 / UC-IWD-121 Main Flow/A1."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), progress="Done", complete=True)
    services.verify_work(complaint=row, actor=actor(22), outcome="approved")
    bill = services.submit_bill(
        complaint=row, actor=actor(12), invoice_number="INV", amount=10000,
        supporting_records={"evidence": True},
    )
    services.audit_bill(bill=bill, actor=actor(31), outcome="query", remarks="Missing proof")
    with pytest.raises(ValueError, match="validated"):
        services.approve_payment(bill=bill, actor=actor(40), approved=True)


@pytest.mark.django_db
def test_uc_015_iwd_131_payment_and_settlement():
    """UC-015 / UC-IWD-131 Main Flow/A1."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), progress="Done", complete=True)
    services.verify_work(complaint=row, actor=actor(22), outcome="approved")
    bill = services.submit_bill(
        complaint=row, actor=actor(12), invoice_number="INV", amount=10000,
        supporting_records={"evidence": True},
    )
    services.audit_bill(bill=bill, actor=actor(31), outcome="validated")
    services.approve_payment(bill=bill, actor=actor(40), approved=True)
    assert services.record_settlement(bill=bill, actor=actor(50), status="paid").state == "settled"


@pytest.mark.django_db
def test_uc_016_iwd_141_feedback():
    """UC-016 / UC-IWD-141 Main Flow."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), progress="Done", complete=True)
    services.verify_work(complaint=row, actor=actor(22), outcome="approved")
    assert services.submit_feedback(complaint=row, actor=actor(7), rating=4).rating == 4


@pytest.mark.django_db
def test_uc_017_iwd_151_resubmit_recalculates_band():
    """UC-017 / UC-IWD-151 Main Flow/A1."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="reject", reason="Revise")
    services.modify_and_resubmit(complaint=row, actor=actor(12), total_cost=30000)
    assert row.state == "committee_review"


@pytest.mark.django_db
def test_uc_018_iwd_175_configured_notification():
    """UC-018 / UC-IWD-175 Main Flow."""
    row = complaint()
    notification = services.issue_configured_notification(
        complaint=row, actor=actor(20), event="policy_update", recipients=[7], message="Policy updated"
    )
    assert notification.event == "policy_update"


def test_uc_019_iwd_181_active_role_switch():
    """UC-019 / UC-IWD-181 Main Flow/E1."""
    user = actor(7, roles=("Engineer", "Department Head"))
    assert services.switch_active_role(actor=user, role="Engineer") == "Engineer"
    with pytest.raises(ValueError, match="not assigned"):
        services.switch_active_role(actor=user, role="Dean")
