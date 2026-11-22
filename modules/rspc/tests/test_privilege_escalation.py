"""Privilege escalation tests for RSPC (Step 5.5).

Asserts that read authority does not convey write authority, and missing
permissions strictly yield HTTP 403 Forbidden.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.services import proposal as proposal_services


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("rspc",))
    session = make_session(modules=modules, **kw)
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


@pytest.mark.django_db
def test_faculty_cannot_endorse_proposal(stub_iam):
    """Faculty has view and create, but NOT endorse."""
    prop = proposal_services.create_proposal(
        user_id=10,
        title="Test Proposal",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("100000.00"),
    )
    proposal_services.submit_proposal(proposal=prop, actor_user_id=10)

    client = _client(
        stub_iam,
        user_id=10,
        roles=("faculty",),
        permissions=("rspc.proposal.view", "rspc.proposal.create"),
    )
    resp = client.post(
        f"/api/v1/rspc/proposals/{prop.id}/endorse/", data={"comments": "Sneaky"}, format="json"
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_hod_cannot_approve_proposal(stub_iam):
    """HoD has endorse, but NOT approve (Dean only)."""
    prop = proposal_services.create_proposal(
        user_id=10,
        title="Test Proposal",
        proposal_type="sponsored_research",
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("100000.00"),
    )
    proposal_services.submit_proposal(proposal=prop, actor_user_id=10)
    proposal_services.endorse_proposal(proposal=prop, actor_user_id=50)

    client = _client(
        stub_iam,
        user_id=50,
        roles=("Head of Department",),
        permissions=("rspc.proposal.view", "rspc.proposal.endorse"),
    )
    resp = client.post(
        f"/api/v1/rspc/proposals/{prop.id}/approve/",
        data={"comments": "Overstepping"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unauthenticated_request_is_rejected():
    client = APIClient()
    resp = client.get("/api/v1/rspc/proposals/")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_missing_module_grant_is_forbidden(stub_iam):
    """A principal without the 'rspc' module grant cannot access RSPC endpoints."""
    client = _client(
        stub_iam,
        user_id=10,
        modules=("placement_cell",),  # Only placement, NOT rspc
        permissions=("rspc.proposal.view",),
    )
    resp = client.get("/api/v1/rspc/proposals/")
    assert resp.status_code == 403
