import pytest

from modules.iwd import services
from modules.iwd.models import IwdComplaint, IwdFeedback, IwdInventoryItem, IwdNotification
from modules.iwd.tests.spec.conftest import actor, assessed, complaint


@pytest.mark.django_db
def test_fr_001_afr_iwd_001_employee_submits_valid_complaint():
    """FR-001 / AFR-IWD-001."""
    row = complaint()
    assert row.pk and row.reporter_user_id == 7


@pytest.mark.django_db
def test_fr_002_afr_iwd_007_automatic_assignment_uses_lowest_load():
    """FR-002 / AFR-IWD-007."""
    IwdComplaint.objects.create(
        reporter_user_id=99, title="Existing", description="Existing", location="A",
        engineer_user_id=11, state="assigned",
    )
    row = services.submit_complaint(
        actor=actor(7), title="Issue", description="Details", location="B",
        metadata={"engineer_user_ids": [11, 12]},
    )
    assert row.engineer_user_id == 12


@pytest.mark.django_db
def test_fr_003_afr_iwd_010_engineer_records_assessment():
    """FR-003 / AFR-IWD-010."""
    row = complaint()
    result = services.assess(complaint=row, actor=actor(12), assessment={"repair": "replace"})
    assert result.state == "assessed"
    assert result.metadata["assessment"]["repair"] == "replace"


@pytest.mark.django_db
def test_fr_004_afr_iwd_013_estimate_is_stored_and_routed():
    """FR-004 / AFR-IWD-013."""
    row = assessed(cost=20000)
    assert row.estimate.total_cost == 20000
    assert row.state == "low_cost_review"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("amount", "state"),
    [(24999.99, "low_cost_review"), (25000, "committee_review"), (250000, "committee_review"),
     (250000.01, "director_review")],
)
def test_fr_005_afr_iwd_014_cost_band_boundaries(amount, state):
    """FR-005 / AFR-IWD-014."""
    assert assessed(cost=amount).state == state


@pytest.mark.django_db
def test_fr_006_afr_iwd_020_department_head_can_approve_reject_or_forward():
    """FR-006 / AFR-IWD-020."""
    approved = assessed(cost=30000)
    services.committee_review(complaint=approved, actor=actor(21), outcome="feasible")
    services.decide(complaint=approved, actor=actor(22), outcome="approve")
    assert approved.state == "estimate_approved"

    forwarded = assessed(cost=30000)
    services.committee_review(complaint=forwarded, actor=actor(21), outcome="feasible")
    services.decide(complaint=forwarded, actor=actor(22), outcome="forward")
    assert forwarded.state == "director_review"

    rejected = assessed(cost=30000)
    services.committee_review(complaint=rejected, actor=actor(21), outcome="feasible")
    services.decide(complaint=rejected, actor=actor(22), outcome="reject", reason="Needs revision")
    assert rejected.state == "rejected"


@pytest.mark.django_db
def test_fr_007_afr_iwd_024_rejection_requires_and_retains_reason():
    """FR-007 / AFR-IWD-024."""
    row = assessed(cost=10000)
    with pytest.raises(ValueError, match="reason"):
        services.decide(complaint=row, actor=actor(22), outcome="reject")
    services.decide(complaint=row, actor=actor(22), outcome="reject", reason="Missing breakdown")
    row.refresh_from_db()
    assert row.rejection_reason == "Missing breakdown"


@pytest.mark.django_db
def test_fr_008_afr_iwd_028_stock_issue_or_shortage():
    """FR-008 / AFR-IWD-028."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    IwdInventoryItem.objects.create(name="Pipe", sku="PIPE", quantity=2)
    result = services.check_stock(
        complaint=row, actor=actor(22), materials=[{"sku": "PIPE", "quantity": 2}]
    )
    assert result.state == "materials_issued"

    shortage = assessed(cost=10000)
    services.decide(complaint=shortage, actor=actor(22), outcome="approve")
    need = services.check_stock(
        complaint=shortage, actor=actor(22), materials=[{"sku": "MISSING", "quantity": 1}]
    )
    assert need.state == "pending" and shortage.state == "materials_pending"


@pytest.mark.django_db
def test_fr_009_afr_iwd_033_urgent_flag_creates_alert():
    """FR-009 / AFR-IWD-033."""
    row = complaint()
    services.flag_urgent(complaint=row, actor=actor(12), remarks="Safety risk")
    assert row.urgent
    assert IwdNotification.objects.filter(complaint=row, event="urgent_escalation").exists()


@pytest.mark.django_db
def test_fr_010_afr_iwd_038_resolution_requires_verification():
    """FR-010 / AFR-IWD-038."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), progress="Done", complete=True)
    assert row.state == "verification_pending"
    services.verify_work(complaint=row, actor=actor(22), outcome="approved")
    assert row.state == "resolved"


@pytest.mark.django_db
def test_fr_011_afr_iwd_040_verified_work_can_be_billed_and_audited():
    """FR-011 / AFR-IWD-040."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), progress="Done", complete=True)
    services.verify_work(complaint=row, actor=actor(22), outcome="approved")
    bill = services.submit_bill(
        complaint=row, actor=actor(12), invoice_number="INV-1", amount=10000,
        supporting_records={"completion": "evidence"},
    )
    services.audit_bill(bill=bill, actor=actor(31), outcome="validated")
    assert bill.state == "validated"
    assert row.state == "payment_approval_pending"


@pytest.mark.django_db
def test_fr_012_afr_iwd_046_employee_submits_feedback_after_resolution():
    """FR-012 / AFR-IWD-046."""
    row = assessed(cost=10000)
    services.decide(complaint=row, actor=actor(22), outcome="approve")
    services.execute_work(complaint=row, actor=actor(12), progress="Done", complete=True)
    services.verify_work(complaint=row, actor=actor(22), outcome="approved")
    feedback = services.submit_feedback(
        complaint=row, actor=actor(7), rating=5, comments="Resolved", post_repair_issue=""
    )
    assert isinstance(feedback, IwdFeedback)
