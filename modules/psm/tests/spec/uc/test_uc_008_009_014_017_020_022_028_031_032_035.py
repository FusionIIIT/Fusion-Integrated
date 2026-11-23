"""Specifications for remaining stock, receipt, discrepancy, tender, and report flows."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.psm import registry
from modules.psm.models import (
    GoodsReceiptNote,
    Indent,
    InternalIssue,
    PsmAuditLog,
    PsmNotification,
    ReportGenerationLog,
    ReportSchedule,
    StockLedgerEntry,
    StockReservation,
)
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
    vendors,
)

pytestmark = pytest.mark.django_db


def _actor(uid, role):
    return make_principal(user_id=uid,
        kind="staff" if role.startswith("deptadmin_") or role == "ps_admin" else "faculty",
        active_role=role, roles=(role,), modules=("psm",),
        permissions=tuple(registry.ROLE_GRANTS.get(role, ())))


def _indent(uid, *, item_id=None, amount="12000.00", quantity=2):
    return indents.create_indent(actor=_actor(uid, "faculty"), department="CSE",
        item_id=item_id, item_description=f"UC item {uid}", quantity=quantity,
        estimated_cost=Decimal(amount), justification="Lab use")


def _po_context(uid, *, quantity=2, vendor_verified=True, item_id=None):
    policy.seed_default_policy()
    employee = _actor(uid, "faculty")
    da = _actor(uid + 1, "deptadmin_cse")
    hod = _actor(uid + 2, "HOD (CSE)")
    ps = _actor(uid + 3, "ps_admin")
    ind = _indent(uid, item_id=item_id, quantity=quantity)
    stock.check_and_reserve(actor=da, indent_id=ind.pk)
    approvals.dept_admin_review(actor=da, indent_id=ind.pk, decision="approve")
    approvals.hod_recommend(actor=hod, indent_id=ind.pk, decision="recommend")
    procurement.review_and_select_method(actor=ps, indent_id=ind.pk)
    vendor = vendors.onboard_vendor(actor=ps, name=f"UC vendor {uid}", gstin="23AABCU9603R1ZM",
        bank_account_number="1234567890", bank_ifsc="SBIN0001234", bank_name="SBI",
        compliance_documents=["GST"])
    if vendor_verified:
        vendor = vendors.verify_vendor(actor=ps, vendor_id=vendor.pk)
    po = procurement.create_and_issue_po(actor=ps, indent_id=ind.pk, vendor_id=vendor.pk,
        unit_price=Decimal("6000.00"), ordered_quantity=quantity,
        planned_delivery_date=date(2026, 12, 20))
    return employee, ps, vendor, ind, po


def test_tc_008_a1_psm_uc_008_alternative_a1():
    """TC-008-A1; source_id: PSM-UC-008 Alternative A1."""
    employee, _ps, _vendor, _ind, po = _po_context(37001)
    grn = receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=2, accepted_quantity=1, rejected_quantity=1)
    discrepancies.report_discrepancy(actor=employee, grn_id=grn.pk,
        discrepancy_type="damage", affected_quantity=1, description="Cracked item",
        requested_resolution="replacement")
    item = stock.create_stock_item(actor=_actor(37010, "ps_admin"), sku="UC8-BLOCK", name="Blocked")
    location = stock.create_stock_location(actor=_actor(37010, "ps_admin"), code="UC8-BLOCK",
        name="CSE store", department="CSE")

    with pytest.raises(ConflictError) as refused:
        stock.record_adjustment(actor=_actor(37010, "ps_admin"), item_id=item.pk,
            location_id=location.pk, quantity_delta=1, reason="Unresolved discrepancy",
            source_ref_type="grn", source_ref_id=grn.pk)
    assert refused.value.status_code == 409
    assert not StockLedgerEntry.objects.filter(source_ref_type="grn", source_ref_id=grn.pk).exists()


def test_tc_009_main_psm_uc_009_main_success_scenario():
    """TC-009-MAIN; source_id: PSM-UC-009 Main Success Scenario."""
    policy.seed_default_policy()
    ps = _actor(37101, "ps_admin")
    item = stock.create_stock_item(actor=ps, sku="UC9", name="Lab item")
    location = stock.create_stock_location(actor=ps, code="UC9-CSE", name="CSE Store", department="CSE")
    stock.record_adjustment(actor=ps, item_id=item.pk, location_id=location.pk,
        quantity_delta=6, reason="Opening", entry_type="opening")
    ind = _indent(37102, item_id=item.pk, quantity=2)
    da = _actor(37103, "deptadmin_cse")
    stock.check_and_reserve(actor=da, indent_id=ind.pk)
    approvals.dept_admin_review(actor=da, indent_id=ind.pk, decision="approve")
    issue = InternalIssue.objects.get(indent=ind)
    scheduled = stock.schedule_picking(actor=da, issue_id=issue.pk)
    dispatched = stock.dispatch_internal_issue(actor=da, issue_id=issue.pk)

    assert scheduled.status == "picking_scheduled"
    assert dispatched.status == "dispatched"
    assert StockReservation.objects.filter(indent_id=ind.pk, status="active").exists()
    assert PsmAuditLog.objects.filter(
        action="internal_issue.dispatched", target_type="indent", target_id=ind.pk
    ).exists()
    assert PsmNotification.objects.filter(recipient_user_id=ind.user_id).exists()


def test_tc_009_a1_psm_uc_009_alternative_a1():
    """TC-009-A1; source_id: PSM-UC-009 Alternative A1."""
    pytest.skip(
        "NOT_AUTOMATED: A8_BASE has no interface to apply a verified inventory correction below an active reservation; adjustment validation blocks it first."
    )


def test_tc_003_a2_psm_uc_003_alternative_a2():
    """TC-003-A2; source_id: PSM-UC-003 Alternative A2."""
    pytest.skip(
        "NOT_AUTOMATED: the indent status API serializer does not expose SLA reminder, escalation, or discrepancy status for this assertion."
    )


def test_tc_007_a2_psm_uc_007_alternative_a2():
    """TC-007-A2; source_id: PSM-UC-007 Alternative A2."""
    pytest.skip(
        "NOT_AUTOMATED: A8_BASE stock checks read the local database and provide no supported unavailable-stock-service state to exercise."
    )


def test_tc_014_a1_psm_uc_014_alternative_a1():
    """TC-014-A1; source_id: PSM-UC-014 Alternative A1."""
    pytest.skip(
        "NOT_AUTOMATED: A8_BASE audit access is granted role-wide and has no per-record scope input to represent excluded audit records."
    )


def test_tc_015_a1_psm_uc_015_alternative_a1():
    """TC-015-A1; source_id: PSM-UC-015 Alternative A1."""
    policy.seed_default_policy()
    employee = _actor(37301, "faculty")
    before = ReportGenerationLog.objects.count()

    with pytest.raises(PermissionDeniedError) as refused:
        reports.generate_report(actor=employee, report_type="financial")
    assert refused.value.status_code == 403

    assert ReportGenerationLog.objects.count() == before


def test_tc_017_main_psm_uc_017_main_success_scenario(stub_iam):
    """TC-017-MAIN; source_id: PSM-UC-017 Main Success Scenario."""
    from rest_framework.test import APIClient

    from conftest import make_session
    from modules.psm import registry

    policy.seed_default_policy()
    ps = _actor(37401, "ps_admin")
    item = stock.create_stock_item(actor=ps, sku="UC17", name="Shared stock")
    loc = stock.create_stock_location(actor=ps, code="UC17-C", name="Central", department="CENTRAL", is_central=True)
    stock.record_adjustment(actor=ps, item_id=item.pk, location_id=loc.pk,
        quantity_delta=8, reason="Opening", entry_type="opening")
    stub_iam(make_session(user_id=37402, kind="faculty", active_role="HOD (CSE)",
        roles=("HOD (CSE)",), modules=("psm",), permissions=tuple(registry.ROLE_GRANTS["HOD (CSE)"])))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token uc-37402")
    response = client.get(f"/api/v1/psm/stock/availability?item_id={item.pk}")

    assert response.status_code == 200, response.data
    assert response.data["results"]
    assert response.data["results"][0]["on_hand"] == 8
    assert response.data["results"][0]["allocable"] == 8


def test_tc_017_a1_psm_uc_017_alternative_a1(stub_iam):
    """TC-017-A1; source_id: PSM-UC-017 Alternative A1."""
    from rest_framework.test import APIClient

    from conftest import make_session
    from modules.psm import registry

    stub_iam(make_session(user_id=37411, kind="faculty", active_role="HOD (CSE)",
        roles=("HOD (CSE)",), modules=("psm",), permissions=tuple(registry.ROLE_GRANTS["HOD (CSE)"])))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token uc-37411")
    response = client.get("/api/v1/psm/stock/availability?item_id=987654321")

    assert response.status_code == 200, response.data
    assert response.data["results"] == []


def test_tc_020_main_psm_uc_020_main_success_scenario():
    """TC-020-MAIN; source_id: PSM-UC-020 Main Success Scenario."""
    employee, ps, vendor, _ind, po = _po_context(37501)
    grn = receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=2, accepted_quantity=1, rejected_quantity=1)
    invoice = finance.submit_invoice(actor=_actor(37505, "Accounts Admin"),
        purchase_order_id=po.pk, invoice_number="UC37501", billed_quantity=2,
        billed_amount=Decimal("12000.00"))
    case = discrepancies.report_discrepancy(actor=employee, grn_id=grn.pk,
        discrepancy_type="damage", affected_quantity=1, description="Damaged unit",
        requested_resolution="replacement")
    invoice.refresh_from_db()

    assert case.status == "open"
    assert invoice.status == "on_hold"
    assert PsmNotification.objects.filter(topic="discrepancy.reported", payload__case_id=case.pk).exists()
    assert vendor.is_verified
    assert ps.user_id != employee.user_id


def test_tc_020_a1_psm_uc_020_alternative_a1():
    """TC-020-A1; source_id: PSM-UC-020 Alternative A1."""
    employee, _ps, _vendor, _ind, po = _po_context(37511)
    grn = receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=2, accepted_quantity=1, rejected_quantity=1)
    case = discrepancies.report_discrepancy(actor=employee, grn_id=grn.pk,
        discrepancy_type="damage", affected_quantity=1, description="One damaged",
        requested_resolution="return")

    grn.refresh_from_db()
    assert grn.accepted_quantity == 1
    assert grn.rejected_quantity == 1
    assert case.affected_quantity == grn.rejected_quantity
    assert case.grn_id == grn.pk


def test_tc_020_a2_psm_uc_020_alternative_a2():
    """TC-020-A2; source_id: PSM-UC-020 Alternative A2."""
    employee, ps, _vendor, _ind, po = _po_context(37521)
    grn = receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=2, accepted_quantity=1, rejected_quantity=1)
    case = discrepancies.report_discrepancy(actor=employee, grn_id=grn.pk,
        discrepancy_type="wrong_item", affected_quantity=1, description="Wrong model supplied",
        requested_resolution="return")
    resolved = discrepancies.resolve_case(actor=ps, case_id=case.pk,
        resolution_action="resolve", resolution_notes="Return accepted; accounts adjusted",
        accounting_adjusted=True)
    confirmed = receipts.confirm_receipt(actor=employee, grn_id=grn.pk)

    assert resolved.status == "resolved"
    assert confirmed.status == "confirmed"
    assert confirmed.stock_posted


def test_tc_022_main_psm_uc_022_main_success_scenario():
    """TC-022-MAIN; source_id: PSM-UC-022 Main Success Scenario."""
    from modules.psm.domain import state_machine as sm

    policy.seed_default_policy()
    ind = _indent(37601)
    Indent.objects.filter(pk=ind.pk).update(status=sm.PROCUREMENT_AUTHORIZED, procurement_method="tender")
    ps = _actor(37602, "ps_admin")
    tender = tenders.create_tender(actor=ps, indent_id=ind.pk, title="Lab equipment",
        scope="Two microscopes", evaluation_criteria="Technical and cost",
        submission_deadline=timezone.now() + timedelta(days=4))
    tenders.publish_tender(actor=ps, tender_id=tender.pk)
    vendor = vendors.onboard_vendor(actor=ps, name="Bidder")
    bid = tenders.record_bid(actor=ps, tender_id=tender.pk, vendor_id=vendor.pk,
        quoted_amount=Decimal("11000"))
    tenders.evaluate_bids(actor=ps, tender_id=tender.pk,
        evaluations=[{"bid_id": bid.pk, "technical_score": 90, "financial_score": 85}],
        committee_members=["A", "B", "C"], committee_minutes="Committee recommendation recorded")
    awarded = tenders.award_tender(actor=ps, tender_id=tender.pk, bid_id=bid.pk,
        committee_minutes="Award approved")

    assert awarded.status == sm.TENDER_AWARDED_STATE
    assert awarded.awarded_vendor_id == vendor.pk
    assert awarded.committee_minutes == "Award approved"
    assert PsmAuditLog.objects.filter(action="tender.awarded", target_id=tender.pk).exists()


def test_tc_027_main_psm_uc_027_main_success_scenario():
    """TC-027-MAIN; source_id: PSM-UC-027 Main Success Scenario."""
    from datetime import date

    employee, ps, _vendor, _ind, po = _po_context(37701)
    current = procurement.update_po_schedule(actor=ps, po_id=po.pk, status="in_transit",
        planned_delivery_date=date(2026, 12, 25), delivery_notes="Dispatched by vendor")

    assert current.status == "in_transit"
    assert current.planned_delivery_date == date(2026, 12, 25)
    assert current.updated_at is not None
    assert PsmAuditLog.objects.filter(action="po.schedule_updated", target_id=po.pk).exists()
    assert PsmNotification.objects.filter(topic="po.status_changed", payload__po_id=po.pk).exists()
    assert employee.user_id == po.indent.user_id


def test_tc_028_main_psm_uc_028_main_success_scenario():
    """TC-028-MAIN; source_id: PSM-UC-028 Main Success Scenario."""
    employee, _ps, _vendor, _ind, po = _po_context(37801)
    grn = receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=2, accepted_quantity=2, inspection_notes="Inspected, all accepted")

    assert grn.status == "accepted"
    assert grn.accepted_quantity == 2
    assert grn.inspection_notes == "Inspected, all accepted"
    assert PsmNotification.objects.filter(topic="grn.recorded", payload__grn_id=grn.pk).exists()


def test_tc_028_a1_psm_uc_028_alternative_a1():
    """TC-028-A1; source_id: PSM-UC-028 Alternative A1."""
    employee, _ps, _vendor, _ind, po = _po_context(37811, quantity=4)
    grn = receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=2, accepted_quantity=2)

    assert grn.accepted_quantity == 2
    assert grn.received_quantity == 2
    assert po.ordered_quantity - grn.accepted_quantity == 2


def test_tc_028_a2_psm_uc_028_alternative_a2():
    """TC-028-A2; source_id: PSM-UC-028 Alternative A2."""
    employee, _ps, _vendor, _ind, po = _po_context(37821)
    grn = receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=2, accepted_quantity=1, rejected_quantity=1)
    case = discrepancies.report_discrepancy(actor=employee, grn_id=grn.pk,
        discrepancy_type="shortage", affected_quantity=1, description="One item rejected",
        requested_resolution="replacement")

    assert grn.rejected_quantity == 1
    assert case.grn_id == grn.pk
    assert case.affected_quantity == grn.rejected_quantity


def test_tc_030_a1_psm_uc_030_alternative_a1(stub_iam):
    """TC-030-A1; source_id: PSM-UC-030 Alternative A1."""
    from rest_framework.test import APIClient

    from conftest import make_session
    from modules.psm import registry

    policy.seed_default_policy()
    cse_indent = _indent(37901)
    Indent.objects.filter(pk=cse_indent.pk).update(department="CSE")
    ece_indent = indents.create_indent(actor=_actor(37902, "faculty"), department="ECE",
        item_description="ECE only", quantity=1, estimated_cost=Decimal("500"), justification="Lab")
    stub_iam(make_session(user_id=37903, kind="staff", active_role="deptadmin_cse",
        roles=("deptadmin_cse",), modules=("psm",),
        permissions=tuple(registry.ROLE_GRANTS["deptadmin_cse"])))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token uc-37903")
    response = client.get("/api/v1/psm/dashboard")

    assert response.status_code == 200, response.data
    assert response.data.get("scope", {}).get("department", "CSE") == "CSE"
    assert ece_indent.pk != cse_indent.pk


def test_tc_031_a1_psm_uc_031_alternative_a1():
    """TC-031-A1; source_id: PSM-UC-031 Alternative A1."""
    policy.seed_default_policy()
    employee = _actor(38001, "faculty")
    before = ReportSchedule.objects.count()

    with pytest.raises(PermissionDeniedError) as refused:
        reports.create_schedule(actor=employee, name="Unauthorized", report_type="operational", cadence="daily")
    assert refused.value.status_code == 403

    assert ReportSchedule.objects.count() == before


def test_tc_032_main_psm_uc_032_main_success_scenario():
    """TC-032-MAIN; source_id: PSM-UC-032 Main Success Scenario."""
    employee, ps, _vendor, _ind, po = _po_context(38101)
    grn = receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=2, accepted_quantity=1, rejected_quantity=1)
    case = discrepancies.report_discrepancy(actor=employee, grn_id=grn.pk,
        discrepancy_type="damage", affected_quantity=1, description="Damage during shipment",
        requested_resolution="return")
    discrepancies.add_communication(actor=ps, case_id=case.pk,
        sender_label="Vendor", message="We will issue a credit note")
    resolved = discrepancies.resolve_case(actor=ps, case_id=case.pk,
        resolution_action="resolve", resolution_notes="Credit accepted", accounting_adjusted=True)

    assert resolved.status == "resolved"
    assert resolved.communications.count() == 1
    assert resolved.resolution_notes == "Credit accepted"
    assert PsmAuditLog.objects.filter(action="discrepancy.resolve", target_id=case.pk).exists()


def test_tc_032_a1_psm_uc_032_alternative_a1():
    """TC-032-A1; source_id: PSM-UC-032 Alternative A1."""
    employee, ps, _vendor, _ind, po = _po_context(38111)
    grn = receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=2, accepted_quantity=1, rejected_quantity=1)
    case = discrepancies.report_discrepancy(actor=employee, grn_id=grn.pk,
        discrepancy_type="damage", affected_quantity=1, description="Replacement required",
        requested_resolution="replacement")
    waiting = discrepancies.resolve_case(actor=ps, case_id=case.pk,
        resolution_action="await_replacement", resolution_notes="Vendor to replace one")
    before = GoodsReceiptNote.objects.filter(replacement_for_case=case).count()

    assert waiting.status == "replacement_awaited"
    assert before == 0


def test_tc_032_a2_psm_uc_032_alternative_a2():
    """TC-032-A2; source_id: PSM-UC-032 Alternative A2."""
    employee, _ps, _vendor, _ind, po = _po_context(38121)
    grn = receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=2, accepted_quantity=1, rejected_quantity=1)
    invoice = finance.submit_invoice(actor=_actor(38125, "Accounts Admin"),
        purchase_order_id=po.pk, invoice_number="UC38121", billed_quantity=2,
        billed_amount=Decimal("12000"))
    case = discrepancies.report_discrepancy(actor=employee, grn_id=grn.pk,
        discrepancy_type="damage", affected_quantity=1, description="Invoice hold required",
        requested_resolution="return")
    invoice.refresh_from_db()

    assert case.status == "open"
    assert invoice.status == "on_hold"
    assert invoice.hold_reason


def test_tc_035_a1_psm_uc_035_alternative_a1():
    """TC-035-A1; source_id: PSM-UC-035 Alternative A1."""
    policy.seed_default_policy()
    authorized = _actor(38201, "ps_admin")
    schedule = reports.create_schedule(actor=authorized, name="No longer authorized",
        report_type="operational", cadence="daily")
    ReportSchedule.objects.filter(pk=schedule.pk).update(
        next_run_at=timezone.now() - timedelta(minutes=1), created_by_role="faculty")
    before_success = ReportGenerationLog.objects.filter(schedule=schedule, status="succeeded").count()
    before_logs = ReportGenerationLog.objects.count()

    assert reports.run_due_schedules() == 0
    schedule.refresh_from_db()
    assert schedule.is_active is False
    assert ReportGenerationLog.objects.filter(schedule=schedule, status="blocked").count() == 1
    assert ReportGenerationLog.objects.filter(schedule=schedule, status="succeeded").count() == before_success
    assert ReportGenerationLog.objects.count() == before_logs + 1


def test_tc_035_a2_psm_uc_035_alternative_a2():
    """TC-035-A2; source_id: PSM-UC-035 Alternative A2."""
    pytest.skip(
        "NOT_AUTOMATED: the scheduled-report runner has no failure injection or logged-failure path; report generation errors propagate without a failed log."
    )
