"""Service layer integration tests for RSPC."""

import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied

from core.api.exceptions import ConflictError, DomainError
from modules.rspc.models import Proposal
from modules.rspc.services import (
    extension as extension_services,
)
from modules.rspc.services import (
    finance as finance_services,
)
from modules.rspc.services import (
    project as project_services,
)
from modules.rspc.services import (
    proposal as proposal_services,
)


@pytest.mark.django_db
def test_proposal_lifecycle_flow():
    """Submit -> Endorse by HoD -> Approve by Dean."""
    pi_id = 42
    hod_id = 99
    dean_id = 100

    prop = proposal_services.create_proposal(
        user_id=pi_id,
        title="AI-Driven Autonomous Quantum Radar",
        proposal_type="sponsored_research",
        department="ECE",
        funding_agency="DRDO",
        proposed_budget=Decimal("5000000.00"),
        overhead_amount=Decimal("500000.00"),
        summary="A novel quantum radar tracking prototype.",
    )
    assert prop.status == "draft"

    # PI submits
    prop = proposal_services.submit_proposal(proposal=prop, actor_user_id=pi_id)
    assert prop.status == "submitted_hod"

    # HoD endorses
    prop = proposal_services.endorse_proposal(
        proposal=prop, actor_user_id=hod_id, comments="Strongly recommended"
    )
    assert prop.status == "endorsed_hod"
    assert prop.reviews.count() == 1

    # Dean approves
    prop = proposal_services.approve_proposal(
        proposal=prop, actor_user_id=dean_id, comments="Approved for submission"
    )
    assert prop.status == "approved_dean"
    assert prop.reviews.count() == 2


@pytest.mark.django_db
def test_proposal_cannot_be_endorsed_by_pi():
    """BR-RSPC-004: Dual role prevention."""
    pi_id = 42
    prop = proposal_services.create_proposal(
        user_id=pi_id,
        title="Test Proposal",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("1000000.00"),
    )
    proposal_services.submit_proposal(proposal=prop, actor_user_id=pi_id)

    with pytest.raises(ConflictError, match="Conflict of interest"):
        proposal_services.endorse_proposal(proposal=prop, actor_user_id=pi_id)


@pytest.mark.django_db
def test_project_sanction_and_activation():
    today = datetime.date.today()
    next_year = today + datetime.timedelta(days=365)

    proj = project_services.sanction_and_register_project(
        user_id=42,
        project_code="RSPC/2026/CSE/001",
        project_type="sponsored",
        title="High Performance Computing Cluster Grant",
        department="CSE",
        funding_agency="SERB",
        sanction_order_no="SERB/CRG/2026/00123",
        sanction_date=today,
        start_date=today,
        end_date=next_year,
        sanctioned_amount=Decimal("7500000.00"),
        co_pi_user_ids=[43, 44],
    )
    assert proj.status == "sanctioned"
    assert proj.co_pis.count() == 2

    # Activate
    proj = project_services.activate_project(project=proj, actor_role="admin")
    assert proj.status == "active"


@pytest.mark.django_db
def test_append_only_ledger_and_budget_disbursement():
    """Test ledger immutability and balance tracking."""
    today = datetime.date.today()
    proj = project_services.sanction_and_register_project(
        user_id=42,
        project_code="RSPC/2026/ME/002",
        project_type="sponsored",
        title="Robotic Exoskeleton",
        department="ME",
        funding_agency="CSIR",
        sanction_order_no="CSIR/2026/888",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=180),
        sanctioned_amount=Decimal("2000000.00"),
    )

    # Allocate equipment budget
    head = finance_services.allocate_budget_head(
        project=proj,
        head_type="equipment",
        allocated_amount=Decimal("1200000.00"),
        actor_user_id=1,
    )
    assert head.allocated_amount == Decimal("1200000.00")
    assert head.available_balance == Decimal("1200000.00")

    # Disburse valid amount
    tx = finance_services.disburse_funds(
        project=proj,
        head_type="equipment",
        amount=Decimal("400000.00"),
        reference_no="PO-2026-001",
        description="Sensor array procurement",
        actor_user_id=42,
    )
    assert tx.amount == Decimal("400000.00")
    head.refresh_from_db()
    assert head.spent_amount == Decimal("400000.00")
    assert head.available_balance == Decimal("800000.00")

    # Exceeding budget raises DomainError (422)
    with pytest.raises((ConflictError, DomainError), match="Insufficient balance"):
        finance_services.disburse_funds(
            project=proj,
            head_type="equipment",
            amount=Decimal("900000.00"),
            reference_no="PO-2026-002",
            description="Exceeding purchase",
            actor_user_id=42,
        )

    # Immutable ledger guard: updating or deleting a ledger transaction raises PermissionDenied
    with pytest.raises(PermissionDenied):
        tx.amount = Decimal("500000.00")
        tx.save()

    with pytest.raises(PermissionDenied):
        tx.delete()


@pytest.mark.django_db
def test_extension_and_closure_flow():
    today = datetime.date.today()
    proj = project_services.sanction_and_register_project(
        user_id=42,
        project_code="RSPC/2026/DES/003",
        project_type="consultancy",
        title="Urban Mobility UI",
        department="Design",
        funding_agency="SmartCity",
        sanction_order_no="SC/2026/01",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=90),
        sanctioned_amount=Decimal("500000.00"),
    )
    proj = project_services.activate_project(project=proj, actor_role="admin")

    # Request extension
    ext = extension_services.request_project_extension(
        project=proj,
        requested_end_date=today + datetime.timedelta(days=180),
        months_requested=3,
        justification="Pending user testing trials",
        actor_user_id=42,
    )
    assert proj.status == "extension_requested"

    # Approve extension
    ext = extension_services.review_project_extension(
        extension_request=ext,
        approved=True,
        actor_user_id=100,
        actor_role="dean",
        comments="Approved as requested",
    )
    proj.refresh_from_db()
    assert proj.status == "active"
    assert proj.end_date == today + datetime.timedelta(days=180)

    # Closure
    closure = extension_services.request_project_closure(
        project=proj, actor_user_id=42, remarks="Project completed"
    )
    assert proj.status == "closure_pending"

    closure = extension_services.approve_project_closure(project=proj, actor_user_id=100)
    proj.refresh_from_db()
    assert proj.status == "closed"
    assert closure.status == "approved"


@pytest.mark.django_db
def test_proposal_rejection_flow():
    pi_id = 42
    hod_id = 99
    prop = proposal_services.create_proposal(
        user_id=pi_id,
        title="Edge ML for IoT",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="CSIR",
        proposed_budget=Decimal("2000000.00"),
    )
    prop = proposal_services.submit_proposal(proposal=prop, actor_user_id=pi_id)
    prop = proposal_services.reject_proposal(
        proposal=prop, actor_user_id=hod_id, actor_role="hod", comments="Needs revision"
    )
    assert prop.status == "rejected"
    assert prop.reviews.filter(action="reject").exists()


@pytest.mark.django_db
def test_extension_rejection_flow():
    today = datetime.date.today()
    proj = project_services.sanction_and_register_project(
        user_id=42,
        project_code="RSPC/2026/DES/099",
        project_type="sponsored",
        title="Design Prototyping",
        department="Design",
        funding_agency="MHRD",
        sanction_order_no="MHRD/01",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=90),
        sanctioned_amount=Decimal("100000.00"),
    )
    proj = project_services.activate_project(project=proj, actor_role="admin")
    ext = extension_services.request_project_extension(
        project=proj,
        requested_end_date=today + datetime.timedelta(days=180),
        months_requested=3,
        justification="Pending trials",
        actor_user_id=42,
    )
    ext = extension_services.review_project_extension(
        extension_request=ext,
        approved=False,
        actor_user_id=100,
        actor_role="dean",
        comments="Insufficient justification",
    )
    assert ext.status == "rejected"
    proj.refresh_from_db()
    assert proj.status == "active"


@pytest.mark.django_db
def test_finance_reversal_transaction():
    today = datetime.date.today()
    proj = project_services.sanction_and_register_project(
        user_id=42,
        project_code="RSPC/2026/FIN/REV",
        project_type="sponsored",
        title="Finance Reversal Test",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="DST/REV",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("1000000.00"),
    )
    finance_services.allocate_budget_head(
        project=proj,
        head_type="equipment",
        allocated_amount=Decimal("500000.00"),
        actor_user_id=1,
    )
    tx = finance_services.disburse_funds(
        project=proj,
        head_type="equipment",
        amount=Decimal("100000.00"),
        reference_no="PO-REV-01",
        description="Vendor refund",
        actor_user_id=1,
    )
    rev_tx = finance_services.record_reversal_transaction(
        original_transaction_id=tx.pk,
        reversal_amount=Decimal("100000.00"),
        reason="Vendor cancelled shipment",
        actor_user_id=1,
    )
    assert rev_tx.transaction_type == "reversal"
    assert rev_tx.amount == Decimal("100000.00")


@pytest.mark.django_db(transaction=True)
def test_concurrent_proposal_approval_prevented_by_select_for_update():
    """Verify that racing approval attempts on the same proposal cannot double-approve."""
    import threading

    prop = proposal_services.create_proposal(
        user_id=10,
        title="Concurrent Race Proposal",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("500000.00"),
    )
    proposal_services.submit_proposal(proposal=prop, actor_user_id=10)
    proposal_services.endorse_proposal(proposal=prop, actor_user_id=20, actor_role="hod")

    barrier = threading.Barrier(2)
    results = []
    errors = []

    def worker(dean_id: int):
        from django.db import connection

        try:
            barrier.wait(timeout=5)
            # Re-fetch from db to start clean
            p = Proposal.objects.get(pk=prop.pk)
            approved = proposal_services.approve_proposal(
                proposal=p, actor_user_id=dean_id, actor_role="dean", comments=f"Approved by {dean_id}"
            )
            results.append(approved)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            connection.close()

    t1 = threading.Thread(target=worker, args=(101,))
    t2 = threading.Thread(target=worker, args=(102,))

    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    # Exactly one succeeded and one was blocked by state machine / select_for_update
    from django.db import OperationalError

    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], (ConflictError, OperationalError))
    assert prop.reviews.filter(action="approve").count() == 1

