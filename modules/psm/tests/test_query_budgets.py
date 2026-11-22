# Query budget tests asserting constant SQL count at 2 rows vs. 12 rows (Step 5.8, R2-07).
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from modules.psm import registry
from modules.psm.services import (
    approvals,
    discrepancies,
    finance,
    indents,
    policy,
    procurement,
    receipts,
    reports,
    stock,
    tenders,
    transfers,
    vendors,
)

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
    # Seed non-zero rows across all 17 endpoints (R2-07) so N=2 vs N=12 tests real scaling.
    p_emp = make_principal(user_id=6010, kind="faculty", active_role="faculty", roles=("faculty",))
    p_da = make_principal(
        user_id=6011, kind="staff", active_role="deptadmin_cse", roles=("deptadmin_cse",)
    )
    p_hod = make_principal(
        user_id=6012, kind="faculty", active_role="HOD (CSE)", roles=("HOD (CSE)",)
    )
    p_ps = make_principal(
        user_id=6001,
        kind="staff",
        active_role="ps_admin",
        roles=("ps_admin",),
        modules=("psm",),
        permissions=tuple(registry.ROLE_GRANTS["ps_admin"]),
    )
    p_acc = make_principal(
        user_id=6013, kind="staff", active_role="Accounts Admin", roles=("Accounts Admin",)
    )
    loc_src = stock.create_stock_location(
        actor=p_ps,
        code=f"LOC-SRC-{start}",
        name=f"Central {start}",
        department="Stores",
        is_central=True,
    )
    loc_dst = stock.create_stock_location(
        actor=p_ps, code=f"LOC-DST-{start}", name=f"CSE {start}", department="CSE", is_central=False
    )
    for n in range(start, end):
        it = stock.create_stock_item(actor=p_ps, sku=f"SKU-{n}", name=f"Part {n}")
        stock.record_adjustment(
            actor=p_ps,
            item_id=it.pk,
            location_id=loc_src.pk,
            quantity_delta=20,
            reason="Init",
            entry_type="opening",
        )
        # Internal issue + transfer
        ind_int = indents.create_indent(
            actor=p_emp,
            department="CSE",
            item_id=it.pk,
            item_description=f"Internal {n}",
            quantity=2,
            estimated_cost=Decimal("500.00"),
            justification=f"Internal {n}",
        )
        stock.check_and_reserve(actor=p_da, indent_id=ind_int.pk)
        approvals.dept_admin_review(actor=p_da, indent_id=ind_int.pk, decision="approve")
        transfers.request_transfer(
            actor=p_ps,
            item_id=it.pk,
            source_location_id=loc_src.pk,
            destination_location_id=loc_dst.pk,
            quantity=1,
            notes=f"Transfer {n}",
        )
        # Vendor + direct PO + GRN + Discrepancy + Invoice
        v = vendors.onboard_vendor(
            actor=p_ps,
            name=f"Vendor {n}",
            code=f"VQB{n}",
            gstin="23ABCDE1234F1Z5",
            bank_account_number=f"10000000{n:04d}",
            bank_ifsc="SBIN0001234",
            bank_name="SBI",
            compliance_documents=["gst.pdf"],
        )
        vendors.verify_vendor(actor=p_ps, vendor_id=v.pk)
        ind_po = indents.create_indent(
            actor=p_emp,
            department="CSE",
            item_description=f"PO Item {n}",
            quantity=2,
            estimated_cost=Decimal("2000.00"),
            justification=f"PO {n}",
        )
        stock.check_and_reserve(actor=p_da, indent_id=ind_po.pk)
        approvals.dept_admin_review(actor=p_da, indent_id=ind_po.pk, decision="approve")
        approvals.hod_recommend(actor=p_hod, indent_id=ind_po.pk, decision="recommend")
        procurement.review_and_select_method(actor=p_ps, indent_id=ind_po.pk)
        po = procurement.create_and_issue_po(
            actor=p_ps,
            indent_id=ind_po.pk,
            vendor_id=v.pk,
            ordered_quantity=2,
            unit_price=Decimal("1000.00"),
            planned_delivery_date=date.today() + timedelta(days=5),
        )
        grn = receipts.record_grn(
            actor=p_emp,
            purchase_order_id=po.pk,
            received_quantity=2,
            accepted_quantity=1,
            rejected_quantity=1,
        )
        discrepancies.report_discrepancy(
            actor=p_emp,
            grn_id=grn.pk,
            discrepancy_type="damage",
            affected_quantity=1,
            description=f"Scratch {n}",
            requested_resolution="return",
        )
        finance.submit_invoice(
            actor=p_acc,
            purchase_order_id=po.pk,
            invoice_number=f"INV-QB-{n}",
            billed_quantity=2,
            billed_amount=Decimal("2000.00"),
        )
        # Tender + ReportSchedule
        ind_t = indents.create_indent(
            actor=p_emp,
            department="CSE",
            item_description=f"Tender Item {n}",
            quantity=1,
            estimated_cost=Decimal("75000.00"),
            justification=f"Tender {n}",
        )
        stock.check_and_reserve(actor=p_da, indent_id=ind_t.pk)
        approvals.dept_admin_review(actor=p_da, indent_id=ind_t.pk, decision="approve")
        approvals.hod_recommend(actor=p_hod, indent_id=ind_t.pk, decision="recommend")
        procurement.review_and_select_method(actor=p_ps, indent_id=ind_t.pk)
        tenders.create_tender(
            actor=p_ps,
            indent_id=ind_t.pk,
            title=f"Tender {n}",
            scope="Lab equip",
            evaluation_criteria="L1",
            submission_deadline=timezone.now() + timedelta(days=10),
        )
        reports.create_schedule(
            actor=p_ps, name=f"Sched {n}", report_type="operational", cadence="weekly", filters={}
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
        r_small = client.get(path)
        assert r_small.status_code == 200
    _seed_rows(2, 12)
    with CaptureQueriesContext(connection) as large:
        r_large = client.get(path)
        assert r_large.status_code == 200
    assert len(large) == len(small), f"{path}: {len(small)} queries at 2 rows vs {len(large)} at 12"
