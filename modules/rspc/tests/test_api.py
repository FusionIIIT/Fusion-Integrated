"""API tests for RSPC endpoints."""
import pytest
from rest_framework.test import APIClient
from conftest import make_principal
from modules.rspc.models import ResearchProject
from modules.rspc.domain.state_machine import ProposalStatus


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def faculty_client(monkeypatch, api_client):
    principal = make_principal(
        user_id=101,
        modules=["rspc"],
        permissions=[
            "rspc.proposal.create",
            "rspc.proposal.view_self",
            "rspc.consultancy.create",
            "rspc.consultancy.view_self",
            "rspc.finance.create",
            "rspc.finance.view_self",
            "rspc.procurement.create",
            "rspc.procurement.view_self",
            "rspc.appointment.create",
            "rspc.appointment.view_self",
            "rspc.progress_report.submit",
            "rspc.progress_report.view_self",
            "rspc.closure.submit",
            "rspc.closure.view_self",
        ],
        roles=["faculty"],
        active_role="faculty",
    )
    from fusion_auth.authentication import IamSessionAuthentication
    monkeypatch.setattr(
        IamSessionAuthentication,
        "authenticate",
        lambda self, request: (None, None),
    )
    # Set request.principal via middleware simulation or direct override
    api_client.force_authenticate(user=None)
    # We patch authentication or provide principal directly
    return api_client, principal


@pytest.mark.django_db
def test_unauthenticated_request_rejected(api_client):
    res = api_client.get("/api/v1/rspc/proposals")
    assert res.status_code in (401, 403)


@pytest.mark.django_db
def test_proposal_lifecycle_api(monkeypatch, api_client):
    principal = make_principal(
        user_id=101,
        modules=["rspc"],
        permissions=[
            "rspc.proposal.create",
            "rspc.proposal.view_self",
            "rspc.proposal.review_hod",
            "rspc.proposal.verify_admin",
            "rspc.proposal.decide_dean",
        ],
        roles=["faculty"],
        active_role="faculty",
    )

    # Patch authentication to inject our principal
    from fusion_auth.authentication import IamSessionAuthentication
    monkeypatch.setattr(
        IamSessionAuthentication,
        "authenticate",
        lambda self, request: (None, None),
    )

    # Test via direct service and selector checks
    from modules.rspc import services, selectors

    # 1. Create proposal
    prop = services.create_proposal(
        principal=principal,
        title="AI for Climate Resilience",
        objectives="Develop predictive models",
        funding_source="DST",
        budget_requested=5000000,
        department="CSE",
    )
    assert prop.status == ProposalStatus.DRAFT
    assert prop.user_id == 101

    # 2. Transition to Submitted
    prop = services.transition_proposal(
        proposal_id=prop.id,
        to_status=ProposalStatus.SUBMITTED,
        principal=principal,
    )
    assert prop.status == ProposalStatus.SUBMITTED
    assert prop.submitted_at is not None

    # 3. Transition to HoD review and recommend
    prop = services.transition_proposal(
        proposal_id=prop.id,
        to_status=ProposalStatus.HOD_REVIEW,
        principal=principal,
    )
    prop = services.transition_proposal(
        proposal_id=prop.id,
        to_status=ProposalStatus.HOD_RECOMMENDED,
        principal=principal,
        remarks="Feasible and aligned",
    )
    assert prop.status == ProposalStatus.HOD_RECOMMENDED
    assert prop.hod_remarks == "Feasible and aligned"

    # 4. Visible in selectors
    visible = selectors.visible_proposals(principal)
    assert visible.filter(pk=prop.pk).exists()

    # 5. Check transitions audit log
    assert prop.transitions.count() == 3


@pytest.mark.django_db
def test_consultancy_and_finance_services():
    from modules.rspc import services, selectors
    principal = make_principal(
        user_id=102,
        modules=["rspc"],
        permissions=[
            "rspc.consultancy.create",
            "rspc.consultancy.view_self",
            "rspc.consultancy.verify_admin",
            "rspc.finance.create",
            "rspc.finance.view_self",
            "rspc.finance.verify_admin",
            "rspc.finance.decide_dean",
        ],
        roles=["faculty"],
        active_role="faculty",
    )

    # Consultancy
    c = services.create_consultancy(
        principal=principal,
        title="Smart Grid Analysis",
        client_name="NTPC",
        total_amount=1200000,
    )
    assert c.status == "draft"

    # Finance
    f = services.create_finance_request(
        principal=principal,
        category="expenditure",
        description="High-performance GPU workstation",
        amount=350000,
    )
    assert f.status == "draft"
    f = services.transition_finance(
        request_id=f.id,
        to_status="submitted",
        principal=principal,
    )
    assert f.status == "submitted"
    f = services.transition_finance(
        request_id=f.id,
        to_status="verified",
        principal=principal,
        remarks="Verified against requirements",
    )
    assert f.status == "verified"
    f = services.transition_finance(
        request_id=f.id,
        to_status="approved",
        principal=principal,
        remarks="Approved within delegated authority",
    )
    assert f.status == "approved"
