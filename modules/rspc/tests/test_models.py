"""Tests for RSPC models, invariants, string representations, and immutability guards."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied

from modules.rspc.models import (
    Project,
    ProjectBudgetHead,
    ProjectClosureRequest,
    ProjectExtensionRequest,
    ProjectFundTransaction,
    Proposal,
    ProposalReview,
)


@pytest.mark.django_db
def test_proposal_model_representation_and_lifecycle():
    prop = Proposal.objects.create(
        user_id=10,
        title="Distributed Quantum Consensus",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST-SERB",
        proposed_budget=Decimal("500000.00"),
    )
    assert f"Proposal#{prop.id}" in str(prop)
    assert prop.status == "draft"


@pytest.mark.django_db
def test_proposal_review_model_representation():
    prop = Proposal.objects.create(
        user_id=10,
        title="Quantum Cryptography",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("250000.00"),
    )
    rev = ProposalReview.objects.create(
        proposal=prop,
        reviewer_user_id=20,
        reviewer_role="Head of Department",
        action="endorse",
        comments="Endorsed with full department backing.",
    )
    assert "Review by Head of Department" in str(rev)
    assert "endorse" in str(rev)


@pytest.mark.django_db
def test_project_and_budget_head_models():
    today = datetime.date.today()
    proj = Project.objects.create(
        user_id=10,
        project_code="RSPC/2026/CSE/777",
        project_type="sponsored",
        title="Scalable Fault-Tolerant Systems",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-DST-777",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("1000000.00"),
    )
    assert "Project RSPC/2026/CSE/777" in str(proj)
    assert proj.status == "sanctioned"

    head = ProjectBudgetHead.objects.create(
        project=proj,
        head_type="Equipment",
        allocated_amount=Decimal("600000.00"),
    )
    assert "Equipment" in str(head)
    assert head.available_balance == Decimal("600000.00")

    # Update spent and committed
    head.spent_amount = Decimal("150000.00")
    head.committed_amount = Decimal("50000.00")
    head.save()
    assert head.available_balance == Decimal("400000.00")


@pytest.mark.django_db
def test_financial_ledger_immutability_and_append_only():
    today = datetime.date.today()
    proj = Project.objects.create(
        user_id=10,
        project_code="RSPC/2026/CSE/888",
        project_type="sponsored",
        title="Immutable Ledger Grant",
        department="CSE",
        funding_agency="SERB",
        sanction_order_no="SO-888",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=180),
        sanctioned_amount=Decimal("300000.00"),
    )
    head = ProjectBudgetHead.objects.create(
        project=proj,
        head_type="Consumables",
        allocated_amount=Decimal("300000.00"),
    )
    tx = ProjectFundTransaction.objects.create(
        project=proj,
        budget_head=head,
        transaction_type="allocation",
        amount=Decimal("300000.00"),
        reference_no="INIT-ALLOC",
        created_by_user_id=1,
    )
    assert f"Tx#{tx.id}" in str(tx)

    # Immutability: row update is forbidden
    with pytest.raises(PermissionDenied, match="immutable"):
        tx.description = "Tampered description"
        tx.save()

    # Append-only: row deletion is forbidden
    with pytest.raises(PermissionDenied, match="append-only"):
        tx.delete()


@pytest.mark.django_db
def test_extension_and_closure_request_models():
    today = datetime.date.today()
    proj = Project.objects.create(
        user_id=10,
        project_code="P-EXT-MODELS",
        project_type="sponsored",
        title="Lifecycle Model Grant",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-EXT",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=90),
        sanctioned_amount=Decimal("100000.00"),
    )
    ext = ProjectExtensionRequest.objects.create(
        project=proj,
        requested_end_date=today + datetime.timedelta(days=180),
        months_requested=3,
        justification="Experimental data collection extension",
    )
    assert "Extension for P-EXT-MODELS" in str(ext)
    assert ext.status == "submitted"

    closure = ProjectClosureRequest.objects.create(
        project=proj,
        remarks="Deliverables submitted to funding agency.",
    )
    assert "Closure for P-EXT-MODELS" in str(closure)
    assert closure.status == "pending"
