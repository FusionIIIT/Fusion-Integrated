"""Query budget tests for RSPC (Step 5.8).

Asserts that list views execute within a constant number of database queries
regardless of the number of items returned (no N+1 queries).
"""

import datetime
from decimal import Decimal

import pytest
from pytest_django.asserts import assertNumQueries
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import ProjectBudgetHead
from modules.rspc.services import project as project_services


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("rspc",))
    session = make_session(modules=modules, **kw)
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


@pytest.mark.django_db
def test_project_list_query_budget(stub_iam):
    today = datetime.date.today()
    client = _client(
        stub_iam,
        user_id=1,
        roles=("admin",),
        permissions=("rspc.project.view",),
    )

    # Create 5 projects with Co-PIs and Budget Heads
    for i in range(5):
        proj = project_services.sanction_and_register_project(
            user_id=10,
            project_code=f"RSPC/2026/BUDGET/{i:03d}",
            project_type="sponsored",
            title=f"Grant Project #{i}",
            department="CSE",
            funding_agency="DST",
            sanction_order_no=f"DST/{i}",
            sanction_date=today,
            start_date=today,
            end_date=today + datetime.timedelta(days=365),
            sanctioned_amount=Decimal("1000000.00"),
            co_pi_user_ids=[11, 12],
        )
        ProjectBudgetHead.objects.create(
            project=proj, head_type="equipment", allocated_amount=Decimal("500000.00")
        )
        ProjectBudgetHead.objects.create(
            project=proj, head_type="consumables", allocated_amount=Decimal("200000.00")
        )

    # Prefetch ensures constant query count (Project + CoPI prefetch + BudgetHead prefetch) <= 5 queries
    with assertNumQueries(3):
        resp = client.get("/api/v1/rspc/projects/")
        assert resp.status_code == 200
        assert len(resp.data) == 5
