# Scoping isolation tests: foreign rows yield 404, never 403 (Step 5.6, BR-PSM-020).
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from modules.psm import registry
from modules.psm.services import indents, policy, stock, transfers

pytestmark = pytest.mark.django_db


def _as(stub_iam, *, uid: int, role: str):
    stub_iam(
        make_session(
            user_id=uid,
            kind="faculty",
            active_role=role,
            roles=(role,),
            modules=("psm",),
            permissions=tuple(registry.ROLE_GRANTS[role]),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token scope")
    return c


def test_employee_cannot_see_or_modify_another_employees_indent(stub_iam):
    # BR-PSM-020, AFR-PSM-012
    policy.seed_default_policy()
    p_a = make_principal(user_id=4001, kind="faculty", active_role="faculty", roles=("faculty",))
    ind_a = indents.create_indent(
        actor=p_a,
        department="CSE",
        item_description="Oscilloscope",
        quantity=1,
        estimated_cost=Decimal("15000.00"),
        justification="Lab",
    )
    c_b = _as(stub_iam, uid=4002, role="faculty")
    assert c_b.get("/api/v1/psm/indents").data["results"] == []
    assert c_b.get(f"/api/v1/psm/indents/{ind_a.pk}").status_code == 404
    assert (
        c_b.patch(f"/api/v1/psm/indents/{ind_a.pk}", {"quantity": 9}, format="json").status_code
        == 404
    )
    assert (
        c_b.post(f"/api/v1/psm/indents/{ind_a.pk}/withdraw", {}, format="json").status_code == 404
    )


def test_department_admin_isolated_to_own_department_including_reports(stub_iam):
    # BR-PSM-020, BR-PSM-024
    policy.seed_default_policy()
    p_cse = make_principal(user_id=4010, kind="faculty", active_role="faculty", roles=("faculty",))
    p_ece = make_principal(user_id=4011, kind="faculty", active_role="faculty", roles=("faculty",))
    ind_cse = indents.create_indent(
        actor=p_cse,
        department="CSE",
        item_description="GPU",
        quantity=1,
        estimated_cost=Decimal("40000.00"),
        justification="AI lab",
    )
    ind_ece = indents.create_indent(
        actor=p_ece,
        department="ECE",
        item_description="Spectrum Analyzer",
        quantity=1,
        estimated_cost=Decimal("40000.00"),
        justification="RF lab",
    )
    c_cse_admin = _as(stub_iam, uid=4020, role="deptadmin_cse")
    listed_ids = [r["id"] for r in c_cse_admin.get("/api/v1/psm/indents").data["results"]]
    assert ind_cse.pk in listed_ids
    assert ind_ece.pk not in listed_ids
    assert c_cse_admin.get(f"/api/v1/psm/indents/{ind_ece.pk}").status_code == 404
    # Even filtering explicitly for ECE returns 0 rows.
    r_filt = c_cse_admin.get("/api/v1/psm/indents?department=ECE")
    assert r_filt.status_code == 200 and r_filt.data["results"] == []
    # Reports respect scoping too.
    r_rep = c_cse_admin.post(
        "/api/v1/psm/reports/generate",
        {"report_type": "operational", "filters": {"department": "ECE"}},
        format="json",
    )
    assert r_rep.status_code == 200 and r_rep.data["row_count"] == 0


def test_transfer_isolation_between_departments(stub_iam):
    # BR-PSM-020, BW-PSM-08
    policy.seed_default_policy()
    p_ps = make_principal(user_id=4030, kind="staff", active_role="ps_admin", roles=("ps_admin",))
    item = stock.create_stock_item(actor=p_ps, sku="ISO-1", name="Router")
    loc_ece = stock.create_stock_location(
        actor=p_ps, code="ECE-S", name="ECE Store", department="ECE"
    )
    loc_me = stock.create_stock_location(actor=p_ps, code="ME-S", name="ME Store", department="ME")
    stock.record_adjustment(
        actor=p_ps,
        item_id=item.pk,
        location_id=loc_ece.pk,
        quantity_delta=10,
        reason="Opening",
        entry_type="opening",
    )
    p_me = make_principal(
        user_id=4031, kind="staff", active_role="deptadmin_me", roles=("deptadmin_me",)
    )
    trf = transfers.request_transfer(
        actor=p_me,
        item_id=item.pk,
        source_location_id=loc_ece.pk,
        destination_location_id=loc_me.pk,
        quantity=3,
    )
    c_cse = _as(stub_iam, uid=4032, role="deptadmin_cse")
    assert c_cse.get("/api/v1/psm/transfers").data["results"] == []
    assert (
        c_cse.post(f"/api/v1/psm/transfers/{trf.pk}/dispatch", {}, format="json").status_code == 404
    )
