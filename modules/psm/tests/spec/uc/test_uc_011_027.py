"""Approval, final authorization, procurement, and PO use-case tests."""

from datetime import date
from decimal import Decimal

import pytest

from conftest import make_principal
from core.api.exceptions import ConflictError, DomainError
from modules.psm.models import IndentTransition, PsmAuditLog, PsmNotification
from modules.psm.services import approvals, indents, policy, procurement, stock, vendors

pytestmark = pytest.mark.django_db


def _actor(uid, role):
    return make_principal(
        user_id=uid,
        kind="staff" if role.startswith("deptadmin_") or role == "ps_admin" else "faculty",
        active_role=role,
        roles=(role,),
        modules=("psm",),
    )


def _indent(uid, amount="40000.00", item="Projector"):
    return indents.create_indent(
        actor=_actor(uid, "faculty"), department="CSE", item_description=item,
        quantity=2, estimated_cost=Decimal(amount), justification="Lecture hall upgrade",
    )


def _reviewed_indent(uid, amount="40000.00"):
    ind = _indent(uid, amount)
    da = _actor(uid + 1, "deptadmin_cse")
    stock.check_and_reserve(actor=da, indent_id=ind.pk)
    approvals.dept_admin_review(actor=da, indent_id=ind.pk, decision="approve", priority="high")
    approvals.hod_recommend(actor=_actor(uid + 2, "HOD (CSE)"), indent_id=ind.pk, decision="recommend")
    return ind


def _eligible_for_po(uid, *, verified=True):
    policy.seed_default_policy()
    ind = _reviewed_indent(uid)
    ps = _actor(uid + 3, "ps_admin")
    procurement.review_and_select_method(actor=ps, indent_id=ind.pk)
    vendor = vendors.onboard_vendor(actor=ps, name=f"PO Vendor {uid}", gstin="23AABCU9603R1ZM",
        bank_account_number="1234567890", bank_ifsc="SBIN0001234", bank_name="SBI",
        compliance_documents=["GST"])
    if verified:
        vendor = vendors.verify_vendor(actor=ps, vendor_id=vendor.pk)
    return ind, ps, vendor


def test_tc_011_main_psm_uc_011_main_success_scenario():
    """TC-011-MAIN; source_id: PSM-UC-011 Main Success Scenario."""
    policy.seed_default_policy()
    ind = _indent(35001)
    stock.check_and_reserve(actor=_actor(35002, "deptadmin_cse"), indent_id=ind.pk)
    reviewed = approvals.dept_admin_review(actor=_actor(35002, "deptadmin_cse"),
        indent_id=ind.pk, decision="approve", priority="critical")

    assert reviewed.status == "department_reviewed"
    assert reviewed.priority == "critical"
    assert IndentTransition.objects.filter(indent=ind, to_status=reviewed.status).exists()
    assert PsmNotification.objects.filter(recipient_user_id=ind.user_id, topic="indent.reviewed").exists()


def test_tc_011_a1_psm_uc_011_alternative_a1():
    """TC-011-A1; source_id: PSM-UC-011 Alternative A1."""
    policy.seed_default_policy()
    ind = _indent(35011)
    stock.check_and_reserve(actor=_actor(35012, "deptadmin_cse"), indent_id=ind.pk)
    before = ind.status

    with pytest.raises(DomainError) as refused:
        approvals.dept_admin_review(actor=_actor(35012, "deptadmin_cse"),
            indent_id=ind.pk, decision="reject", reason="  ")
    assert refused.value.status_code == 422
    ind.refresh_from_db()
    assert ind.status == "external_required"
    assert before == "submitted"
    rejected = approvals.dept_admin_review(actor=_actor(35012, "deptadmin_cse"),
        indent_id=ind.pk, decision="reject", reason="No budget")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "No budget"


def test_tc_011_a2_psm_uc_011_alternative_a2():
    """TC-011-A2; source_id: PSM-UC-011 Alternative A2."""
    policy.seed_default_policy()
    owner = _actor(35021, "faculty")
    first = indents.create_indent(actor=owner, department="CSE", item_description="Repeater",
        quantity=1, estimated_cost=Decimal("4000"), justification="Lab")
    duplicate = indents.create_indent(actor=owner, department="CSE", item_description="Repeater",
        quantity=1, estimated_cost=Decimal("4000"), justification="Second lab")
    assert duplicate.is_duplicate_flagged
    assert duplicate.status == "submitted"
    stock.check_and_reserve(actor=_actor(35022, "deptadmin_cse"), indent_id=duplicate.pk)
    reviewed = approvals.dept_admin_review(actor=_actor(35022, "deptadmin_cse"),
        indent_id=duplicate.pk, decision="approve")
    first.refresh_from_db()
    assert reviewed.status != "cancelled"
    assert first.status == "submitted"
    assert reviewed.duplicate_reviewed


def test_tc_012_main_psm_uc_012_main_success_scenario():
    """TC-012-MAIN; source_id: PSM-UC-012 Main Success Scenario."""
    policy.seed_default_policy()
    ind = _reviewed_indent(35101, amount="150000.00")
    ps = _actor(35104, "ps_admin")
    selected = procurement.review_and_select_method(actor=ps, indent_id=ind.pk)
    assert selected.status == "awaiting_final_approval"
    authorized = approvals.final_decision(actor=_actor(35105, "Director"),
        indent_id=ind.pk, decision="approve")

    assert authorized.status == "procurement_authorized"
    assert IndentTransition.objects.filter(indent=ind, to_status="procurement_authorized").exists()
    assert PsmNotification.objects.filter(recipient_user_id=ind.user_id, topic="indent.final_approve").exists()


def test_tc_012_a1_psm_uc_012_alternative_a1():
    """TC-012-A1; source_id: PSM-UC-012 Alternative A1."""
    policy.seed_default_policy()
    ind = _reviewed_indent(35111, amount="150000.00")
    procurement.review_and_select_method(actor=_actor(35114, "ps_admin"), indent_id=ind.pk)

    with pytest.raises(DomainError) as refused:
        approvals.final_decision(actor=_actor(35115, "Director"), indent_id=ind.pk,
            decision="reject", reason=" ")
    assert refused.value.status_code == 422
    rejected = approvals.final_decision(actor=_actor(35115, "Director"),
        indent_id=ind.pk, decision="reject", reason="Funding unavailable")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Funding unavailable"


def test_tc_016_main_psm_uc_016_main_success_scenario():
    """TC-016-MAIN; source_id: PSM-UC-016 Main Success Scenario."""
    policy.seed_default_policy()
    ind = _indent(35201)
    stock.check_and_reserve(actor=_actor(35202, "deptadmin_cse"), indent_id=ind.pk)
    approvals.dept_admin_review(actor=_actor(35202, "deptadmin_cse"), indent_id=ind.pk, decision="approve")
    recommended = approvals.hod_recommend(actor=_actor(35203, "HOD (CSE)"),
        indent_id=ind.pk, decision="recommend")

    assert recommended.status == "hod_recommended"
    assert IndentTransition.objects.filter(indent=ind, to_status="hod_recommended").exists()
    assert PsmNotification.objects.filter(recipient_user_id=ind.user_id, topic="indent.recommend").exists()


def test_tc_016_a1_psm_uc_016_alternative_a1():
    """TC-016-A1; source_id: PSM-UC-016 Alternative A1."""
    policy.seed_default_policy()
    ind = _indent(35211)
    stock.check_and_reserve(actor=_actor(35212, "deptadmin_cse"), indent_id=ind.pk)
    approvals.dept_admin_review(actor=_actor(35212, "deptadmin_cse"), indent_id=ind.pk, decision="approve")
    changes = approvals.hod_recommend(actor=_actor(35213, "HOD (CSE)"),
        indent_id=ind.pk, decision="request_changes", reason="Specify required connectors")

    assert changes.status == "changes_requested"
    modified = indents.modify_indent(actor=_actor(35211, "faculty"), indent_id=ind.pk,
        justification="Specify USB-C connectors")
    assert modified.status == "submitted"
    assert modified.version == 2


def test_tc_016_a2_psm_uc_016_alternative_a2():
    """TC-016-A2; source_id: PSM-UC-016 Alternative A2."""
    policy.seed_default_policy()
    ind = _indent(35221)
    stock.check_and_reserve(actor=_actor(35222, "deptadmin_cse"), indent_id=ind.pk)
    approvals.dept_admin_review(actor=_actor(35222, "deptadmin_cse"), indent_id=ind.pk, decision="approve")
    with pytest.raises(DomainError) as refused:
        approvals.hod_recommend(actor=_actor(35223, "HOD (CSE)"), indent_id=ind.pk,
            decision="reject", reason=" ")
    assert refused.value.status_code == 422
    rejected = approvals.hod_recommend(actor=_actor(35223, "HOD (CSE)"),
        indent_id=ind.pk, decision="reject", reason="Not justified")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Not justified"


def test_tc_025_main_psm_uc_025_main_success_scenario():
    """TC-025-MAIN; source_id: PSM-UC-025 Main Success Scenario."""
    policy.seed_default_policy()
    ind = _reviewed_indent(35301)
    reviewed = procurement.review_and_select_method(actor=_actor(35304, "ps_admin"), indent_id=ind.pk)

    assert reviewed.status == "procurement_authorized"
    assert reviewed.procurement_method == "direct"
    assert PsmNotification.objects.filter(recipient_user_id=ind.user_id,
        topic="indent.procurement_reviewed").exists()


def test_tc_025_a1_psm_uc_025_alternative_a1():
    """TC-025-A1; source_id: PSM-UC-025 Alternative A1."""
    policy.seed_default_policy()
    ind = _indent(35311)
    ps = _actor(35314, "ps_admin")
    vendor = vendors.onboard_vendor(actor=ps, name="Unverified before approvals")

    with pytest.raises(ConflictError) as refused:
        procurement.create_and_issue_po(actor=ps, indent_id=ind.pk, vendor_id=vendor.pk,
            unit_price=Decimal("1000"), planned_delivery_date=date(2026, 12, 20))
    assert refused.value.status_code == 409
    ind.refresh_from_db()
    assert ind.status == "submitted"
    assert not hasattr(ind, "purchase_order")


def test_tc_025_a2_psm_uc_025_alternative_a2():
    """TC-025-A2; source_id: PSM-UC-025 Alternative A2."""
    ind, ps, vendor = _eligible_for_po(35321, verified=False)

    with pytest.raises(ConflictError) as refused:
        procurement.create_and_issue_po(actor=ps, indent_id=ind.pk, vendor_id=vendor.pk,
            unit_price=Decimal("1000"), planned_delivery_date=date(2026, 12, 20))
    assert refused.value.status_code == 409
    ind.refresh_from_db()
    assert ind.status == "procurement_authorized"
    assert vendor.is_verified is False


def test_tc_026_main_psm_uc_026_main_success_scenario():
    """TC-026-MAIN; source_id: PSM-UC-026 Main Success Scenario."""
    ind, ps, vendor = _eligible_for_po(35401)
    po = procurement.create_and_issue_po(actor=ps, indent_id=ind.pk, vendor_id=vendor.pk,
        unit_price=Decimal("1000"), planned_delivery_date=date(2026, 12, 20))

    assert po.status == "issued"
    assert po.po_number
    assert PsmAuditLog.objects.filter(action="po.issued", target_id=po.pk).exists()
    assert PsmNotification.objects.filter(topic="po.issued", payload__po_id=po.pk).exists()


def test_tc_026_a1_psm_uc_026_alternative_a1():
    """TC-026-A1; source_id: PSM-UC-026 Alternative A1."""
    policy.seed_default_policy()
    ind = _indent(35411)
    ps = _actor(35414, "ps_admin")
    vendor = vendors.onboard_vendor(actor=ps, name="Authorized vendor", gstin="23AABCU9603R1ZM",
        bank_account_number="1234567890", bank_ifsc="SBIN0001234", bank_name="SBI",
        compliance_documents=["GST"])
    vendors.verify_vendor(actor=ps, vendor_id=vendor.pk)
    with pytest.raises(ConflictError) as refused:
        procurement.create_and_issue_po(actor=ps, indent_id=ind.pk, vendor_id=vendor.pk,
            unit_price=Decimal("1000"), planned_delivery_date=date(2026, 12, 20))
    assert refused.value.status_code == 409
    ind.refresh_from_db()
    assert ind.status == "submitted"


def test_tc_026_a2_psm_uc_026_alternative_a2():
    """TC-026-A2; source_id: PSM-UC-026 Alternative A2."""
    ind, ps, vendor = _eligible_for_po(35421, verified=False)
    with pytest.raises(ConflictError) as refused:
        procurement.create_and_issue_po(actor=ps, indent_id=ind.pk, vendor_id=vendor.pk,
            unit_price=Decimal("1000"), planned_delivery_date=date(2026, 12, 20))
    assert refused.value.status_code == 409
    assert not PsmAuditLog.objects.filter(action="po.issued", target_id=ind.pk).exists()


def test_tc_027_a1_psm_uc_027_alternative_a1(stub_iam):
    """TC-027-A1; source_id: PSM-UC-027 Alternative A1."""
    from rest_framework.test import APIClient

    from conftest import make_session
    from modules.psm import registry

    ind, ps, vendor = _eligible_for_po(35501)
    po = procurement.create_and_issue_po(actor=ps, indent_id=ind.pk, vendor_id=vendor.pk,
        unit_price=Decimal("1000"), planned_delivery_date=date(2026, 12, 20))
    before = (po.status, po.planned_delivery_date)
    stub_iam(make_session(user_id=35509, kind="faculty", active_role="faculty", roles=("faculty",),
        modules=("psm",), permissions=tuple(registry.ROLE_GRANTS["faculty"])))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token uc-35509")
    response = client.patch(f"/api/v1/psm/purchase-orders/{po.pk}",
        {"status": "in_transit", "delivery_notes": "Shipped"}, format="json")
    assert response.status_code == 403
    po.refresh_from_db()
    assert (po.status, po.planned_delivery_date) == before

