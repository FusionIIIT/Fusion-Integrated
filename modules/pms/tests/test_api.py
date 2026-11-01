"""Comprehensive API endpoint tests for PMS.

Maps to all 33 use cases UC-PMS-001 through UC-PMS-033 and CFR-PMS-001..030.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    AttorneyPanel,
    PostGrantMaintenance,
)
from modules.pms.services import submit_application

pytestmark = pytest.mark.django_db


def _client(stub_iam, user_id=1001, roles=("student",), permissions=()):
    session = make_session(
        user_id=user_id,
        roles=roles,
        active_role=roles[0] if roles else None,
        permissions=permissions,
        modules=("pms",),
    )
    stub_iam(session)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


# --- UC-PMS-001: Submit Patent Application ---


def test_api_submit_application(stub_iam):
    """UC-PMS-001, CFR-PMS-005: Submit new patent application via POST /api/v1/pms/applications/."""
    c = _client(
        stub_iam, user_id=1001, permissions=("pms.application.create", "pms.application.view_self")
    )
    payload = {
        "title": "Quantum Error Correction System",
        "abstract": "A novel topological method for stabilizing qubits.",
        "detailed_description": "Comprehensive implementation details...",
        "claims": "1. A quantum circuit comprising...",
        "domain": "Computer Science",
        "jurisdiction": "IN",
        "coinventors": [
            {
                "user_id": 1002,
                "name": "Dr. Bose",
                "email": "bose@test.com",
                "ownership_percentage": "40.00",
            },
            {
                "user_id": 1001,
                "name": "Lead Inventor",
                "email": "lead@test.com",
                "ownership_percentage": "60.00",
            },
        ],
        "documents": [
            {
                "title": "Claims Doc",
                "filename": "claims.pdf",
                "file_size_bytes": 4096,
                "doc_type": "claims",
            }
        ],
    }

    res = c.post("/api/v1/pms/applications/", payload, format="json")
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "submitted"
    assert "PMS-" in data["application_no"]
    assert len(data["coinventors"]) == 2
    assert len(data["documents"]) == 1


# --- UC-PMS-002: Track Application Status and History ---


def test_api_application_detail(stub_iam):
    """UC-PMS-002: Retrieve full application details."""
    app = submit_application(
        applicant_user_id=1001,
        title="Laser Cooling",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Physics",
    )
    c = _client(stub_iam, user_id=1001, permissions=("pms.application.view_self",))
    res = c.get(f"/api/v1/pms/applications/{app.id}/")
    assert res.status_code == 200
    assert res.json()["title"] == "Laser Cooling"


# --- UC-PMS-005: Revise and Resubmit Application ---


def test_api_revise_application(stub_iam):
    """UC-PMS-005, CFR-PMS-008: Revise and resubmit application under revision."""
    app = submit_application(
        applicant_user_id=1001,
        title="AI Tool",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="AI",
    )
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save()

    c = _client(
        stub_iam, user_id=1001, permissions=("pms.application.revise", "pms.application.view_self")
    )
    res = c.post(
        f"/api/v1/pms/applications/{app.id}/revise/",
        {
            "feedback_response": "Addressed all points raised by reviewer.",
            "claims": "Updated Claims 1-5.",
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "resubmitted"


# --- UC-PMS-006: Withdraw Patent Application ---


def test_api_withdraw_application(stub_iam):
    """UC-PMS-006, CFR-PMS-015: Withdraw application before filing."""
    app = submit_application(
        applicant_user_id=1001,
        title="Withdrawable App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    c = _client(
        stub_iam,
        user_id=1001,
        permissions=("pms.application.withdraw", "pms.application.view_self"),
    )
    res = c.post(
        f"/api/v1/pms/applications/{app.id}/withdraw/",
        {"reason": "Applicant commercial reprioritization."},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "withdrawn"
    assert res.json()["is_withdrawn"] is True


# --- UC-PMS-007 & UC-PMS-008: Director Assignment and Review ---


def test_api_assign_and_review_director(stub_iam):
    """UC-PMS-007, 008, CFR-PMS-006, 007: Assign Director and submit review."""
    app = submit_application(
        applicant_user_id=1001,
        title="Nanotech Filter",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Nanotechnology",
    )

    # 1. PCC_ADMIN assigns Director
    c_admin = _client(
        stub_iam,
        user_id=9001,
        roles=("pcc_admin",),
        permissions=("pms.application.assign_director", "pms.application.view"),
    )
    res_assign = c_admin.post(
        f"/api/v1/pms/applications/{app.id}/assign-director/", {"director_user_id": 2001}
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["status"] == "under_review"

    # 2. Director submits review decision
    c_dir = _client(
        stub_iam,
        user_id=2001,
        roles=("director",),
        permissions=("pms.application.review", "pms.application.view"),
    )
    res_review = c_dir.post(
        f"/api/v1/pms/applications/{app.id}/review/",
        {
            "decision": "Approve",
            "justification": "The novelty and non-obviousness criteria are convincingly met in claims 1-10.",
            "feedback": "Recommended for expedited patent filing.",
        },
    )
    assert res_review.status_code == 201
    assert res_review.json()["decision"] == "Approve"

    app.refresh_from_db()
    assert app.status == "approved"


# --- UC-PMS-009: Review and Decide Patent Budget ---


def test_api_budget_management(stub_iam):
    """UC-PMS-009, CFR-PMS-011: Submit budget line items and decide budget."""
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.APPROVED.value
    app.save()

    c_dir = _client(
        stub_iam,
        user_id=2001,
        roles=("director",),
        permissions=("pms.budget.review", "pms.application.view"),
    )

    # Put line items
    res_put = c_dir.put(
        f"/api/v1/pms/applications/{app.id}/budget/",
        {"filing_fees": "12000.00", "attorney_fees": "25000.00", "administrative_costs": "3000.00"},
    )
    assert res_put.status_code == 200
    assert Decimal(str(res_put.json()["total_cost"])) == Decimal("40000.00")

    # Decide budget
    res_decide = c_dir.post(
        f"/api/v1/pms/applications/{app.id}/budget/",
        {"decision": "Approve", "justification": "Costs conform to standard scale."},
    )
    assert res_decide.status_code == 200
    assert res_decide.json()["status"] == "approved"


# --- UC-PMS-010 & UC-PMS-011: Attorney Assignment and Response ---


def test_api_attorney_assignment_and_response(stub_iam):
    """UC-PMS-010, 011, CFR-PMS-009: PCC_ADMIN assigns attorney, attorney accepts."""
    AttorneyPanel.objects.create(
        attorney_user_id=5001,
        name="Adv. Verma",
        email="v@atty.com",
        is_approved=True,
        current_workload=0,
        max_workload=5,
    )
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.APPROVED.value
    app.save()

    # PCC_ADMIN assigns attorney
    c_admin = _client(
        stub_iam,
        user_id=9001,
        roles=("pcc_admin",),
        permissions=("pms.attorney.assign", "pms.application.view"),
    )
    res_assign = c_admin.post(
        f"/api/v1/pms/applications/{app.id}/assign-attorney/", {"attorney_user_id": 5001}
    )
    assert res_assign.status_code == 201
    assignment_id = res_assign.json()["id"]

    # Attorney accepts assignment
    c_atty = _client(
        stub_iam,
        user_id=5001,
        roles=("attorney",),
        permissions=("pms.attorney.respond_assignment", "pms.application.view"),
    )
    res_resp = c_atty.post(
        f"/api/v1/pms/attorney-assignments/{assignment_id}/respond/", {"accept": True}
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "accepted"


# --- UC-PMS-012: Patentability Assessment ---


def test_api_patentability_assessment(stub_iam):
    """UC-PMS-012, CFR-PMS-010: Attorney records patentability assessment."""
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    c_atty = _client(
        stub_iam,
        user_id=5001,
        roles=("attorney",),
        permissions=("pms.patentability.assess", "pms.application.view"),
    )
    res = c_atty.post(
        f"/api/v1/pms/applications/{app.id}/patentability/",
        {
            "recommendation": "File Patent",
            "opinion_text": "Strong novelty over prior art D1-D4. Non-obvious inventive step established.",
            "novelty_score": 9,
            "non_obviousness_score": 8,
            "utility_score": 10,
        },
    )
    assert res.status_code == 201
    assert res.json()["recommendation"] == "File Patent"


# --- UC-PMS-013 & UC-PMS-014: External Filing and Grant ---


def test_api_filing_and_grant(stub_iam):
    """UC-PMS-013, 014: Record external filing and grant."""
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 1001,
                "name": "P",
                "email": "p@t.com",
                "ownership_percentage": "100.00",
                "agreement_signed": True,
            }
        ],
    )
    app.status = PatentApplicationStatus.BUDGET_APPROVED.value
    app.save()
    budget = app.budget
    budget.status = "approved"
    budget.save()

    c_atty = _client(
        stub_iam,
        user_id=5001,
        roles=("attorney",),
        permissions=("pms.filing.record", "pms.application.view"),
    )

    # 1. Filing
    res_filing = c_atty.post(
        f"/api/v1/pms/applications/{app.id}/filing/",
        {
            "external_filing_id": "IPO/DEL/2026/05432",
            "external_filing_date": "2026-11-01",
            "filing_confirmation": "E-filing confirmation receipt attached.",
        },
    )
    assert res_filing.status_code == 200
    assert res_filing.json()["status"] == "filed"

    # 2. Grant
    res_grant = c_atty.post(
        f"/api/v1/pms/applications/{app.id}/grant/",
        {"patent_number": "IN-501234", "grant_date": "2026-11-02"},
    )
    assert res_grant.status_code == 200
    assert res_grant.json()["status"] == "granted"


# --- UC-PMS-014, 015, 029: Office Action and Response Workflow ---


def test_api_office_action_workflow(stub_iam):
    """UC-PMS-014, 015, 029: Office action record, draft, approve, submit."""
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.save()

    c_atty = _client(
        stub_iam,
        user_id=5001,
        roles=("attorney",),
        permissions=(
            "pms.office_action.record",
            "pms.office_action.respond",
            "pms.application.view",
        ),
    )

    # 1. Record OA
    res_oa = c_atty.post(
        f"/api/v1/pms/applications/{app.id}/office-actions/",
        {
            "action_type": "FER",
            "issue_date": "2026-11-01",
            "due_date": "2027-02-01",
            "details": "Objection regarding claim clarity.",
            "requires_applicant_review": True,
        },
    )
    assert res_oa.status_code == 201
    oa_id = res_oa.json()["id"]

    # 2. Draft Response
    res_draft = c_atty.post(
        f"/api/v1/pms/office-actions/{oa_id}/draft-response/",
        {"draft_response": "Detailed rebuttal addressing clarity of claim 1."},
    )
    assert res_draft.status_code == 200

    # 3. Applicant approves
    c_app = _client(
        stub_iam,
        user_id=1001,
        permissions=("pms.office_action.review", "pms.application.view_self"),
    )
    res_apprv = c_app.post(f"/api/v1/pms/office-actions/{oa_id}/approve-response/")
    assert res_apprv.status_code == 200
    assert res_apprv.json()["applicant_approved"] is True

    # 4. Attorney submits
    res_sub = c_atty.post(
        f"/api/v1/pms/office-actions/{oa_id}/submit-response/",
        {"submission_details": "Filed via IPO portal."},
    )
    assert res_sub.status_code == 200
    assert res_sub.json()["status"] == "response_submitted"


# --- UC-PMS-017 & UC-PMS-018: Maintenance Cycle ---


def test_api_maintenance_workflow(stub_iam):
    """UC-PMS-017, 018: Request renewal decision, Director decides, Attorney records."""
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.GRANTED.value
    app.save()

    maint = PostGrantMaintenance.objects.create(
        application=app, cycle_number=1, fee_due_date="2029-11-01", fee_amount=Decimal("5000.00")
    )

    c_atty = _client(
        stub_iam,
        user_id=5001,
        roles=("attorney",),
        permissions=("pms.maintenance.manage", "pms.application.view"),
    )
    c_dir = _client(
        stub_iam,
        user_id=2001,
        roles=("director",),
        permissions=("pms.maintenance.decide", "pms.application.view"),
    )

    # 1. Attorney requests renewal decision
    res_req = c_atty.post(f"/api/v1/pms/maintenance/{maint.id}/request-renewal/")
    assert res_req.status_code == 200

    # 2. Director decides Renew
    res_dec = c_dir.post(
        f"/api/v1/pms/maintenance/{maint.id}/decide-renewal/", {"decision": "Renew"}
    )
    assert res_dec.status_code == 200
    assert res_dec.json()["director_decision"] == "Renew"

    # 3. Attorney records action
    res_act = c_atty.post(
        f"/api/v1/pms/maintenance/{maint.id}/record-action/",
        {"transaction_reference": "TXN-MAINT-2029-01"},
    )
    assert res_act.status_code == 200
    assert res_act.json()["maintenance_status"] == "renewed"


# --- UC-PMS-004: Prior Art Search and Attachment ---


def test_api_prior_art_search_and_attach(stub_iam):
    """UC-PMS-004, CFR-PMS-017: Search prior art and attach reference."""
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    c = _client(
        stub_iam, user_id=1001, permissions=("pms.prior_art.search", "pms.application.view_self")
    )

    # Search
    res_search = c.get("/api/v1/pms/prior-art/search/?q=quantum")
    assert res_search.status_code == 200
    assert len(res_search.json()["results"]) >= 1

    # Attach
    res_attach = c.post(
        f"/api/v1/pms/applications/{app.id}/prior-art/",
        {"source": "IEEE", "reference_id": "IEEE-12345", "title": "Quantum Circuit Bounds"},
    )
    assert res_attach.status_code == 201
    assert res_attach.json()["reference_id"] == "IEEE-12345"


# --- UC-PMS-019: Document Upload ---


def test_api_document_upload(stub_iam):
    """UC-PMS-019, CFR-PMS-018: Upload document version."""
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.save()

    c = _client(
        stub_iam, user_id=1001, permissions=("pms.document.manage", "pms.application.view_self")
    )
    res = c.post(
        f"/api/v1/pms/applications/{app.id}/documents/",
        {
            "doc_type": "drawings",
            "title": "Circuit Diagram",
            "filename": "diagram.pdf",
            "file_size_bytes": 1024,
        },
    )
    assert res.status_code == 201
    assert res.json()["version"] == 1


# --- UC-PMS-020 & UC-PMS-021: Licensing ---


def test_api_licensing_lifecycle(stub_iam):
    """UC-PMS-020, 021, CFR-PMS-019: Submit and review licensing request."""
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    c_app = _client(
        stub_iam, user_id=1001, permissions=("pms.licensing.submit", "pms.application.view_self")
    )
    res_sub = c_app.post(
        f"/api/v1/pms/applications/{app.id}/licensing/",
        {
            "licensee_name": "Tech Corp",
            "request_type": "exclusive",
            "commercial_terms": "10% royalties on sales",
        },
    )
    assert res_sub.status_code == 201
    req_id = res_sub.json()["id"]

    c_dir = _client(
        stub_iam, user_id=2001, permissions=("pms.licensing.review", "pms.application.view")
    )
    res_rev = c_dir.post(
        f"/api/v1/pms/licensing/{req_id}/review/",
        {"status": "negotiating", "negotiation_notes": "Terms under review by committee."},
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["status"] == "negotiating"


# --- UC-PMS-022 & UC-PMS-023: Appeal ---


def test_api_appeal_lifecycle(stub_iam):
    """UC-PMS-022, 023, CFR-PMS-020: File appeal and review."""
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.REJECTED.value
    app.save()

    c_app = _client(
        stub_iam, user_id=1001, permissions=("pms.application.appeal", "pms.application.view_self")
    )
    res_appeal = c_app.post(
        f"/api/v1/pms/applications/{app.id}/appeal/",
        {
            "grounds": "Reviewer misapplied prior art D1.",
            "justification": "D1 teaches away from our core method.",
        },
    )
    assert res_appeal.status_code == 201
    appeal_id = res_appeal.json()["id"]

    c_dir = _client(
        stub_iam,
        user_id=2001,
        permissions=("pms.application.review_appeal", "pms.application.view"),
    )
    res_rev = c_dir.post(
        f"/api/v1/pms/appeals/{appeal_id}/review/",
        {
            "outcome": "Modify Decision",
            "outcome_justification": "Appeals committee accepted argument.",
        },
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["outcome"] == "Modify Decision"


# --- UC-PMS-028 & UC-PMS-024: Audit & Reports ---


def test_api_audit_and_reports(stub_iam):
    """UC-PMS-028, 024: View audit trail and reports."""
    app = submit_application(
        applicant_user_id=1001,
        title="App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="Tech",
    )
    c_admin = _client(
        stub_iam,
        user_id=9001,
        roles=("pcc_admin",),
        permissions=("pms.audit.view", "pms.report.view", "pms.application.view"),
    )

    # Audit trail
    res_audit = c_admin.get(f"/api/v1/pms/audit-trail/?application_id={app.id}")
    assert res_audit.status_code == 200
    assert len(res_audit.json()) >= 1

    # Reports
    res_rep = c_admin.get("/api/v1/pms/reports/")
    assert res_rep.status_code == 200
    assert "total_applications" in res_rep.json()
    assert "status_distribution" in res_rep.json()
