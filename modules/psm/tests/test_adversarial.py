# Adversarial tests: self-approval, unverified vendor, unresolved discrepancy, CSV injection, missing policy (Step 5.11).
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import ConflictError
from modules.psm import registry
from modules.psm.services import (
    approvals,
    discrepancies,
    indents,
    policy,
    procurement,
    receipts,
    stock,
    vendors,
)

pytestmark = pytest.mark.django_db


def test_missing_policy_refuses_cleanly_with_409_not_500(stub_iam):
    # Step 2.8, BR-PSM-028
    stub_iam(
        make_session(
            user_id=8001,
            kind="faculty",
            active_role="faculty",
            roles=("faculty",),
            modules=("psm",),
            permissions=tuple(registry.ROLE_GRANTS["faculty"]),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token adv")
    r = c.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_description": "Cable",
            "quantity": 1,
            "estimated_cost": "500.00",
            "justification": "Lab",
        },
        format="json",
    )
    assert r.status_code == 409
    assert r.data["error"]["code"] == "policy_missing"


def test_approver_cannot_approve_own_indent():
    # Step 5.11: self-approval blocked across Dept Admin, HOD, PS Admin, Director.
    policy.seed_default_policy()
    p_da = make_principal(
        user_id=8010, kind="staff", active_role="deptadmin_cse", roles=("deptadmin_cse",)
    )
    ind = indents.create_indent(
        actor=p_da,
        department="CSE",
        item_description="Desk",
        quantity=1,
        estimated_cost=Decimal("5000.00"),
        justification="Office",
    )
    stock.check_and_reserve(actor=p_da, indent_id=ind.pk)
    with pytest.raises(ConflictError) as exc:
        approvals.dept_admin_review(actor=p_da, indent_id=ind.pk, decision="approve")
    assert exc.value.code == "self_approval_forbidden"


def test_unverified_vendor_blocked_at_po_and_payment():
    # BR-PSM-012, AFR-PSM-040, AFR-PSM-063, AFR-PSM-064
    policy.seed_default_policy()
    p_emp = make_principal(user_id=8020, kind="faculty", active_role="faculty", roles=("faculty",))
    p_da = make_principal(
        user_id=8021, kind="staff", active_role="deptadmin_cse", roles=("deptadmin_cse",)
    )
    p_hod = make_principal(
        user_id=8022, kind="faculty", active_role="HOD (CSE)", roles=("HOD (CSE)",)
    )
    p_ps = make_principal(user_id=8023, kind="staff", active_role="ps_admin", roles=("ps_admin",))
    v = vendors.onboard_vendor(actor=p_ps, name="Unverified Co")
    ind = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="Sensor",
        quantity=2,
        estimated_cost=Decimal("2000.00"),
        justification="Lab",
    )
    stock.check_and_reserve(actor=p_da, indent_id=ind.pk)
    approvals.dept_admin_review(actor=p_da, indent_id=ind.pk, decision="approve")
    approvals.hod_recommend(actor=p_hod, indent_id=ind.pk, decision="recommend")
    procurement.review_and_select_method(actor=p_ps, indent_id=ind.pk)
    with pytest.raises(ConflictError) as exc:
        procurement.create_and_issue_po(
            actor=p_ps,
            indent_id=ind.pk,
            vendor_id=v.pk,
            unit_price=Decimal("1000.00"),
            planned_delivery_date=date(2026, 12, 1),
        )
    assert exc.value.code == "vendor_unverified"


def test_unresolved_discrepancy_blocks_stock_posting_and_second_replacement():
    # BR-PSM-009, BR-PSM-018, BW-PSM-10
    policy.seed_default_policy()
    p_emp = make_principal(user_id=8030, kind="faculty", active_role="faculty", roles=("faculty",))
    p_da = make_principal(
        user_id=8031, kind="staff", active_role="deptadmin_cse", roles=("deptadmin_cse",)
    )
    p_hod = make_principal(
        user_id=8032, kind="faculty", active_role="HOD (CSE)", roles=("HOD (CSE)",)
    )
    p_ps = make_principal(user_id=8033, kind="staff", active_role="ps_admin", roles=("ps_admin",))
    v = vendors.onboard_vendor(
        actor=p_ps,
        name="GoodCo",
        gstin="23AABCU9603R1ZM",
        bank_account_number="1234567890",
        bank_ifsc="SBIN0001234",
        bank_name="SBI",
        compliance_documents=["GST"],
    )
    vendors.verify_vendor(actor=p_ps, vendor_id=v.pk)
    ind = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="Board",
        quantity=5,
        estimated_cost=Decimal("5000.00"),
        justification="Lab",
    )
    stock.check_and_reserve(actor=p_da, indent_id=ind.pk)
    approvals.dept_admin_review(actor=p_da, indent_id=ind.pk, decision="approve")
    approvals.hod_recommend(actor=p_hod, indent_id=ind.pk, decision="recommend")
    procurement.review_and_select_method(actor=p_ps, indent_id=ind.pk)
    po = procurement.create_and_issue_po(
        actor=p_ps,
        indent_id=ind.pk,
        vendor_id=v.pk,
        unit_price=Decimal("1000.00"),
        planned_delivery_date=date(2026, 12, 1),
    )
    grn = receipts.record_grn(
        actor=p_emp,
        purchase_order_id=po.pk,
        received_quantity=5,
        accepted_quantity=3,
        rejected_quantity=2,
    )
    case = discrepancies.report_discrepancy(
        actor=p_emp,
        grn_id=grn.pk,
        discrepancy_type="damage",
        affected_quantity=2,
        description="2 boards cracked",
        requested_resolution="replacement",
    )
    with pytest.raises(ConflictError) as exc_post:
        receipts.confirm_receipt(actor=p_emp, grn_id=grn.pk)
    assert exc_post.value.code == "unresolved_discrepancy"
    # First replacement traversal permitted (BW-PSM-10); second refused.
    discrepancies.resolve_case(
        actor=p_ps,
        case_id=case.pk,
        resolution_action="await_replacement",
        resolution_notes="Vendor sending 2 units",
    )
    with pytest.raises(ConflictError) as exc_rep:
        discrepancies.resolve_case(
            actor=p_ps,
            case_id=case.pk,
            resolution_action="await_replacement",
            resolution_notes="Second try",
        )
    assert exc_rep.value.code == "replacement_limit_reached"


def test_csv_export_escapes_formula_injection(stub_iam):
    # AFR-PSM-079, security-baseline 4.10
    policy.seed_default_policy()
    p_emp = make_principal(user_id=8040, kind="faculty", active_role="faculty", roles=("faculty",))
    indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="=CMD|' /C calc'!A0",
        quantity=1,
        estimated_cost=Decimal("500.00"),
        justification="Test",
    )
    stub_iam(
        make_session(
            user_id=8041,
            kind="staff",
            active_role="ps_admin",
            roles=("ps_admin",),
            modules=("psm",),
            permissions=tuple(registry.ROLE_GRANTS["ps_admin"]),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token csv")
    r = c.post("/api/v1/psm/reports/export", {"report_type": "operational"}, format="json")
    assert r.status_code == 200
    assert "'=CMD" in r.content.decode("utf-8")
