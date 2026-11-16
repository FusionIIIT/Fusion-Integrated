import pytest

from modules.iwd import services
from modules.iwd.models import IwdInventoryItem
from modules.iwd.tests.spec.conftest import actor, assessed, complaint


@pytest.mark.django_db
def test_wf_001_bw_iwd_01_intake_and_assessment():
    """WF-001 / BW-IWD-01."""
    row = complaint()
    assert services.assess(complaint=row, actor=actor(12), assessment={"repair": "fix"}).state == "assessed"


@pytest.mark.django_db
def test_wf_002_bw_iwd_02_low_cost_approval():
    """WF-002 / BW-IWD-02."""
    row = assessed(cost=10000)
    assert services.decide(complaint=row, actor=actor(20), outcome="approve").state == "estimate_approved"


@pytest.mark.django_db
def test_wf_003_bw_iwd_03_mid_range_approval():
    """WF-003 / BW-IWD-03."""
    row = assessed(cost=30000)
    services.committee_review(complaint=row, actor=actor(21), outcome="feasible")
    assert services.decide(complaint=row, actor=actor(22), outcome="approve").state == "estimate_approved"


@pytest.mark.django_db
def test_wf_004_bw_iwd_04_forward_to_director():
    """WF-004 / BW-IWD-04."""
    row = assessed(cost=30000)
    services.committee_review(complaint=row, actor=actor(21), outcome="feasible")
    services.decide(complaint=row, actor=actor(22), outcome="forward")
    assert services.decide(complaint=row, actor=actor(40), outcome="approve").state == "estimate_approved"


@pytest.mark.django_db
def test_wf_005_bw_iwd_05_high_cost_vendor_selection():
    """WF-005 / BW-IWD-05."""
    row = assessed(cost=300001)
    services.decide(complaint=row, actor=actor(40), outcome="approve")
    assert services.select_vendor(
        complaint=row, actor=actor(41), vendor_name="Vendor", route="competitive_bidding"
    ).state == "vendor_selected"


@pytest.mark.django_db
def test_wf_006_bw_iwd_06_08_stock_and_shortage():
    """WF-006 / BW-IWD-06-08."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="approve")
    IwdInventoryItem.objects.create(name="Cable", sku="CABLE", quantity=1)
    assert services.check_stock(
        complaint=row, actor=actor(20), materials=[{"sku": "CABLE", "quantity": 1}]
    ).state == "materials_issued"


@pytest.mark.django_db
def test_wf_007_bw_iwd_09_10_execution_and_rework():
    """WF-007 / BW-IWD-09-10."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), complete=True)
    services.verify_work(complaint=row, actor=actor(20), outcome="rework")
    services.execute_work(complaint=row, actor=actor(12), complete=True)
    assert services.verify_work(complaint=row, actor=actor(20), outcome="approved").state == "resolved"


@pytest.mark.django_db
def test_wf_008_bw_iwd_11_billing_audit_settlement():
    """WF-008 / BW-IWD-11."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), complete=True)
    services.verify_work(complaint=row, actor=actor(20), outcome="approved")
    bill = services.submit_bill(
        complaint=row, actor=actor(12), invoice_number="I", amount=10000,
        supporting_records={"proof": True},
    )
    services.audit_bill(bill=bill, actor=actor(30), outcome="validated")
    services.approve_payment(bill=bill, actor=actor(40), approved=True)
    assert services.record_settlement(bill=bill, actor=actor(50), status="paid").state == "settled"


@pytest.mark.django_db
def test_wf_009_bw_iwd_12_14_rejected_resubmission():
    """WF-009 / BW-IWD-12-14."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="reject", reason="Change")
    services.modify_and_resubmit(complaint=row, actor=actor(12), total_cost=30000)
    assert row.state == "committee_review"


@pytest.mark.django_db
def test_wf_010_bw_iwd_15_urgent_fast_track():
    """WF-010 / BW-IWD-15."""
    row = complaint()
    services.flag_urgent(complaint=row, actor=actor(12))
    assert services.review_urgent(complaint=row, actor=actor(22), accepted=True).urgent


@pytest.mark.django_db
@pytest.mark.parametrize("amount", [10000, 30000, 300001])
def test_wf_011_cw_iwd_01_estimate_composite_routes(amount):
    """WF-011 / CW-IWD-01."""
    assert assessed(cost=amount).estimate.cost_band in {"low", "mid", "high"}


@pytest.mark.django_db
def test_wf_012_cw_iwd_02_material_composite():
    """WF-012 / CW-IWD-02."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="approve")
    need = services.check_stock(complaint=row, actor=actor(20), materials=[{"sku": "X", "quantity": 1}])
    assert need.state == "pending"


@pytest.mark.django_db
def test_wf_013_cw_iwd_03_resolution_guard():
    """WF-013 / CW-IWD-03."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), complete=True)
    assert row.state == "verification_pending"


@pytest.mark.django_db
def test_wf_014_cw_iwd_04_rejection_composite():
    """WF-014 / CW-IWD-04."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="reject", reason="Correct")
    assert services.modify_and_resubmit(
        complaint=row, actor=actor(12), total_cost=10000
    ).cost_band == "low"
