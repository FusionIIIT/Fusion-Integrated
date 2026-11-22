"""Tests specifically designed to exercise boundary conditions, edge cases,
model representations, and management commands to ensure >90% coverage.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from rest_framework.test import APIClient

from conftest import make_session
from core.api.exceptions import BadRequestError, ConflictError, DomainError, NotFoundError
from modules.rspc import registry
from modules.rspc.domain.entities import (
    BudgetHeadEntity,
    ProjectEntity,
    ProposalEntity,
    ProposalStatus,
    ProposalStatusString,
)
from modules.rspc.domain.state_machine import DomainTransitionError, ProposalStateMachine
from modules.rspc.models import (
    Project,
    ProjectBudgetHead,
    ProjectClosureRequest,
    ProjectExtensionRequest,
    ProjectFundTransaction,
    Proposal,
    ProposalReview,
)
from modules.rspc.registry import ROLE_GRANTS
from modules.rspc.selectors import (
    finance as finance_selectors,
    project as project_selectors,
    proposal as proposal_selectors,
    scoping as scoping_selectors,
)
from modules.rspc.services import (
    extension as extension_services,
    finance as finance_services,
    project as project_services,
    proposal as proposal_services,
)


def _client(stub_iam, user_id=1, role="admin", perms=None, department="CSE"):
    perms = perms or ROLE_GRANTS.get(role, ())
    session = make_session(
        user_id=user_id,
        roles=(role,),
        active_role=role,
        permissions=tuple(perms),
        modules=("rspc",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


# --- 1. Management Commands & Registry Readiness ----------------------------


@pytest.mark.django_db
def test_management_commands():
    """Execute rspc_check_deadlines and rspc_readiness commands."""
    call_command("rspc_check_deadlines")
    call_command("rspc_readiness")


def test_registry_readiness_error_branches(monkeypatch):
    """Test registry.readiness when tables or Celery beat schedule are missing."""
    from django.db import connection

    monkeypatch.setattr(connection.introspection, "table_names", lambda: [])
    unmet = registry.readiness()
    assert any("Database tables missing" in u for u in unmet)

    from config.celery import app

    monkeypatch.setattr(app.conf, "beat_schedule", {})
    unmet2 = registry.readiness()
    assert any("Celery beat schedule missing" in u for u in unmet2)


# --- 2. Model __str__ & Immutability Guards ---------------------------------


@pytest.mark.django_db
def test_model_string_representations_and_guards():
    today = datetime.date.today()
    prop = Proposal.objects.create(
        user_id=10,
        title="Str Test Proposal",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("100000.00"),
    )
    assert "Proposal#" in str(prop)

    rev = ProposalReview.objects.create(
        proposal=prop, reviewer_user_id=20, reviewer_role="HoD", action="endorse", comments="OK"
    )
    assert "Review by HoD" in str(rev)

    proj = Project.objects.create(
        user_id=10,
        project_code="P-STR-01",
        project_type="sponsored",
        title="Str Test Project",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO-STR",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=100),
        sanctioned_amount=Decimal("500000.00"),
    )
    assert "Project P-STR-01" in str(proj)

    head = ProjectBudgetHead.objects.create(
        project=proj, head_type="equipment", allocated_amount=Decimal("200000.00")
    )
    assert "equipment" in str(head)
    assert head.available_balance == Decimal("200000.00")

    tx = ProjectFundTransaction.objects.create(
        project=proj,
        budget_head=head,
        transaction_type="allocation",
        amount=Decimal("200000.00"),
        reference_no="ALLOC-1",
        created_by_user_id=1,
    )
    assert "Tx#" in str(tx)

    # Immutability guards
    with pytest.raises(PermissionDenied, match="immutable"):
        tx.save()
    with pytest.raises(PermissionDenied, match="append-only"):
        tx.delete()

    ext = ProjectExtensionRequest.objects.create(
        project=proj,
        requested_end_date=today + datetime.timedelta(days=200),
        months_requested=3,
        justification="Rain",
    )
    assert "Extension" in str(ext)

    cls_req = ProjectClosureRequest.objects.create(project=proj, remarks="Done")
    assert "Closure" in str(cls_req)


# --- 3. Domain Entities & State Machine Equality -----------------------------


def test_domain_entity_dataclasses():
    p_ent = ProposalEntity(
        id=1,
        proposal_type="sponsored_research",
        title="T",
        pi_user_id=10,
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("100.00"),
        overhead_amount=Decimal("20.00"),
        status="draft",
    )
    assert p_ent.title == "T"

    proj_ent = ProjectEntity(
        id=1,
        project_code="P1",
        project_type="sponsored",
        title="PT",
        pi_user_id=10,
        department="CSE",
        funding_agency="DST",
        sanctioned_amount=Decimal("100.00"),
        status="active",
    )
    assert proj_ent.project_code == "P1"

    b_ent = BudgetHeadEntity(
        head_type="travel",
        allocated_amount=Decimal("1000.00"),
        spent_amount=Decimal("200.00"),
        committed_amount=Decimal("100.00"),
    )
    assert b_ent.available_balance == Decimal("700.00")

    # ProposalStatusString edge cases
    s = ProposalStatusString("draft")
    assert s == "draft"
    assert s != 123
    assert s != "other"

    s_not_rec = ProposalStatusString("Department Not Recommended")
    assert s_not_rec == "rejected"
    assert s_not_rec == "Department Not Recommended"

    s_dean = ProposalStatusString("Dean Not Approved")
    assert s_dean == "rejected"
    assert s_dean == "Dean Not Approved"


# --- 4. Services Edge Cases & Refusals ---------------------------------------


@pytest.mark.django_db
def test_proposal_service_edge_cases():
    # Negative budget
    with pytest.raises(DomainError, match="strictly positive"):
        proposal_services.create_proposal(
            user_id=10,
            title="T",
            proposal_type="sponsored_research",
            department="CSE",
            funding_agency="DST",
            proposed_budget=Decimal("-10.00"),
        )

    # Incomplete proposal on submit
    prop = proposal_services.create_proposal(
        user_id=10,
        title="",  # Empty title
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("100.00"),
    )
    with pytest.raises(DomainError, match="missing mandatory fields"):
        proposal_services.submit_proposal(proposal=prop, actor_user_id=10)

    # Non-PI submit
    prop.title = "Valid Title"
    prop.save()
    with pytest.raises(BadRequestError, match="Only the Principal Investigator"):
        proposal_services.submit_proposal(proposal=prop, actor_user_id=99)

    # Submit from illegal status
    prop.status = "approved_dean"
    prop.save()
    with pytest.raises(ConflictError, match="Illegal transition"):
        proposal_services.submit_proposal(proposal=prop, actor_user_id=10)


@pytest.mark.django_db
def test_project_service_edge_cases():
    today = datetime.date.today()
    # End date before start date
    with pytest.raises(BadRequestError, match="greater than or equal to start date"):
        project_services.sanction_and_register_project(
            user_id=10,
            project_code="P-ERR-1",
            project_type="sponsored",
            title="T",
            department="CSE",
            funding_agency="DST",
            sanction_order_no="SO",
            sanction_date=today,
            start_date=today,
            end_date=today - datetime.timedelta(days=1),
            sanctioned_amount=Decimal("100.00"),
        )

    # Negative sanctioned amount
    with pytest.raises(BadRequestError, match="strictly positive"):
        project_services.sanction_and_register_project(
            user_id=10,
            project_code="P-ERR-2",
            project_type="sponsored",
            title="T",
            department="CSE",
            funding_agency="DST",
            sanction_order_no="SO",
            sanction_date=today,
            start_date=today,
            end_date=today + datetime.timedelta(days=10),
            sanctioned_amount=Decimal("-100.00"),
        )

    # Activate already active project
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-ACT-TWICE",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=10),
        sanctioned_amount=Decimal("100.00"),
    )
    project_services.activate_project(project=proj, actor_role="admin")
    with pytest.raises(ConflictError, match="Illegal transition"):
        project_services.activate_project(project=proj, actor_role="admin")


@pytest.mark.django_db
def test_finance_service_edge_cases():
    today = datetime.date.today()
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-FIN-EDGES",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=10),
        sanctioned_amount=Decimal("100.00"),
    )

    # Negative allocation
    with pytest.raises(BadRequestError, match="cannot be negative"):
        finance_services.allocate_budget_head(
            project=proj, head_type="travel", allocated_amount=Decimal("-50.00"), actor_user_id=1
        )

    # Disburse on non-existent head
    with pytest.raises(BadRequestError, match="not configured"):
        finance_services.disburse_funds(
            project=proj,
            head_type="contingency",
            amount=Decimal("10.00"),
            reference_no="X",
            description="",
            actor_user_id=1,
        )

    # Reversal on non-existent transaction
    with pytest.raises(BadRequestError, match="not found"):
        finance_services.record_reversal_transaction(
            original_transaction_id=999999,
            reversal_amount=Decimal("10.00"),
            reason="Refund",
            actor_user_id=1,
        )

    # Non-positive reversal amount
    head = finance_services.allocate_budget_head(
        project=proj, head_type="travel", allocated_amount=Decimal("100.00"), actor_user_id=1
    )
    tx = finance_services.disburse_funds(
        project=proj,
        head_type="travel",
        amount=Decimal("50.00"),
        reference_no="PO-REV",
        description="",
        actor_user_id=1,
    )
    with pytest.raises(BadRequestError, match="must be positive"):
        finance_services.record_reversal_transaction(
            original_transaction_id=tx.pk,
            reversal_amount=Decimal("0.00"),
            reason="Refund",
            actor_user_id=1,
        )


@pytest.mark.django_db
def test_extension_service_edge_cases():
    today = datetime.date.today()
    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="P-EXT-EDGES",
        project_type="sponsored",
        title="T",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="SO",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=10),
        sanctioned_amount=Decimal("100.00"),
    )

    # Non-PI requests extension
    with pytest.raises(BadRequestError, match="Only the Principal Investigator"):
        extension_services.request_project_extension(
            project=proj,
            requested_end_date=today + datetime.timedelta(days=50),
            months_requested=2,
            justification="J",
            actor_user_id=99,
        )

    req = extension_services.request_project_extension(
        project=proj,
        requested_end_date=today + datetime.timedelta(days=50),
        months_requested=2,
        justification="J",
        actor_user_id=10,
    )
    # Reviewing already reviewed extension
    extension_services.review_project_extension(
        extension_request=req, approved=True, actor_user_id=30, actor_role="dean"
    )
    with pytest.raises(ConflictError, match=r"Extension request has already been reviewed\."):
        extension_services.review_project_extension(
            extension_request=req, approved=True, actor_user_id=30, actor_role="dean"
        )

    # Over 12 months requires Director approval
    req13 = extension_services.request_project_extension(
        project=proj,
        requested_end_date=today + datetime.timedelta(days=400),
        months_requested=13,
        justification="Large extension",
        actor_user_id=10,
    )
    with pytest.raises(ConflictError, match="require Director approval"):
        extension_services.review_project_extension(
            extension_request=req13, approved=True, actor_user_id=30, actor_role="dean"
        )


# --- 5. Selectors & Scoping Edge Cases ---------------------------------------


@pytest.mark.django_db
def test_selectors_and_scoping_branches(stub_iam):
    from types import SimpleNamespace
    from fusion_auth.principal import Principal

    session_fac = make_session(
        user_id=10,
        roles=("faculty",),
        active_role="faculty",
        permissions=tuple(ROLE_GRANTS.get("faculty", ())),
        modules=("rspc",),
    )
    fac_principal = Principal.from_session(session_fac)
    req = SimpleNamespace(principal=fac_principal)

    # Scope proposals & projects with status filter
    prop = proposal_services.create_proposal(
        user_id=10,
        title="Scoped Prop",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("100.00"),
    )
    proposals = proposal_selectors.list_proposals(req, status="draft")
    assert prop in proposals

    proposals_empty = proposal_selectors.list_proposals(req, status="approved_dean")
    assert prop not in proposals_empty

    reviews = proposal_selectors.get_proposal_reviews(prop.id)
    assert list(reviews) == []

    # HoD scoping with matching and different departments
    p_cse = proposal_services.create_proposal(
        user_id=11,
        title="CSE Proposal",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("100.00"),
    )
    proposal_services.submit_proposal(proposal=p_cse, actor_user_id=11)

    p_ece = proposal_services.create_proposal(
        user_id=12,
        title="ECE Proposal",
        proposal_type="sponsored_research",
        department="ECE",
        funding_agency="DST",
        proposed_budget=Decimal("100.00"),
    )
    proposal_services.submit_proposal(proposal=p_ece, actor_user_id=12)

    hod_principal = SimpleNamespace(
        user_id=20,
        roles=("Head of Department",),
        active_role="Head of Department",
        department="CSE",
    )
    hod_req = SimpleNamespace(principal=hod_principal)
    hod_proposals = scoping_selectors.scope_proposals(hod_req)
    assert p_cse in hod_proposals
    assert p_ece not in hod_proposals

    # get_user_id and is_admin_or_dean on empty request
    assert scoping_selectors.get_user_id(None) == 0
    assert not scoping_selectors.is_admin_or_dean(None)
    assert not scoping_selectors.is_hod(None)
    assert scoping_selectors.get_department(None) == ""

    # get_proposal_or_404 and get_project_or_404 404 paths
    with pytest.raises(NotFoundError):
        scoping_selectors.get_proposal_or_404(req, 999999)
    with pytest.raises(NotFoundError):
        scoping_selectors.get_project_or_404(req, 999999)
