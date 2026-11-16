import pytest

from modules.iwd import services
from modules.iwd.models import IwdInventoryItem
from modules.iwd.tests.spec.conftest import actor, assessed, complaint


def test_br_001_iwd_001_active_role_switch_rejects_unassigned():
    """BR-001 / BR-IWD-001."""
    user = actor(7, roles=("Engineer",))
    with pytest.raises(ValueError):
        services.switch_active_role(actor=user, role="Dean")


@pytest.mark.django_db
def test_br_002_iwd_002_assignment_and_notification():
    """BR-002 / BR-IWD-002."""
    row = complaint()
    assert row.engineer_user_id == 12 and row.notifications.exists()


@pytest.mark.parametrize(
    ("amount", "band"),
    [(24999, "low"), (25000, "mid"), (250000, "mid"), (250001, "high")],
)
def test_br_003_iwd_003_cost_band_rule(amount, band):
    """BR-003 / BR-IWD-003."""
    assert services.cost_band(amount) == band


@pytest.mark.django_db
def test_br_004_iwd_004_low_cost_requires_approval():
    """BR-004 / BR-IWD-004."""
    row = assessed(cost=10000)
    with pytest.raises(ValueError, match="approved"):
        services.check_stock(complaint=row, actor=actor(20), materials=[{"sku": "X", "quantity": 1}])


@pytest.mark.django_db
def test_br_005_iwd_005_mid_range_requires_committee():
    """BR-005 / BR-IWD-005."""
    row = assessed(cost=30000)
    with pytest.raises(ValueError, match="committee"):
        services.decide(complaint=row, actor=actor(20), outcome="approve")


@pytest.mark.django_db
def test_br_006_iwd_006_department_head_decision():
    """BR-006 / BR-IWD-006."""
    row = assessed(cost=30000)
    services.committee_review(complaint=row, actor=actor(21), outcome="feasible")
    assert services.decide(complaint=row, actor=actor(22), outcome="forward").state == "director_review"


@pytest.mark.django_db
def test_br_007_iwd_007_high_cost_requires_director_approval():
    """BR-007 / BR-IWD-007."""
    row = assessed(cost=300001)
    assert services.decide(complaint=row, actor=actor(40), outcome="approve").state == "bidding_authorized"


@pytest.mark.django_db
def test_br_008_iwd_008_vendor_route_is_validated():
    """BR-008 / BR-IWD-008."""
    row = assessed(cost=300001)
    services.decide(complaint=row, actor=actor(40), outcome="approve")
    with pytest.raises(ValueError, match="approved procurement"):
        services.select_vendor(complaint=row, actor=actor(41), vendor_name="Bad", route="direct")


@pytest.mark.django_db
def test_br_009_iwd_009_rejection_resubmission_recalculates_route():
    """BR-009 / BR-IWD-009."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="reject", reason="Revise")
    services.modify_and_resubmit(complaint=row, actor=actor(12), total_cost=30000)
    assert row.state == "committee_review"


@pytest.mark.django_db
def test_br_010_iwd_010_inventory_before_procurement():
    """BR-010 / BR-IWD-010."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="approve")
    need = services.check_stock(complaint=row, actor=actor(20), materials=[{"sku": "NONE", "quantity": 1}])
    assert need.state == "pending"


@pytest.mark.django_db
def test_br_011_iwd_011_inventory_movement_audit():
    """BR-011 / BR-IWD-011."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="approve")
    IwdInventoryItem.objects.create(name="Bolt", sku="BOLT", quantity=1)
    services.check_stock(complaint=row, actor=actor(20), materials=[{"sku": "BOLT", "quantity": 1}])
    assert row.inventory_movements.count() == 1


@pytest.mark.django_db
def test_br_012_iwd_012_urgent_does_not_change_route():
    """BR-012 / BR-IWD-012."""
    row = assessed(cost=30000)
    services.flag_urgent(complaint=row, actor=actor(12))
    assert row.state == "committee_review"


@pytest.mark.django_db
def test_br_013_iwd_013_decisions_are_audited():
    """BR-013 / BR-IWD-013."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="reject", reason="No detail")
    assert row.audit_events.filter(action="approval rejection").exists()


@pytest.mark.django_db
def test_br_014_iwd_014_rework_keeps_complaint_unresolved():
    """BR-014 / BR-IWD-014."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), complete=True)
    services.verify_work(complaint=row, actor=actor(20), outcome="rework")
    assert row.state == "rework_required"


@pytest.mark.django_db
def test_br_015_iwd_015_bill_audit_records_query():
    """BR-015 / BR-IWD-015."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), complete=True)
    services.verify_work(complaint=row, actor=actor(20), outcome="approved")
    bill = services.submit_bill(
        complaint=row, actor=actor(12), invoice_number="I", amount=10000,
        supporting_records={"proof": True},
    )
    services.audit_bill(bill=bill, actor=actor(30), outcome="query", remarks="Mismatch")
    assert bill.state == "queried"


@pytest.mark.django_db
def test_br_016_iwd_016_settlement_sequence_is_enforced():
    """BR-016 / BR-IWD-016."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(20), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), complete=True)
    services.verify_work(complaint=row, actor=actor(20), outcome="approved")
    bill = services.submit_bill(
        complaint=row, actor=actor(12), invoice_number="I", amount=10000,
        supporting_records={"proof": True},
    )
    with pytest.raises(ValueError, match="validated"):
        services.approve_payment(bill=bill, actor=actor(40), approved=True)


@pytest.mark.django_db
def test_br_017_iwd_017_feedback_after_resolution_only():
    """BR-017 / BR-IWD-017."""
    row = complaint()
    with pytest.raises(ValueError, match="after physical"):
        services.submit_feedback(complaint=row, actor=actor(7), rating=5)


def test_br_018_iwd_018_department_head_and_dean_are_not_aliases():
    """BR-018 / BR-IWD-018."""
    user = actor(7, roles=("Department Head",))
    with pytest.raises(ValueError):
        services.switch_active_role(actor=user, role="Dean")
