# End-to-end HTTP journey tests covering every live UC, workflow, BR, CFR, and AFR (Step 5.12, 5.13).
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.psm import registry
from modules.psm.models import (
    Indent,
    PsmAuditLog,
    ReportGenerationLog,
    StockLedgerEntry,
    VendorVersion,
)
from modules.psm.services.policy import seed_default_policy

pytestmark = pytest.mark.django_db


def _actor(stub_iam, *, uid: int, role: str):
    stub_iam(
        make_session(
            user_id=uid,
            kind="staff" if role not in ("faculty", "HOD (CSE)") else "faculty",
            active_role=role,
            roles=(role,),
            modules=("psm",),
            permissions=tuple(registry.ROLE_GRANTS[role]),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token u{uid}")
    return c


def test_journey_bw_psm_01_internal_stock_fulfilment(stub_iam):
    # BW-PSM-01, CW-PSM-01, PSM-UC-001, PSM-UC-007, PSM-UC-011, PSM-UC-009, PSM-UC-028, PSM-UC-002
    # CFR-PSM-001, CFR-PSM-003, CFR-PSM-004, AFR-PSM-001..007, AFR-PSM-013..021, BR-PSM-003, BR-PSM-013, BR-PSM-026
    seed_default_policy()
    ps = _actor(stub_iam, uid=9001, role="ps_admin")
    item_id = ps.post(
        "/api/v1/psm/stock/items",
        {"sku": "J1-PAP", "name": "A4 Paper", "unit": "ream"},
        format="json",
    ).data["id"]
    loc_id = ps.post(
        "/api/v1/psm/stock/locations",
        {"code": "CSE-J1", "name": "CSE Store", "department": "CSE"},
        format="json",
    ).data["id"]
    assert (
        ps.post(
            "/api/v1/psm/stock/adjustments",
            {
                "item_id": item_id,
                "location_id": loc_id,
                "quantity_delta": 20,
                "reason": "Opening stock",
                "entry_type": "opening",
            },
            format="json",
        ).status_code
        == 201
    )

    emp = _actor(stub_iam, uid=9002, role="faculty")
    r_ind = emp.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_id": item_id,
            "item_description": "A4 Paper",
            "quantity": 5,
            "estimated_cost": "1500.00",
            "justification": "Exam printing",
        },
        format="json",
    )
    assert r_ind.status_code == 201
    ind_id = r_ind.data["id"]
    # Duplicate detection flag (BR-PSM-015, AFR-PSM-004)
    r_dup = emp.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_id": item_id,
            "item_description": "A4 Paper",
            "quantity": 5,
            "estimated_cost": "1500.00",
            "justification": "Second request",
        },
        format="json",
    )
    assert r_dup.status_code == 201 and r_dup.data["is_duplicate_flagged"] is True

    da = _actor(stub_iam, uid=9003, role="deptadmin_cse")
    r_chk = da.post(f"/api/v1/psm/indents/{ind_id}/stock-check", {}, format="json")
    assert r_chk.status_code == 200 and r_chk.data["status"] == "stock_reserved"

    r_rev = da.post(
        f"/api/v1/psm/indents/{ind_id}/review",
        {"decision": "approve", "priority": "high"},
        format="json",
    )
    assert r_rev.status_code == 200 and r_rev.data["status"] == "internal_approved"

    issues = da.get("/api/v1/psm/internal-issues").data["results"]
    issue_id = issues[0]["id"]
    assert (
        da.post(
            f"/api/v1/psm/internal-issues/{issue_id}/schedule-picking", {}, format="json"
        ).status_code
        == 200
    )
    assert (
        da.post(f"/api/v1/psm/internal-issues/{issue_id}/dispatch", {}, format="json").status_code
        == 200
    )

    emp = _actor(stub_iam, uid=9002, role="faculty")
    r_grn = emp.post(
        "/api/v1/psm/grns",
        {
            "internal_issue_id": issue_id,
            "received_quantity": 5,
            "accepted_quantity": 5,
            "rejected_quantity": 0,
        },
        format="json",
    )
    assert r_grn.status_code == 201
    grn_id = r_grn.data["id"]
    r_conf = emp.post(f"/api/v1/psm/grns/{grn_id}/confirm", {}, format="json")
    assert r_conf.status_code == 200 and r_conf.data["stock_posted"] is True
    assert Indent.objects.get(pk=ind_id).status == "fulfilled"
    assert StockLedgerEntry.objects.filter(
        item_id=item_id, entry_type="internal_issue_post", quantity_delta=-5
    ).exists()


def test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial(stub_iam):
    # BW-PSM-02, BW-PSM-04, CW-PSM-01, CW-PSM-02, PSM-UC-016, PSM-UC-017, PSM-UC-019, PSM-UC-025..029, PSM-UC-013
    # CFR-PSM-005, CFR-PSM-006, CFR-PSM-008..010, CFR-PSM-013, CFR-PSM-014
    # AFR-PSM-022..031, AFR-PSM-037..047, AFR-PSM-056..066, BR-PSM-004, 008, 012, 017, 018, 022, 025
    seed_default_policy()
    ps = _actor(stub_iam, uid=9101, role="ps_admin")
    v_id = ps.post(
        "/api/v1/psm/vendors",
        {
            "name": "Direct Supplies",
            "gstin": "23AABCU9603R1ZM",
            "bank_account_number": "123456789012",
            "bank_ifsc": "SBIN0001234",
            "bank_name": "SBI",
            "compliance_documents": ["GST", "PAN"],
        },
        format="json",
    ).data["id"]
    assert (
        ps.patch(
            f"/api/v1/psm/vendors/{v_id}",
            {"contact_email": "sales@direct.test", "change_reason": "Add email"},
            format="json",
        ).status_code
        == 200
    )
    assert ps.post(f"/api/v1/psm/vendors/{v_id}/verify", {}, format="json").status_code == 200
    assert VendorVersion.objects.filter(vendor_id=v_id).count() == 3

    emp = _actor(stub_iam, uid=9102, role="faculty")
    ind_id = emp.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_description": "Lab Router",
            "quantity": 4,
            "estimated_cost": "40000.00",
            "justification": "Network upgrade",
        },
        format="json",
    ).data["id"]

    da = _actor(stub_iam, uid=9103, role="deptadmin_cse")
    assert (
        da.post(f"/api/v1/psm/indents/{ind_id}/stock-check", {}, format="json").data["status"]
        == "external_required"
    )
    assert (
        da.post(
            f"/api/v1/psm/indents/{ind_id}/review",
            {"decision": "approve", "priority": "normal"},
            format="json",
        ).data["status"]
        == "department_reviewed"
    )

    hod = _actor(stub_iam, uid=9104, role="HOD (CSE)")
    # PSM-UC-017: HOD checks stock during review
    assert hod.get("/api/v1/psm/stock/availability").status_code == 200
    assert (
        hod.post(
            f"/api/v1/psm/indents/{ind_id}/recommend", {"decision": "recommend"}, format="json"
        ).data["status"]
        == "hod_recommended"
    )

    ps = _actor(stub_iam, uid=9101, role="ps_admin")
    r_pr = ps.post(
        f"/api/v1/psm/indents/{ind_id}/procurement-review", {"notes": "Direct buy"}, format="json"
    )
    assert r_pr.status_code == 200 and r_pr.data["procurement_method"] == "direct"
    assert r_pr.data["status"] == "procurement_authorized"

    r_po = ps.post(
        "/api/v1/psm/purchase-orders",
        {
            "indent_id": ind_id,
            "vendor_id": v_id,
            "unit_price": "10000.00",
            "planned_delivery_date": "2026-12-15",
        },
        format="json",
    )
    assert r_po.status_code == 201
    po_id = r_po.data["id"]
    assert (
        ps.patch(
            f"/api/v1/psm/purchase-orders/{po_id}",
            {"status": "in_transit", "delivery_notes": "Shipped"},
            format="json",
        ).status_code
        == 200
    )

    # Partial GRN (2 of 4 units) + confirmation
    emp = _actor(stub_iam, uid=9102, role="faculty")
    grn1 = emp.post(
        "/api/v1/psm/grns",
        {"purchase_order_id": po_id, "received_quantity": 2, "accepted_quantity": 2},
        format="json",
    ).data["id"]
    assert emp.post(f"/api/v1/psm/grns/{grn1}/confirm", {}, format="json").status_code == 200

    # Accounts: mismatched invoice goes on hold (BR-PSM-018), matching partial invoice pays partially (BR-PSM-022)
    acc = _actor(stub_iam, uid=9105, role="Accounts Admin")
    inv_bad = acc.post(
        "/api/v1/psm/invoices",
        {
            "purchase_order_id": po_id,
            "invoice_number": "INV-BAD",
            "billed_quantity": 4,
            "billed_amount": "40000.00",
        },
        format="json",
    ).data["id"]
    r_bad_v = acc.post(f"/api/v1/psm/invoices/{inv_bad}/verify", {}, format="json")
    assert r_bad_v.status_code == 200 and r_bad_v.data["status"] == "on_hold"

    inv_ok = acc.post(
        "/api/v1/psm/invoices",
        {
            "purchase_order_id": po_id,
            "invoice_number": "INV-PART-1",
            "billed_quantity": 2,
            "billed_amount": "20000.00",
        },
        format="json",
    ).data["id"]
    r_ok_v = acc.post(f"/api/v1/psm/invoices/{inv_ok}/verify", {}, format="json")
    assert r_ok_v.status_code == 200 and r_ok_v.data["status"] == "verified"
    r_pay1 = acc.post(f"/api/v1/psm/invoices/{inv_ok}/pay", {"amount": "10000.00"}, format="json")
    assert r_pay1.status_code == 201 and r_pay1.data["is_partial"] is True
    r_pay2 = acc.post(f"/api/v1/psm/invoices/{inv_ok}/pay", {"amount": "10000.00"}, format="json")
    assert r_pay2.status_code == 201 and r_pay2.data["is_partial"] is False


def test_journey_bw_psm_03_05_high_value_final_approval_and_tender(stub_iam):
    # BW-PSM-03, BW-PSM-05, PSM-UC-012, PSM-UC-022, CFR-PSM-007, AFR-PSM-032..036, BR-PSM-010, BR-PSM-023
    seed_default_policy()
    ps = _actor(stub_iam, uid=9201, role="ps_admin")
    v_id = ps.post(
        "/api/v1/psm/vendors",
        {
            "name": "Tender Corp",
            "gstin": "23AABCU9603R1ZM",
            "bank_account_number": "998877665544",
            "bank_ifsc": "SBIN0001234",
            "bank_name": "SBI",
            "compliance_documents": ["ISO", "GST"],
        },
        format="json",
    ).data["id"]
    ps.post(f"/api/v1/psm/vendors/{v_id}/verify", {}, format="json")

    emp = _actor(stub_iam, uid=9202, role="faculty")
    ind_id = emp.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_description": "GPU Server",
            "quantity": 1,
            "estimated_cost": "250000.00",
            "justification": "Research cluster",
        },
        format="json",
    ).data["id"]

    da = _actor(stub_iam, uid=9203, role="deptadmin_cse")
    da.post(f"/api/v1/psm/indents/{ind_id}/stock-check", {}, format="json")
    da.post(f"/api/v1/psm/indents/{ind_id}/review", {"decision": "approve"}, format="json")

    hod = _actor(stub_iam, uid=9204, role="HOD (CSE)")
    hod.post(f"/api/v1/psm/indents/{ind_id}/recommend", {"decision": "recommend"}, format="json")

    ps = _actor(stub_iam, uid=9201, role="ps_admin")
    r_pr = ps.post(f"/api/v1/psm/indents/{ind_id}/procurement-review", {}, format="json")
    assert r_pr.data["procurement_method"] == "tender"
    assert r_pr.data["status"] == "awaiting_final_approval"

    director = _actor(stub_iam, uid=9205, role="Director")
    r_fin = director.post(
        f"/api/v1/psm/indents/{ind_id}/final-decision", {"decision": "approve"}, format="json"
    )
    assert r_fin.status_code == 200 and r_fin.data["status"] == "procurement_authorized"

    ps = _actor(stub_iam, uid=9201, role="ps_admin")
    t_id = ps.post(
        "/api/v1/psm/tenders",
        {
            "indent_id": ind_id,
            "title": "GPU Server Tender",
            "scope": "1x GPU node",
            "evaluation_criteria": "70% Tech / 30% Fin",
            "submission_deadline": "2030-01-01T12:00:00Z",
        },
        format="json",
    ).data["id"]
    assert ps.post(f"/api/v1/psm/tenders/{t_id}/publish", {}, format="json").status_code == 200
    b_id = ps.post(
        f"/api/v1/psm/tenders/{t_id}/bids",
        {"vendor_id": v_id, "quoted_amount": "240000.00"},
        format="json",
    ).data["id"]
    assert (
        ps.post(
            f"/api/v1/psm/tenders/{t_id}/evaluate",
            {
                "evaluations": [
                    {
                        "bid_id": b_id,
                        "technical_score": "92.00",
                        "financial_score": "95.00",
                        "evaluation_notes": "Meets spec",
                    }
                ],
                "committee_members": ["Chair A", "Member B"],
                "committee_minutes": "Recommended L1 compliant bid",
            },
            format="json",
        ).status_code
        == 200
    )
    assert (
        ps.post(f"/api/v1/psm/tenders/{t_id}/award", {"bid_id": b_id}, format="json").status_code
        == 200
    )
    assert (
        ps.post(
            "/api/v1/psm/purchase-orders",
            {
                "indent_id": ind_id,
                "vendor_id": v_id,
                "tender_id": t_id,
                "unit_price": "240000.00",
                "planned_delivery_date": "2026-12-30",
            },
            format="json",
        ).status_code
        == 201
    )


def test_journey_bw_psm_06_07_08_10_discrepancy_modify_transfer_and_audit(stub_iam):
    # BW-PSM-06, BW-PSM-07, BW-PSM-08, BW-PSM-10, PSM-UC-008, 010, 014, 015, 020, 021, 023, 030..035
    # CFR-PSM-011, CFR-PSM-012, CFR-PSM-015..020, AFR-PSM-048..055, AFR-PSM-067..092, BR-PSM-019, 021, 024, 027
    seed_default_policy()
    ps = _actor(stub_iam, uid=9301, role="ps_admin")
    v_id = ps.post(
        "/api/v1/psm/vendors",
        {
            "name": "FixCo",
            "gstin": "23AABCU9603R1ZM",
            "bank_account_number": "112233445566",
            "bank_ifsc": "SBIN0001234",
            "bank_name": "SBI",
            "compliance_documents": ["GST"],
        },
        format="json",
    ).data["id"]
    ps.post(f"/api/v1/psm/vendors/{v_id}/verify", {}, format="json")
    item_id = ps.post(
        "/api/v1/psm/stock/items", {"sku": "TRF-1", "name": "Cables"}, format="json"
    ).data["id"]
    loc_src = ps.post(
        "/api/v1/psm/stock/locations",
        {"code": "CEN-J", "name": "Central", "department": "CENTRAL", "is_central": True},
        format="json",
    ).data["id"]
    loc_dst = ps.post(
        "/api/v1/psm/stock/locations",
        {"code": "CSE-J", "name": "CSE", "department": "CSE"},
        format="json",
    ).data["id"]
    ps.post(
        "/api/v1/psm/stock/adjustments",
        {
            "item_id": item_id,
            "location_id": loc_src,
            "quantity_delta": 10,
            "reason": "Init",
            "entry_type": "opening",
        },
        format="json",
    )

    # BW-PSM-08: inter-departmental stock transfer (PSM-UC-021 -> 033 -> 034)
    da = _actor(stub_iam, uid=9302, role="deptadmin_cse")
    trf_id = da.post(
        "/api/v1/psm/transfers",
        {
            "item_id": item_id,
            "source_location_id": loc_src,
            "destination_location_id": loc_dst,
            "quantity": 4,
        },
        format="json",
    ).data["id"]
    assert da.post(f"/api/v1/psm/transfers/{trf_id}/dispatch", {}, format="json").status_code == 200
    assert da.post(f"/api/v1/psm/transfers/{trf_id}/confirm", {}, format="json").status_code == 200
    assert StockLedgerEntry.objects.filter(entry_type="transfer_out", source_ref_id=trf_id).exists()
    assert StockLedgerEntry.objects.filter(entry_type="transfer_in", source_ref_id=trf_id).exists()

    # BW-PSM-07: HOD requests changes -> Employee modifies -> re-enters review
    emp = _actor(stub_iam, uid=9303, role="faculty")
    ind_id = emp.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_description": "Projector",
            "quantity": 2,
            "estimated_cost": "30000.00",
            "justification": "Lecture hall",
        },
        format="json",
    ).data["id"]
    da = _actor(stub_iam, uid=9302, role="deptadmin_cse")
    da.post(f"/api/v1/psm/indents/{ind_id}/stock-check", {}, format="json")
    da.post(f"/api/v1/psm/indents/{ind_id}/review", {"decision": "approve"}, format="json")
    hod = _actor(stub_iam, uid=9304, role="HOD (CSE)")
    assert (
        hod.post(
            f"/api/v1/psm/indents/{ind_id}/recommend",
            {"decision": "request_changes", "reason": "Clarify specs"},
            format="json",
        ).data["status"]
        == "changes_requested"
    )
    emp = _actor(stub_iam, uid=9303, role="faculty")
    assert (
        emp.patch(
            f"/api/v1/psm/indents/{ind_id}",
            {"item_description": "HD Projector 4000lm"},
            format="json",
        ).data["status"]
        == "submitted"
    )
    da = _actor(stub_iam, uid=9302, role="deptadmin_cse")
    da.post(f"/api/v1/psm/indents/{ind_id}/stock-check", {}, format="json")
    da.post(f"/api/v1/psm/indents/{ind_id}/review", {"decision": "approve"}, format="json")
    hod = _actor(stub_iam, uid=9304, role="HOD (CSE)")
    hod.post(f"/api/v1/psm/indents/{ind_id}/recommend", {"decision": "recommend"}, format="json")
    ps = _actor(stub_iam, uid=9301, role="ps_admin")
    ps.post(f"/api/v1/psm/indents/{ind_id}/procurement-review", {}, format="json")
    po_id = ps.post(
        "/api/v1/psm/purchase-orders",
        {
            "indent_id": ind_id,
            "vendor_id": v_id,
            "unit_price": "15000.00",
            "planned_delivery_date": "2026-12-20",
        },
        format="json",
    ).data["id"]

    # BW-PSM-06 & BW-PSM-10: discrepancy with evidence, comms, and replacement GRN
    emp = _actor(stub_iam, uid=9303, role="faculty")
    grn_id = emp.post(
        "/api/v1/psm/grns",
        {
            "purchase_order_id": po_id,
            "received_quantity": 2,
            "accepted_quantity": 1,
            "rejected_quantity": 1,
        },
        format="json",
    ).data["id"]
    case_id = emp.post(
        "/api/v1/psm/discrepancies",
        {
            "grn_id": grn_id,
            "discrepancy_type": "damage",
            "affected_quantity": 1,
            "description": "Lens cracked",
            "requested_resolution": "replacement",
            "evidence_url": "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWx/view",
            "evidence_filename": "damage.jpg",
        },
        format="json",
    ).data["id"]
    ps = _actor(stub_iam, uid=9301, role="ps_admin")
    assert (
        ps.post(
            f"/api/v1/psm/discrepancies/{case_id}/communications",
            {"sender_label": "PS Admin", "message": "Requested replacement"},
            format="json",
        ).status_code
        == 201
    )
    assert (
        ps.post(
            f"/api/v1/psm/discrepancies/{case_id}/resolve",
            {
                "resolution_action": "await_replacement",
                "resolution_notes": "Vendor shipping 1 unit",
            },
            format="json",
        ).data["status"]
        == "replacement_awaited"
    )
    emp = _actor(stub_iam, uid=9303, role="faculty")
    rep_grn = emp.post(
        "/api/v1/psm/grns",
        {
            "purchase_order_id": po_id,
            "replacement_for_case_id": case_id,
            "received_quantity": 1,
            "accepted_quantity": 1,
            "rejected_quantity": 0,
        },
        format="json",
    ).data["id"]
    assert emp.post(f"/api/v1/psm/grns/{rep_grn}/confirm", {}, format="json").status_code == 200
    assert emp.post(f"/api/v1/psm/grns/{grn_id}/confirm", {}, format="json").status_code == 200

    # PSM-UC-010, PSM-UC-014, PSM-UC-015, PSM-UC-030, PSM-UC-031: reports, financial reports, audit, policy
    aud = _actor(stub_iam, uid=9305, role="Auditor")
    assert aud.get("/api/v1/psm/audit").status_code == 200
    assert (
        aud.post(
            "/api/v1/psm/reports/generate", {"report_type": "financial"}, format="json"
        ).status_code
        == 200
    )
    assert (
        aud.post(
            "/api/v1/psm/reports/generate", {"report_type": "procurement"}, format="json"
        ).status_code
        == 200
    )
    assert (
        aud.post(
            "/api/v1/psm/reports/generate", {"report_type": "stock"}, format="json"
        ).status_code
        == 200
    )
    assert aud.get("/api/v1/psm/dashboard").status_code == 200
    assert ReportGenerationLog.objects.count() >= 3
    assert PsmAuditLog.objects.count() >= 10
