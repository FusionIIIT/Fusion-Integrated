"""Query budget tests for RSPC (Step 5.8).

Asserts that list views execute within an identical, constant number of database queries
regardless of whether there are 2 rows or 20 rows (no N+1 queries).
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import ProjectBudgetHead
from modules.rspc.services import finance as finance_services
from modules.rspc.services import project as project_services
from modules.rspc.services import proposal as proposal_services


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("rspc",))
    session = make_session(modules=modules, **kw)
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


@pytest.mark.django_db
def test_project_list_query_budget_is_constant_across_sizes(stub_iam, django_assert_num_queries):
    """Assert project list executes the exact same number of queries with 2 rows and with 20 rows."""
    today = datetime.date.today()
    client = _client(
        stub_iam,
        user_id=1,
        roles=("admin",),
        permissions=("rspc.project.view",),
    )

    # 1. Create 2 projects
    for i in range(2):
        proj = project_services.sanction_and_register_project(
            user_id=10,
            project_code=f"RSPC/2026/QB2/{i:03d}",
            project_type="sponsored",
            title=f"Grant Project #{i}",
            department="CSE",
            funding_agency="DST",
            sanction_order_no=f"DST-2/{i}",
            sanction_date=today,
            start_date=today,
            end_date=today + datetime.timedelta(days=365),
            sanctioned_amount=Decimal("1000000.00"),
            co_pi_user_ids=[11, 12],
        )
        ProjectBudgetHead.objects.create(
            project=proj, head_type="equipment", allocated_amount=Decimal("500000.00")
        )

    # Measure query count with 2 projects
    with django_assert_num_queries(3):
        resp2 = client.get("/api/v1/rspc/projects/")
        assert resp2.status_code == 200
        assert len(resp2.data) == 2

    # 2. Add 18 more projects (total 20)
    for i in range(2, 20):
        proj = project_services.sanction_and_register_project(
            user_id=10,
            project_code=f"RSPC/2026/QB20/{i:03d}",
            project_type="sponsored",
            title=f"Grant Project #{i}",
            department="CSE",
            funding_agency="DST",
            sanction_order_no=f"DST-20/{i}",
            sanction_date=today,
            start_date=today,
            end_date=today + datetime.timedelta(days=365),
            sanctioned_amount=Decimal("1000000.00"),
            co_pi_user_ids=[11, 12],
        )
        ProjectBudgetHead.objects.create(
            project=proj, head_type="equipment", allocated_amount=Decimal("500000.00")
        )

    # Measure query count with 20 projects: MUST BE EXACTLY THE SAME 3 QUERIES!
    with django_assert_num_queries(3):
        resp20 = client.get("/api/v1/rspc/projects/")
        assert resp20.status_code == 200
        assert len(resp20.data) == 20


@pytest.mark.django_db
def test_proposal_list_query_budget_is_constant_across_sizes(stub_iam, django_assert_num_queries):
    """Assert proposal list executes the exact same number of queries with 2 rows and with 20 rows."""
    client = _client(
        stub_iam,
        user_id=1,
        roles=("Dean (RSPC)",),
        permissions=("rspc.proposal.view",),
    )

    # 1. Create 2 proposals with reviews
    for i in range(2):
        prop = proposal_services.create_proposal(
            user_id=10,
            title=f"Proposal #{i}",
            proposal_type="sponsored_research",
            department="CSE",
            funding_agency="DST",
            proposed_budget=Decimal("500000.00"),
        )
        proposal_services.submit_proposal(proposal=prop, actor_user_id=10)

    # Measure with 2 proposals (1 for proposals + 1 for prefetched reviews = 2 queries)
    with django_assert_num_queries(2):
        resp2 = client.get("/api/v1/rspc/proposals/")
        assert resp2.status_code == 200
        assert len(resp2.data) == 2

    # 2. Add 18 more proposals (total 20)
    for i in range(2, 20):
        prop = proposal_services.create_proposal(
            user_id=10,
            title=f"Proposal #{i}",
            proposal_type="sponsored_research",
            department="CSE",
            funding_agency="DST",
            proposed_budget=Decimal("500000.00"),
        )
        proposal_services.submit_proposal(proposal=prop, actor_user_id=10)

    # Measure with 20 proposals: MUST BE EXACTLY THE SAME 2 QUERIES!
    with django_assert_num_queries(2):
        resp20 = client.get("/api/v1/rspc/proposals/")
        assert resp20.status_code == 200
        assert len(resp20.data) == 20


@pytest.mark.django_db
def test_ledger_list_query_budget_is_constant_across_sizes(stub_iam, django_assert_num_queries):
    """Assert project ledger list executes the exact same queries with 2 rows and with 20 rows."""
    today = datetime.date.today()
    client = _client(
        stub_iam,
        user_id=1,
        roles=("admin",),
        permissions=("rspc.project.view", "rspc.fund.view"),
    )

    proj = project_services.sanction_and_register_project(
        user_id=10,
        project_code="RSPC/2026/LEDGER/QB",
        project_type="sponsored",
        title="Ledger Grant",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="DST/LEDGER",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("1000000.00"),
    )
    finance_services.allocate_budget_head(
        project=proj, head_type="equipment", allocated_amount=Decimal("500000.00"), actor_user_id=1
    )

    # Add 1 disbursement (total 2 transactions: 1 allocation + 1 disburse)
    finance_services.disburse_funds(
        project=proj, head_type="equipment", amount=Decimal("1000.00"), reference_no="TX-0", description="", actor_user_id=10
    )

    # Measure with 2 transactions (1 project check + 1 ledger select_related = 2 queries)
    with django_assert_num_queries(2):
        resp2 = client.get(f"/api/v1/rspc/projects/{proj.id}/ledger/")
        assert resp2.status_code == 200
        assert len(resp2.data) == 2

    # Add 18 more disbursements (total 20 transactions)
    for i in range(1, 19):
        finance_services.disburse_funds(
            project=proj, head_type="equipment", amount=Decimal("100.00"), reference_no=f"TX-{i}", description="", actor_user_id=10
        )

    # Measure with 20 transactions: MUST BE EXACTLY THE SAME 2 QUERIES!
    with django_assert_num_queries(2):
        resp20 = client.get(f"/api/v1/rspc/projects/{proj.id}/ledger/")
        assert resp20.status_code == 200
        assert len(resp20.data) == 20
