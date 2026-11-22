# Comprehensive traceability and branch-coverage tests for PSM (Steps 5.4, 5.10, 5.13).
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.psm import contracts, registry
from modules.psm.models import StockLedgerEntry
from modules.psm.selectors import reports as report_sel
from modules.psm.selectors import scoping
from modules.psm.selectors import stock as stock_sel
from modules.psm.services import (
    approvals,
    discrepancies,
    indents,
    policy,
    procurement,
    receipts,
    reports,
    stock,
    transfers,
    vendors,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, uid: int, role: str) -> APIClient:
    stub_iam(
        make_session(
            user_id=uid,
            kind="faculty" if role in ("faculty", "HOD (CSE)") else "staff",
            active_role=role,
            roles=(role,),
            modules=("psm",),
            permissions=tuple(registry.ROLE_GRANTS[role]),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token u{uid}")
    return c


def _make_p(uid: int, role: str):
    return make_principal(
        user_id=uid,
        kind="faculty" if role in ("faculty", "HOD (CSE)") else "staff",
        active_role=role,
        roles=(role,),
        modules=("psm",),
        permissions=tuple(registry.ROLE_GRANTS[role]),
    )


def _setup_actors():
    return (
        _make_p(9101, "faculty"),
        _make_p(9102, "deptadmin_cse"),
        _make_p(9103, "HOD (CSE)"),
        _make_p(9104, "ps_admin"),
        _make_p(9105, "Director"),
        _make_p(9106, "Accounts Admin"),
        _make_p(9107, "Auditor"),
    )


def test_http_endpoints_invoices_reports_schedules_audit_notifications_policy(stub_iam):
    # CFR-PSM-009, CFR-PSM-010, CFR-PSM-016, CFR-PSM-018, CFR-PSM-019, CFR-PSM-020
    # AFR-PSM-057, AFR-PSM-058, AFR-PSM-059, AFR-PSM-060, AFR-PSM-061, AFR-PSM-065, AFR-PSM-066
    # AFR-PSM-068, AFR-PSM-069, AFR-PSM-070, AFR-PSM-071, AFR-PSM-072, AFR-PSM-073, AFR-PSM-074
    # AFR-PSM-075, AFR-PSM-076, AFR-PSM-077, AFR-PSM-078, AFR-PSM-081, AFR-PSM-087, AFR-PSM-088
    # AFR-PSM-089, AFR-PSM-091, AFR-PSM-092, PSM-UC-029
    p_emp, p_dept, p_hod, p_ps, _p_dir, _p_acc, _p_aud = _setup_actors()
    policy.seed_default_policy()
    c_dir = _client(stub_iam, uid=9105, role="Director")

    # Policy GET + POST (CFR-PSM-019, AFR-PSM-087, AFR-PSM-088, AFR-PSM-089)
    r_pol_get = c_dir.get("/api/v1/psm/policy")
    assert r_pol_get.status_code == 200
    assert len(r_pol_get.json()["results"]) >= 1
    c_ps = _client(stub_iam, uid=9104, role="ps_admin")
    r_pol_post = c_ps.post(
        "/api/v1/psm/policy",
        {
            "version": "2026.99",
            "effective_from": timezone.now().isoformat(),
            "direct_limit": "50000.00",
            "final_approval_threshold": "100000.00",
            "high_priority_direct_allowed": True,
            "modifiable_states": [
                "draft",
                "submitted",
                "changes_requested",
                "department_reviewed",
            ],
            "withdrawable_states": [
                "draft",
                "submitted",
                "changes_requested",
                "department_reviewed",
            ],
            "sla_normal_reminder_hours": 24,
            "sla_normal_escalation_hours": 48,
            "sla_high_reminder_hours": 12,
            "sla_high_escalation_hours": 24,
            "partial_payment_enabled": True,
            "duplicate_window_days": 14,
            "is_active": True,
        },
        format="json",
    )
    assert r_pol_post.status_code == 201

    # Full procurement setup for invoice hold + verify + pay HTTP endpoints
    v = vendors.onboard_vendor(
        actor=p_ps,
        name="HTTP Vendor",
        gstin="23ABCDE1234F1Z5",
        bank_account_number="112233445566",
        bank_ifsc="SBIN0001234",
        bank_name="SBI",
        compliance_documents=["gst.pdf"],
        contact_email="http@v.test",
    )
    vendors.verify_vendor(actor=p_ps, vendor_id=v.pk)
    ind = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="4K Monitor",
        quantity=2,
        estimated_cost=Decimal("20000.00"),
        justification="Lab display",
        submit=True,
    )
    stock.check_and_reserve(actor=p_dept, indent_id=ind.pk)
    approvals.dept_admin_review(
        actor=p_dept, indent_id=ind.pk, decision="approve", priority="normal"
    )
    approvals.hod_recommend(actor=p_hod, indent_id=ind.pk, decision="recommend")
    procurement.review_and_select_method(actor=p_ps, indent_id=ind.pk)
    po = procurement.create_and_issue_po(
        actor=p_ps,
        indent_id=ind.pk,
        vendor_id=v.pk,
        ordered_quantity=2,
        unit_price=Decimal("10000.00"),
        planned_delivery_date=date.today() + timedelta(days=7),
    )
    grn = receipts.record_grn(
        actor=p_emp, purchase_order_id=po.pk, received_quantity=2, accepted_quantity=2
    )
    receipts.confirm_receipt(actor=p_emp, grn_id=grn.pk)

    # Invoice list + create + hold + verify + pay via HTTP (AFR-PSM-057..061, PSM-UC-029)
    c_acc = _client(stub_iam, uid=9106, role="Accounts Admin")
    r_inv_create = c_acc.post(
        "/api/v1/psm/invoices",
        {
            "purchase_order_id": po.pk,
            "invoice_number": "INV-HTTP-1",
            "billed_quantity": 2,
            "billed_amount": "20000.00",
        },
        format="json",
    )
    assert r_inv_create.status_code == 201
    inv_id = r_inv_create.json()["id"]
    assert c_acc.get("/api/v1/psm/invoices").status_code == 200
    r_hold = c_acc.post(
        f"/api/v1/psm/invoices/{inv_id}/hold", {"reason": "Check GST"}, format="json"
    )
    assert r_hold.status_code == 200
    assert r_hold.json()["status"] == "on_hold"
    r_ver = c_acc.post(f"/api/v1/psm/invoices/{inv_id}/verify", {}, format="json")
    assert r_ver.status_code == 200
    assert r_ver.json()["status"] == "verified"
    r_pay = c_acc.post(
        f"/api/v1/psm/invoices/{inv_id}/pay",
        {"amount": "10000.00", "payment_reference": "UTR-HTTP-1"},
        format="json",
    )
    assert r_pay.status_code == 201

    # Report schedules list + create + patch via HTTP (AFR-PSM-065..078, AFR-PSM-081)
    c_ps = _client(stub_iam, uid=9104, role="ps_admin")
    r_sched = c_ps.post(
        "/api/v1/psm/reports/schedules",
        {
            "name": "Weekly Ops",
            "report_type": "operational",
            "cadence": "weekly",
            "filters": {"department": "CSE"},
        },
        format="json",
    )
    assert r_sched.status_code == 201
    sched_id = r_sched.json()["id"]
    assert c_ps.get("/api/v1/psm/reports/schedules").status_code == 200
    r_patch = c_ps.patch(
        f"/api/v1/psm/reports/schedules/{sched_id}",
        {"is_active": False, "cadence": "monthly"},
        format="json",
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["is_active"] is False

    # Audit log filter + notifications + dashboard (CFR-PSM-018, CFR-PSM-020, AFR-PSM-091, AFR-PSM-092)
    c_aud = _client(stub_iam, uid=9107, role="Auditor")
    assert c_aud.get("/api/v1/psm/audit?target_type=invoice").status_code == 200
    c_emp = _client(stub_iam, uid=9101, role="faculty")
    assert c_emp.get("/api/v1/psm/notifications").status_code == 200
    assert c_emp.get("/api/v1/psm/indents?status=fulfilled").status_code == 200

    # List endpoints for stock, transfers, vendors, tenders, POs, GRNs, discrepancies
    c_ps = _client(stub_iam, uid=9104, role="ps_admin")
    assert c_ps.get("/api/v1/psm/dashboard").status_code == 200
    assert c_ps.get("/api/v1/psm/stock/items").status_code == 200
    assert c_ps.get("/api/v1/psm/stock/locations").status_code == 200
    assert c_ps.get("/api/v1/psm/transfers").status_code == 200
    assert c_ps.get("/api/v1/psm/vendors").status_code == 200
    assert c_ps.get("/api/v1/psm/tenders").status_code == 200
    assert c_ps.get("/api/v1/psm/purchase-orders").status_code == 200
    assert c_ps.get("/api/v1/psm/grns").status_code == 200
    assert c_ps.get("/api/v1/psm/discrepancies").status_code == 200


def test_discrepancy_resolution_return_replacement_and_communication():
    # AFR-PSM-046, AFR-PSM-049, AFR-PSM-050, AFR-PSM-051, AFR-PSM-052, AFR-PSM-053
    # AFR-PSM-054, AFR-PSM-055, BR-PSM-025, BW-PSM-06, BW-PSM-10
    p_emp, p_dept, p_hod, p_ps, _p_dir, _p_acc, _p_aud = _setup_actors()
    policy.seed_default_policy()
    v = vendors.onboard_vendor(
        actor=p_ps,
        name="Disc Vendor",
        gstin="23DISCA1234F1Z5",
        bank_account_number="223344556677",
        bank_ifsc="SBIN0001234",
        bank_name="SBI",
        compliance_documents=["gst.pdf"],
        contact_email="disc@v.test",
    )
    vendors.verify_vendor(actor=p_ps, vendor_id=v.pk)
    ind = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="Router",
        quantity=3,
        estimated_cost=Decimal("15000.00"),
        justification="Switch rack",
        submit=True,
    )
    stock.check_and_reserve(actor=p_dept, indent_id=ind.pk)
    approvals.dept_admin_review(
        actor=p_dept, indent_id=ind.pk, decision="approve", priority="normal"
    )
    approvals.hod_recommend(actor=p_hod, indent_id=ind.pk, decision="recommend")
    procurement.review_and_select_method(actor=p_ps, indent_id=ind.pk)
    po = procurement.create_and_issue_po(
        actor=p_ps,
        indent_id=ind.pk,
        vendor_id=v.pk,
        ordered_quantity=3,
        unit_price=Decimal("5000.00"),
        planned_delivery_date=date.today() + timedelta(days=5),
    )
    grn = receipts.record_grn(
        actor=p_emp,
        purchase_order_id=po.pk,
        received_quantity=3,
        accepted_quantity=2,
        rejected_quantity=1,
        inspection_notes="1 damaged unit",
    )

    # Validation: invalid evidence URL refused (AFR-PSM-049)
    with pytest.raises(DomainError):
        discrepancies.report_discrepancy(
            actor=p_emp,
            grn_id=grn.pk,
            discrepancy_type="damaged",
            affected_quantity=1,
            description="Cracked chassis",
            requested_resolution="replacement",
            evidence_url="http://evil.example.com/bad.exe",
        )

    case = discrepancies.report_discrepancy(
        actor=p_emp,
        grn_id=grn.pk,
        discrepancy_type="damaged",
        affected_quantity=1,
        description="Cracked chassis",
        requested_resolution="replacement",
        evidence_url="https://drive.google.com/file/d/1234567890abcdef/view",
        evidence_filename="damage photo.jpg",
    )
    assert case.status == "open"

    # Discrepancy communication thread (AFR-PSM-051, AFR-PSM-052)
    comm = discrepancies.add_communication(
        actor=p_ps, case_id=case.pk, sender_label="PS Admin", message="Vendor contacted"
    )
    assert comm.case_id == case.pk

    # Resolve with replacement delivery (BR-PSM-025: allowed once), then resolve and close
    waiting = discrepancies.resolve_case(
        actor=p_ps,
        case_id=case.pk,
        resolution_action="await_replacement",
        resolution_notes="Vendor sending replacement",
    )
    assert waiting.status == "replacement_awaited"
    assert waiting.replacement_count == 1

    # Second replacement cycle refused (BR-PSM-025)
    with pytest.raises(ConflictError):
        discrepancies.resolve_case(
            actor=p_ps,
            case_id=case.pk,
            resolution_action="await_replacement",
            resolution_notes="Second attempt",
        )

    resolved = discrepancies.resolve_case(
        actor=p_ps,
        case_id=case.pk,
        resolution_action="resolve",
        resolution_notes="Replacement accepted",
        inventory_adjusted=True,
    )
    assert resolved.status == "resolved"
    closed = discrepancies.resolve_case(
        actor=p_ps,
        case_id=case.pk,
        resolution_action="close",
        resolution_notes="Case closed",
    )
    assert closed.status == "closed"

    # Missing case raises NotFoundError
    with pytest.raises(NotFoundError):
        discrepancies.resolve_case(
            actor=p_ps,
            case_id=999999,
            resolution_action="resolve",
            resolution_notes="None",
        )


def test_transfers_cancel_stock_adjustments_vendor_updates_and_approvals():
    # AFR-PSM-005, AFR-PSM-006, AFR-PSM-007, AFR-PSM-010, AFR-PSM-011, AFR-PSM-014
    # AFR-PSM-017, AFR-PSM-018, AFR-PSM-019, AFR-PSM-023, AFR-PSM-024, AFR-PSM-025, AFR-PSM-026
    # AFR-PSM-029, AFR-PSM-030, AFR-PSM-031, AFR-PSM-033, AFR-PSM-034, AFR-PSM-035, AFR-PSM-036
    # AFR-PSM-038, AFR-PSM-039, AFR-PSM-041, AFR-PSM-042, AFR-PSM-043, AFR-PSM-044
    # BR-PSM-021, BR-PSM-027, PSM-UC-020, PSM-UC-026, PSM-UC-027, PSM-UC-032, PSM-UC-033, PSM-UC-034
    p_emp, p_dept, p_hod, p_ps, _p_dir, _p_acc, _p_aud = _setup_actors()
    policy.seed_default_policy()

    # Stock locations, item, adjustment, selectors (PSM-UC-026, PSM-UC-027)
    loc_cse = stock.create_stock_location(
        actor=p_ps, code="LOC-CSE-COV", name="CSE Store", department="CSE", is_central=False
    )
    loc_ece = stock.create_stock_location(
        actor=p_ps, code="LOC-ECE-COV", name="ECE Store", department="ECE", is_central=False
    )
    item = stock.create_stock_item(
        actor=p_ps, sku="SKU-COV-01", name="Lab Cable", category="Electrical", unit="pcs"
    )
    stock.record_adjustment(
        actor=p_ps,
        item_id=item.pk,
        location_id=loc_cse.pk,
        quantity_delta=15,
        reason="Initial stock",
    )
    stock.record_adjustment(
        actor=p_ps,
        item_id=item.pk,
        location_id=loc_cse.pk,
        quantity_delta=-5,
        reason="Damaged coil write-off",
    )
    assert StockLedgerEntry.objects.filter(item=item, entry_type="adjustment").count() == 2
    rows = stock_sel.availability_rows(p_ps, item_id=item.pk, location_id=loc_cse.pk)
    assert rows and rows[0]["allocable"] == 10

    # Transfer request + cancel (PSM-UC-032)
    p_dept_ece = _make_p(9112, "deptadmin_ece")
    tr1 = transfers.request_transfer(
        actor=p_dept_ece,
        item_id=item.pk,
        source_location_id=loc_cse.pk,
        destination_location_id=loc_ece.pk,
        quantity=2,
        notes="ECE lab setup",
    )
    cancelled = transfers.cancel_transfer(actor=p_dept_ece, transfer_id=tr1.pk)
    assert cancelled.status == "cancelled"
    with pytest.raises(NotFoundError):
        transfers.cancel_transfer(actor=p_dept_ece, transfer_id=999999)

    # Transfer request + dispatch authorization + confirm (PSM-UC-032, 033, 034, BR-PSM-027)
    tr2 = transfers.request_transfer(
        actor=p_dept_ece,
        item_id=item.pk,
        source_location_id=loc_cse.pk,
        destination_location_id=loc_ece.pk,
        quantity=3,
        notes="ECE bench",
    )
    # R1-03: destination-dept admin and ps_admin on non-central source are refused
    with pytest.raises(PermissionDeniedError):
        transfers.dispatch_transfer(actor=p_dept_ece, transfer_id=tr2.pk)
    with pytest.raises(PermissionDeniedError):
        transfers.dispatch_transfer(actor=p_ps, transfer_id=tr2.pk)
    dispatched = transfers.dispatch_transfer(actor=p_dept, transfer_id=tr2.pk)
    assert dispatched.status == "dispatched"
    confirmed = transfers.confirm_transfer(actor=p_dept_ece, transfer_id=tr2.pk)
    assert confirmed.status == "completed"
    # Verify dual ledger posting (BR-PSM-027, AFR-PSM-068..070)
    assert StockLedgerEntry.objects.filter(
        source_ref_type="stock_transfer", source_ref_id=tr2.pk, entry_type="transfer_out"
    ).exists()
    assert StockLedgerEntry.objects.filter(
        source_ref_type="stock_transfer", source_ref_id=tr2.pk, entry_type="transfer_in"
    ).exists()
    # R1-03: ps_admin is permitted when source_location.is_central=True
    loc_central = stock.create_stock_location(
        actor=p_ps, code="LOC-CEN-COV", name="Central Store", department="Stores", is_central=True
    )
    stock.record_adjustment(
        actor=p_ps, item_id=item.pk, location_id=loc_central.pk, quantity_delta=10, reason="Init"
    )
    tr_cen = transfers.request_transfer(
        actor=p_dept_ece,
        item_id=item.pk,
        source_location_id=loc_central.pk,
        destination_location_id=loc_ece.pk,
        quantity=2,
        notes="From central",
    )
    assert transfers.dispatch_transfer(actor=p_ps, transfer_id=tr_cen.pk).status == "dispatched"

    # Vendor update + change history (PSM-UC-020, BR-PSM-021)
    v = vendors.onboard_vendor(
        actor=p_ps,
        name="Perf Vendor",
        gstin="23PERFA1234F1Z5",
        bank_account_number="334455667788",
        bank_ifsc="SBIN0001234",
        bank_name="SBI",
        compliance_documents=["gst.pdf"],
        contact_email="perf@v.test",
    )
    vendors.verify_vendor(actor=p_ps, vendor_id=v.pk)
    v_upd = vendors.update_vendor(
        actor=p_ps,
        vendor_id=v.pk,
        change_reason="Email update",
        contact_email="perf2@v.test",
    )
    assert v_upd.contact_email == "perf2@v.test"

    # Approval changes_requested -> modify -> resubmit -> hod reject (AFR-PSM-017..026)
    ind = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="DSO 100MHz",
        quantity=1,
        estimated_cost=Decimal("22000.00"),
        justification="Lab upgrade",
        submit=True,
    )
    stock.check_and_reserve(actor=p_dept, indent_id=ind.pk)
    approvals.dept_admin_review(
        actor=p_dept, indent_id=ind.pk, decision="approve", priority="normal"
    )
    ind_chg = approvals.hod_recommend(
        actor=p_hod,
        indent_id=ind.pk,
        decision="request_changes",
        reason="Specify probe rating",
    )
    assert ind_chg.status == "changes_requested"
    ind_mod = indents.modify_indent(
        actor=p_emp, indent_id=ind.pk, justification="Lab upgrade with 10x probes"
    )
    assert ind_mod.status == "submitted"
    stock.check_and_reserve(actor=p_dept, indent_id=ind.pk)
    approvals.dept_admin_review(
        actor=p_dept, indent_id=ind.pk, decision="approve", priority="normal"
    )
    ind_rej = approvals.hod_recommend(
        actor=p_hod, indent_id=ind.pk, decision="reject", reason="Deferred to Q2"
    )
    assert ind_rej.status == "rejected"

    # Contracts plural getters coverage
    summaries = contracts.get_indent_summaries([p_emp.user_id])
    assert summaries[p_emp.user_id].rejected_count >= 1
    assert contracts.get_indent_summaries([]) == {}
    obligations = contracts.get_pending_receipt_obligations([p_emp.user_id])
    assert obligations[p_emp.user_id].unconfirmed_grn_count == 0
    assert contracts.get_pending_receipt_obligations([]) == {}


def test_reports_all_types_filters_scoping_and_throttle_429(stub_iam, monkeypatch):
    # AFR-PSM-070..078, CFR-PSM-016
    from core.api.throttling import PrincipalScopedThrottle

    p_emp, _p_dept, _p_hod, p_ps, _p_dir, p_acc, _p_aud = _setup_actors()
    policy.seed_default_policy()
    for rtype in ("operational", "procurement", "stock", "financial"):
        actor = p_acc if rtype == "financial" else p_ps
        res = reports.generate_report(
            actor=actor,
            report_type=rtype,
            filters={
                "department": "CSE",
                "date_from": str(date.today() - timedelta(days=30)),
                "date_to": str(date.today()),
            },
        )
        assert "rows" in res
    cols, _rows = report_sel.build_report_rows(
        p_ps, report_type="stock", filters={"department": "CSE"}
    )
    assert cols
    with pytest.raises(PermissionDeniedError):
        reports.generate_report(actor=p_emp, report_type="financial", filters={})

    # Scoping fallbacks for generic dept_admin
    p_generic_dept = _make_p(9199, "dept_admin")
    assert scoping.indents_for(p_generic_dept).count() == 0
    assert scoping.purchase_orders_for(p_generic_dept).count() == 0
    assert scoping.tenders_for(p_generic_dept).count() == 0
    assert scoping.grns_for(p_generic_dept).count() == 0
    assert scoping.invoices_for(p_generic_dept).count() == 0

    with pytest.raises(NotFoundError):
        reports.update_schedule(actor=p_ps, schedule_id=999999, is_active=False)

    # Throttle enforcement on psm_export (429)
    cache.clear()
    monkeypatch.setitem(PrincipalScopedThrottle.THROTTLE_RATES, "psm_export", "1/min")
    c_ps = _client(stub_iam, uid=9104, role="ps_admin")
    r1 = c_ps.post(
        "/api/v1/psm/reports/export",
        {"report_type": "operational", "filters": {}},
        format="json",
    )
    r2 = c_ps.post(
        "/api/v1/psm/reports/export",
        {"report_type": "operational", "filters": {}},
        format="json",
    )
    assert r1.status_code == 200
    assert r2.status_code == 429
    cache.clear()


def test_r1_04_discrepancy_resolve_atomic_inventory_and_accounting_adjustments():
    # R1-04: AFR-PSM-054, AFR-PSM-055, BR-PSM-019 atomic stock ledger + invoice adjustment
    from modules.psm.models import Invoice, PsmAuditLog
    from modules.psm.services import finance

    p_emp, p_dept, p_hod, p_ps, _p_dir, p_acc, _p_aud = _setup_actors()
    policy.seed_default_policy()
    loc = stock.create_stock_location(
        actor=p_ps, code="LOC-R104", name="CSE Lab", department="CSE", is_central=False
    )
    item = stock.create_stock_item(
        actor=p_ps, sku="SKU-R104", name="Oscilloscope", category="Lab", unit="pcs"
    )
    v = vendors.onboard_vendor(
        actor=p_ps,
        name="R104 Vendor",
        gstin="23ABCDE5678F1Z5",
        bank_account_number="998877665544",
        bank_ifsc="SBIN0001234",
        bank_name="SBI",
        compliance_documents=["gst.pdf"],
        contact_email="r104@v.test",
    )
    vendors.verify_vendor(actor=p_ps, vendor_id=v.pk)
    ind = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_id=item.pk,
        item_description="Oscilloscope",
        quantity=3,
        estimated_cost=Decimal("15000.00"),
        justification="Lab equip",
        submit=True,
    )
    stock.check_and_reserve(actor=p_dept, indent_id=ind.pk)
    approvals.dept_admin_review(
        actor=p_dept, indent_id=ind.pk, decision="approve", priority="normal"
    )
    approvals.hod_recommend(actor=p_hod, indent_id=ind.pk, decision="recommend")
    procurement.review_and_select_method(actor=p_ps, indent_id=ind.pk)
    po = procurement.create_and_issue_po(
        actor=p_ps,
        indent_id=ind.pk,
        vendor_id=v.pk,
        ordered_quantity=3,
        unit_price=Decimal("5000.00"),
        planned_delivery_date=date.today() + timedelta(days=5),
    )
    grn = receipts.record_grn(
        actor=p_emp,
        purchase_order_id=po.pk,
        received_quantity=3,
        accepted_quantity=2,
        rejected_quantity=1,
        inspection_notes="1 cracked unit",
    )
    inv = finance.submit_invoice(
        actor=p_acc,
        purchase_order_id=po.pk,
        invoice_number="INV-R104-1",
        billed_quantity=3,
        billed_amount=Decimal("15000.00"),
    )
    # R2-01: unconfirmed GRN must NOT allow discrepancy resolution to verify/pay the invoice
    case_unconf = discrepancies.report_discrepancy(
        actor=p_emp,
        grn_id=grn.pk,
        discrepancy_type="damaged",
        affected_quantity=1,
        description="Cracked display before confirmation",
        requested_resolution="return_and_adjust",
    )
    inv.refresh_from_db()
    assert inv.status == "on_hold"
    discrepancies.resolve_case(
        actor=p_ps,
        case_id=case_unconf.pk,
        resolution_action="resolve",
        resolution_notes="Resolved before GRN confirmation",
        inventory_adjusted=False,
        accounting_adjusted=True,
    )
    inv.refresh_from_db()
    assert inv.status == "on_hold"
    assert inv.eligible_amount == Decimal("0.00")

    # Confirm the GRN first (BR-PSM-009), then open & resolve discrepancy with atomic adjustments
    receipts.confirm_receipt(actor=p_emp, grn_id=grn.pk)
    case = discrepancies.report_discrepancy(
        actor=p_emp,
        grn_id=grn.pk,
        discrepancy_type="damaged",
        affected_quantity=1,
        description="Cracked display",
        requested_resolution="return_and_adjust",
    )
    resolved = discrepancies.resolve_case(
        actor=p_ps,
        case_id=case.pk,
        resolution_action="resolve",
        resolution_notes="Vendor issued credit note for 1 unit",
        inventory_adjusted=True,
        accounting_adjusted=True,
    )
    assert resolved.status == "resolved"
    adj_entry = StockLedgerEntry.objects.filter(
        source_ref_type="discrepancy", source_ref_id=case.pk, location=loc, item=item
    ).first()
    assert adj_entry is not None
    assert adj_entry.quantity_delta == -1
    inv = Invoice.objects.get(pk=inv.pk)
    assert inv.eligible_amount == Decimal("10000.00")
    assert inv.status == "verified"
    assert inv.hold_reason == ""
    assert PsmAuditLog.objects.filter(
        action="stock.discrepancy_adjusted", target_id=adj_entry.pk
    ).exists()
    assert PsmAuditLog.objects.filter(
        action="invoice.discrepancy_adjusted", target_id=inv.pk
    ).exists()


def test_r1_07_r1_09_po_state_machine_and_direct_spec_assertions():
    # R1-07, R1-09: CFR-PSM-009, AFR-PSM-042, AFR-PSM-068..073, PSM-UC-031 direct assertions
    from modules.psm.models import PsmNotification, ReportGenerationLog

    p_emp, p_dept, p_hod, p_ps, _p_dir, _p_acc, _p_aud = _setup_actors()
    policy.seed_default_policy()
    v = vendors.onboard_vendor(
        actor=p_ps,
        name="PO SM Vendor",
        gstin="23ABCDE9999F1Z5",
        bank_account_number="554433221100",
        bank_ifsc="SBIN0001234",
        bank_name="SBI",
        compliance_documents=["gst.pdf"],
        contact_email="posm@v.test",
    )
    vendors.verify_vendor(actor=p_ps, vendor_id=v.pk)
    ind = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="Network Switch",
        quantity=2,
        estimated_cost=Decimal("18000.00"),
        justification="Lab rack",
        submit=True,
    )
    stock.check_and_reserve(actor=p_dept, indent_id=ind.pk)
    approvals.dept_admin_review(
        actor=p_dept, indent_id=ind.pk, decision="approve", priority="normal"
    )
    approvals.hod_recommend(actor=p_hod, indent_id=ind.pk, decision="recommend")
    procurement.review_and_select_method(actor=p_ps, indent_id=ind.pk)
    po = procurement.create_and_issue_po(
        actor=p_ps,
        indent_id=ind.pk,
        vendor_id=v.pk,
        ordered_quantity=2,
        unit_price=Decimal("9000.00"),
        planned_delivery_date=date.today() + timedelta(days=7),
    )
    # Illegal PO jump issued -> closed refused by declarative state machine (R1-07)
    with pytest.raises(ConflictError):
        procurement.update_po_schedule(actor=p_ps, po_id=po.pk, status="closed")
    # Legal PO progression issued -> in_transit -> delivered -> closed (CFR-PSM-009, AFR-PSM-042)
    po = procurement.update_po_schedule(
        actor=p_ps, po_id=po.pk, status="in_transit", delivery_notes="Dispatched by courier"
    )
    assert po.status == "in_transit"
    assert PsmNotification.objects.filter(topic="po.status_changed").exists()
    po = procurement.update_po_schedule(actor=p_ps, po_id=po.pk, status="delivered")
    po = procurement.update_po_schedule(actor=p_ps, po_id=po.pk, status="closed")
    assert po.status == "closed"
    with pytest.raises(ConflictError):
        procurement.update_po_schedule(actor=p_ps, po_id=po.pk, delivery_notes="Late note")
    # Scheduled report creation, update, and execution log (PSM-UC-031, AFR-PSM-071..073)
    sched = reports.create_schedule(
        actor=p_ps, name="Daily Ops", report_type="operational", cadence="daily", filters={}
    )
    sched = reports.update_schedule(actor=p_ps, schedule_id=sched.pk, cadence="weekly")
    assert sched.cadence == "weekly"
    sched.next_run_at = timezone.now() - timedelta(minutes=1)
    sched.save(update_fields=["next_run_at"])
    assert reports.run_due_schedules() == 1
    assert ReportGenerationLog.objects.filter(schedule=sched, status="succeeded").exists()


def test_r2_02_03_04_07_queue_ordering_replacement_mismatch_overflow_and_bounds(stub_iam):
    # R2-02 (AFR-PSM-025), R2-03, R2-04, R2-07 (AFR-PSM-014, AFR-PSM-023, discrepancy qty bounds)
    from modules.psm.models import PsmNotification

    p_emp, p_dept, _p_hod, p_ps, _p_dir, _p_acc, _p_aud = _setup_actors()
    policy.seed_default_policy()

    # AFR-PSM-014: stock_available notification on check_and_reserve
    loc = stock.create_stock_location(
        actor=p_ps, code="LOC-R2", name="CSE R2", department="CSE", is_central=False
    )
    item = stock.create_stock_item(actor=p_ps, sku="SKU-R2", name="Meter")
    stock.record_adjustment(
        actor=p_ps, item_id=item.pk, location_id=loc.pk, quantity_delta=10, reason="Init"
    )
    ind_stk = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_id=item.pk,
        item_description="Meter",
        quantity=2,
        estimated_cost=Decimal("1000.00"),
        justification="Stock test",
        submit=True,
    )
    stock.check_and_reserve(actor=p_dept, indent_id=ind_stk.pk)
    assert PsmNotification.objects.filter(
        topic="indent.stock_available", recipient_user_id=p_emp.user_id
    ).exists()

    # AFR-PSM-025 (R2-02): ?queue=1 orders critical/urgent -> high -> normal
    ind_norm = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="Normal Item",
        quantity=1,
        estimated_cost=Decimal("5000.00"),
        justification="Normal",
        submit=True,
    )
    stock.check_and_reserve(actor=p_dept, indent_id=ind_norm.pk)
    approvals.dept_admin_review(
        actor=p_dept, indent_id=ind_norm.pk, decision="approve", priority="normal"
    )
    ind_high = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="High Item",
        quantity=1,
        estimated_cost=Decimal("6000.00"),
        justification="High",
        submit=True,
    )
    stock.check_and_reserve(actor=p_dept, indent_id=ind_high.pk)
    approvals.dept_admin_review(
        actor=p_dept, indent_id=ind_high.pk, decision="approve", priority="high"
    )
    ind_crit = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="Critical Item",
        quantity=1,
        estimated_cost=Decimal("7000.00"),
        justification="Critical",
        submit=True,
    )
    stock.check_and_reserve(actor=p_dept, indent_id=ind_crit.pk)
    approvals.dept_admin_review(
        actor=p_dept, indent_id=ind_crit.pk, decision="approve", priority="critical"
    )
    c_ps = _client(stub_iam, uid=9104, role="ps_admin")
    r_q = c_ps.get("/api/v1/psm/indents?queue=1&status=department_reviewed")
    assert r_q.status_code == 200
    returned_ids = [row["id"] for row in r_q.json()["results"]]
    assert returned_ids == [ind_crit.pk, ind_high.pk, ind_norm.pk]

    # AFR-PSM-023: high-priority direct approval bypasses HOD into procurement_authorized
    direct_ind = procurement.review_and_select_method(actor=p_ps, indent_id=ind_high.pk)
    assert direct_ind.status == "procurement_authorized"

    # R2-03 & R2-07: replacement GRN cross-PO mismatch refused + discrepancy qty bounds enforced
    v = vendors.onboard_vendor(
        actor=p_ps,
        name="R2 Vendor",
        gstin="23ABCDE7777F1Z5",
        bank_account_number="776655443322",
        bank_ifsc="SBIN0001234",
        bank_name="SBI",
        compliance_documents=["gst.pdf"],
        contact_email="r2@v.test",
    )
    vendors.verify_vendor(actor=p_ps, vendor_id=v.pk)
    po1 = procurement.create_and_issue_po(
        actor=p_ps,
        indent_id=ind_high.pk,
        vendor_id=v.pk,
        ordered_quantity=1,
        unit_price=Decimal("6000.00"),
        planned_delivery_date=date.today() + timedelta(days=5),
    )
    procurement.review_and_select_method(actor=p_ps, indent_id=ind_crit.pk)
    po2 = procurement.create_and_issue_po(
        actor=p_ps,
        indent_id=ind_crit.pk,
        vendor_id=v.pk,
        ordered_quantity=1,
        unit_price=Decimal("7000.00"),
        planned_delivery_date=date.today() + timedelta(days=5),
    )
    grn1 = receipts.record_grn(
        actor=p_emp,
        purchase_order_id=po1.pk,
        received_quantity=1,
        accepted_quantity=0,
        rejected_quantity=1,
    )
    # R2-07: affected_quantity <= 0 and > received_quantity must fail
    with pytest.raises(DomainError) as exc_zero:
        discrepancies.report_discrepancy(
            actor=p_emp,
            grn_id=grn1.pk,
            discrepancy_type="damage",
            affected_quantity=0,
            description="Zero qty",
            requested_resolution="replacement",
        )
    assert exc_zero.value.code == "invalid_affected_quantity"
    with pytest.raises(DomainError) as exc_over:
        discrepancies.report_discrepancy(
            actor=p_emp,
            grn_id=grn1.pk,
            discrepancy_type="damage",
            affected_quantity=2,
            description="Over qty",
            requested_resolution="replacement",
        )
    assert exc_over.value.code == "invalid_affected_quantity"
    case1 = discrepancies.report_discrepancy(
        actor=p_emp,
        grn_id=grn1.pk,
        discrepancy_type="damage",
        affected_quantity=1,
        description="Broken",
        requested_resolution="replacement",
    )
    discrepancies.resolve_case(
        actor=p_ps,
        case_id=case1.pk,
        resolution_action="await_replacement",
        resolution_notes="Vendor replacing",
    )
    # R2-03: using case1 (from po1) on po2 must be refused with ConflictError
    with pytest.raises(ConflictError) as exc_mis:
        receipts.record_grn(
            actor=p_emp,
            purchase_order_id=po2.pk,
            replacement_for_case_id=case1.pk,
            received_quantity=1,
            accepted_quantity=1,
        )
    assert exc_mis.value.code == "replacement_source_mismatch"

    # R2-04: 32-bit integer overflow returns clean 400 validation_error JSON (never 500)
    c_emp = _client(stub_iam, uid=9101, role="faculty")
    r_ov1 = c_emp.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_description": "Overflow",
            "quantity": 9_999_999_999,
            "estimated_cost": "100.00",
            "justification": "Test",
        },
        format="json",
    )
    assert r_ov1.status_code == 400
    assert r_ov1.json()["error"]["code"] == "validation_error"
    c_ps = _client(stub_iam, uid=9104, role="ps_admin")
    r_ov2 = c_ps.post(
        "/api/v1/psm/stock/adjustments",
        {
            "item_id": item.pk,
            "location_id": loc.pk,
            "quantity_delta": 9_999_999_999,
            "reason": "Overflow",
        },
        format="json",
    )
    assert r_ov2.status_code == 400
    assert r_ov2.json()["error"]["code"] == "validation_error"
    c_acc = _client(stub_iam, uid=9106, role="Accounts Admin")
    r_ov3 = c_acc.post(
        "/api/v1/psm/invoices",
        {
            "purchase_order_id": po1.pk,
            "invoice_number": "INV-OV-1",
            "billed_quantity": 9_999_999_999,
            "billed_amount": "100.00",
        },
        format="json",
    )
    assert r_ov3.status_code == 400
    assert r_ov3.json()["error"]["code"] == "validation_error"
