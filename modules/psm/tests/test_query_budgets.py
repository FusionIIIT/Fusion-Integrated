# Query budget tests asserting constant SQL count at 2 rows vs. 12 rows (Step 5.8).
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from modules.psm import registry
from modules.psm.services import indents, policy, stock, vendors

pytestmark = pytest.mark.django_db


def _ps_client(stub_iam):
    all_perms = tuple(code for code, _ in registry.PERMISSIONS)
    stub_iam(
        make_session(
            user_id=6001,
            kind="staff",
            active_role="ps_admin",
            roles=("ps_admin",),
            modules=("psm",),
            permissions=all_perms,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token qb")
    return c


def _seed_rows(start: int, end: int):
    p_emp = make_principal(user_id=6010, kind="faculty", active_role="faculty", roles=("faculty",))
    p_ps = make_principal(user_id=6001, kind="staff", active_role="ps_admin", roles=("ps_admin",))
    loc = stock.create_stock_location(
        actor=p_ps, code=f"LOC-{start}", name=f"Store {start}", department="CSE"
    )
    for n in range(start, end):
        indents.create_indent(
            actor=p_emp,
            department="CSE",
            item_description=f"Item {n}",
            quantity=1,
            estimated_cost=Decimal("1000.00"),
            justification=f"Need {n}",
        )
        vendors.onboard_vendor(actor=p_ps, name=f"Vendor {n}", code=f"V{n}")
        it = stock.create_stock_item(actor=p_ps, sku=f"SKU-{n}", name=f"Part {n}")
        stock.record_adjustment(
            actor=p_ps,
            item_id=it.pk,
            location_id=loc.pk,
            quantity_delta=5,
            reason="Init",
            entry_type="opening",
        )


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/psm/dashboard",
        "/api/v1/psm/indents",
        "/api/v1/psm/stock/items",
        "/api/v1/psm/stock/locations",
        "/api/v1/psm/stock/availability",
        "/api/v1/psm/internal-issues",
        "/api/v1/psm/transfers",
        "/api/v1/psm/vendors",
        "/api/v1/psm/tenders",
        "/api/v1/psm/purchase-orders",
        "/api/v1/psm/grns",
        "/api/v1/psm/discrepancies",
        "/api/v1/psm/invoices",
        "/api/v1/psm/reports/schedules",
        "/api/v1/psm/audit",
        "/api/v1/psm/notifications",
        "/api/v1/psm/policy",
    ],
)
def test_list_endpoint_query_count_is_constant_as_rows_grow(stub_iam, path):
    policy.seed_default_policy()
    _seed_rows(0, 2)
    client = _ps_client(stub_iam)
    with CaptureQueriesContext(connection) as small:
        assert client.get(path).status_code == 200
    _seed_rows(2, 12)
    with CaptureQueriesContext(connection) as large:
        assert client.get(path).status_code == 200
    assert len(large) == len(small), f"{path}: {len(small)} queries at 2 rows vs {len(large)} at 12"
