"""Tests for RSPC selectors and scoping invariants."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from modules.rspc.selectors import (
    proposal as proposal_selectors,
)
from modules.rspc.selectors import (
    scoping as scoping_selectors,
)
from modules.rspc.services import proposal as proposal_services


@pytest.mark.django_db
def test_selectors_and_scoping_branches():
    fac_principal = SimpleNamespace(
        user_id=10,
        roles=("faculty",),
        active_role="faculty",
        department="CSE",
    )
    req = SimpleNamespace(principal=fac_principal)

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

    # Empty / Anonymous request helpers
    assert scoping_selectors.get_user_id(None) == 0
    assert not scoping_selectors.is_admin_or_dean(None)
    assert not scoping_selectors.is_hod(None)
    assert scoping_selectors.get_department(None) == ""
