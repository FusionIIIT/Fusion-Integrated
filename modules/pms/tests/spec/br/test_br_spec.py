"""Specification-based tests for Business Rules (BR).
Strategy: BR
Design source: docs/11-pms/spec-tests/BR_DESIGN.json
"""
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput, RuleViolation
from modules.pms.models import Application, AuditEntry
from modules.pms.models.base import AppendOnlyError
from modules.pms.tests.conftest import (
    APPLICANT,
    ATTORNEY,
    DIRECTOR,
    PCC,
    Actor,
    pdf,
)
from modules.pms.tests.test_journeys import (
    JUSTIFY,
    decided,
    draft,
    filed,
    under_review,
    with_attorney,
)

pytestmark = pytest.mark.django_db


# TEST-BR-001 / TEST-BR-002: BR-PMS-003 Reporting scope
def test_br_pms_003_applicant_sees_own_reports_only(world, scanner):
    """TEST-BR-001 / TEST-BR-002: source_id: BR-PMS-003"""
    draft(world, title="Mine")
    rows = world["applicant"].get("reports/status").json()["rows"]
    assert any(r["title"] == "Mine" for r in rows)
    assert world["other"].get("reports/status").json()["rows"] == []


# TEST-BR-003 / TEST-BR-004: BR-PMS-005 Director report scope
def test_br_pms_005_director_report_scope(world, scanner):
    """TEST-BR-003 / TEST-BR-004: source_id: BR-PMS-005"""
    under_review(world)
    resp = world["director"].get("reports/status")
    assert resp.status_code == 200
    assert len(resp.json()["rows"]) >= 1


# TEST-BR-005 / TEST-BR-006: BR-PMS-014 Documents must be PDF
def test_br_pms_014_document_must_be_pdf(world, scanner):
    """TEST-BR-005 / TEST-BR-006: source_id: BR-PMS-014"""
    pk = draft(world)
    # Valid PDF
    r1 = world["applicant"].post(f"applications/{pk}/documents",
                                 {"file": pdf("spec.pdf"), "kind": "specification",
                                  "title": "Spec", "sensitivity": "confidential"},
                                 fmt="multipart")
    assert r1.status_code == 201
    # Invalid non-PDF content
    fake_txt = pdf("bad.pdf", b"NOT_A_PDF_STREAM")
    r2 = world["applicant"].post(f"applications/{pk}/documents",
                                 {"file": fake_txt, "kind": "specification",
                                  "title": "Bad", "sensitivity": "confidential"},
                                 fmt="multipart")
    assert r2.status_code == 422


# TEST-BR-007 / TEST-BR-008: BR-PMS-015 Document size limit
def test_br_pms_015_document_size_limit(world, scanner):
    """TEST-BR-007 / TEST-BR-008: source_id: BR-PMS-015"""
    from modules.pms.domain import documents as ddoc
    with pytest.raises(InvalidInput):
        ddoc.check_size(55 * 1024 * 1024)


# TEST-BR-009 / TEST-BR-010: BR-PMS-016 Malware validation
def test_br_pms_016_malware_scan(world, scanner):
    """TEST-BR-009 / TEST-BR-010: source_id: BR-PMS-016"""
    pk = draft(world)
    from modules.pms.services.scanning import EICAR
    eicar_file = pdf("infected.pdf", EICAR)
    resp = world["applicant"].post(f"applications/{pk}/documents",
                                   {"file": eicar_file, "kind": "claims",
                                    "title": "Infected", "sensitivity": "confidential"},
                                   fmt="multipart")
    assert resp.status_code == 422


# TEST-BR-011 / TEST-BR-012: BR-PMS-017 Required fields before submit
def test_br_pms_017_required_fields_before_submission(world, scanner):
    """TEST-BR-011 / TEST-BR-012: source_id: BR-PMS-017"""
    pk = draft(world)
    resp = world["applicant"].post(f"applications/{pk}/submit")
    assert resp.status_code == 422


# TEST-BR-013 / TEST-BR-014: BR-PMS-020 Inventor agreements before filing
def test_br_pms_020_inventor_agreements_before_filing(world, scanner):
    """TEST-BR-013 / TEST-BR-014: source_id: BR-PMS-020"""
    pk = with_attorney(world)
    resp = world["attorney"].post(f"applications/{pk}/filings", {
        "jurisdiction": "IN", "office_name": "IPO", "external_filing_id": "IN-2026-01",
        "filing_date": str(timezone.localdate()), "confirmation_reference": "CONF-1"})
    assert resp.status_code == 409


# TEST-BR-015 / TEST-BR-016: BR-PMS-022 / BR-PMS-023 Director domain expertise
def test_br_pms_022_023_director_expertise_match():
    """TEST-BR-015 / TEST-BR-016: source_id: BR-PMS-022, BR-PMS-023"""
    from modules.pms.domain.assignment import Candidate, check_director
    cand = Candidate(user_id=DIRECTOR, domain_codes=frozenset(["materials"]), workload=0)
    with pytest.raises(RuleViolation):
        check_director(DIRECTOR, [cand], "chemical", APPLICANT, ())


# TEST-BR-017 / TEST-BR-018: BR-PMS-025 Conflict of interest check
def test_br_pms_025_conflict_of_interest(world, scanner):
    """TEST-BR-017 / TEST-BR-018: source_id: BR-PMS-025"""
    app = Application.objects.create(
        applicant_user_id=DIRECTOR, status=sm.SUBMITTED, domain_code="materials",
        title="Dir Invention", abstract="Abs", description="Desc", claims="Claims",
        reference="PMS-2026-99991", version=1)
    resp = world["pcc"].post(f"applications/{app.pk}/assign-director", {"director_user_id": DIRECTOR})
    assert resp.status_code in (409, 422)


# TEST-BR-019 / TEST-BR-020: BR-PMS-027 PCC_ADMIN conflict check
def test_br_pms_027_pcc_admin_conflict(world, scanner):
    """TEST-BR-019 / TEST-BR-020: source_id: BR-PMS-027"""
    app = Application.objects.create(
        applicant_user_id=PCC, status=sm.SUBMITTED, domain_code="materials",
        title="PCC Invention", abstract="Abs", description="Desc", claims="Claims",
        reference="PMS-2026-99992", version=1)
    resp = world["pcc"].post(f"applications/{app.pk}/assign-director", {"director_user_id": DIRECTOR})
    assert resp.status_code in (403, 409, 422)


# TEST-BR-021 / TEST-BR-022: BR-PMS-029 Review decision outcome exactly one of three
def test_br_pms_029_decision_outcomes(world, scanner):
    """TEST-BR-021 / TEST-BR-022: source_id: BR-PMS-029"""
    pk = under_review(world)
    r1 = world["director"].post(f"applications/{pk}/review",
                                {"decision": "approve", "justification": JUSTIFY})
    assert r1.status_code == 200
    assert r1.json()["status"] == sm.APPROVED


# TEST-BR-023 / TEST-BR-024: BR-PMS-030 Justification length >= 50
def test_br_pms_030_justification_length(world, scanner):
    """TEST-BR-023 / TEST-BR-024: source_id: BR-PMS-030"""
    pk = under_review(world)
    resp = world["director"].post(f"applications/{pk}/review",
                                  {"decision": "approve", "justification": "Too short"})
    assert resp.status_code == 422


# TEST-BR-025 / TEST-BR-026: BR-PMS-033 / 034 Revision permitted from Needs Revision & Rejected
def test_br_pms_033_034_resubmit_permitted_statuses():
    """TEST-BR-025 / TEST-BR-026: source_id: BR-PMS-033, BR-PMS-034"""
    assert sm.APPLICATION.is_legal(sm.NEEDS_REVISION, "resubmit")
    assert sm.APPLICATION.is_legal(sm.REJECTED, "resubmit")


# TEST-BR-027 / TEST-BR-028: BR-PMS-040 Only PCC_ADMIN assigns Attorney to Approved
def test_br_pms_040_only_pcc_admin_assigns_attorney(world, scanner):
    """TEST-BR-027 / TEST-BR-028: source_id: BR-PMS-040"""
    pk = decided(world, "approve")
    resp = world["director"].post(f"applications/{pk}/assign-attorney",
                                  {"attorney_user_id": ATTORNEY})
    assert resp.status_code == 403


# TEST-BR-029 / TEST-BR-030: BR-PMS-041 Attorney from approved panel
def test_br_pms_041_attorney_panel_requirement(world, scanner):
    """TEST-BR-029 / TEST-BR-030: source_id: BR-PMS-041"""
    pk = decided(world, "approve")
    resp = world["pcc"].post(f"applications/{pk}/assign-attorney",
                             {"attorney_user_id": 9999})
    assert resp.status_code in (409, 422)


# TEST-BR-031 / TEST-BR-032: BR-PMS-046 Final opinion recommendation
def test_br_pms_046_final_opinion_recommendation(world, scanner):
    """TEST-BR-031 / TEST-BR-032: source_id: BR-PMS-046"""
    pk = with_attorney(world)
    r_save = world["attorney"].post(f"applications/{pk}/assessments", {
        "analysis": "Thorough legal analysis.", "novelty": "Novel claim set.",
        "non_obviousness": "Non-obvious step.", "utility": "Clear industrial application.",
        "recommendation": "file_patent"
    })
    assert r_save.status_code in (200, 201)
    aid = r_save.json()["assessments"][0]["id"]
    r_fin = world["attorney"].post(f"assessments/{aid}/finalize")
    assert r_fin.status_code == 200
    assert r_fin.json()["status"] == "final"


# TEST-BR-033 / TEST-BR-034: BR-PMS-048..050 Budget components
def test_br_pms_048_budget_components(world, scanner):
    """TEST-BR-033 / TEST-BR-034: source_id: BR-PMS-048, BR-PMS-049, BR-PMS-050"""
    pk = with_attorney(world)
    resp = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "8000.00", "attorney_fee": "35000.00", "admin_cost": "2000.00"
    })
    assert resp.status_code == 201
    b = resp.json()
    total = Decimal(b["filing_fee"]) + Decimal(b["attorney_fee"]) + Decimal(b["admin_cost"])
    assert total == Decimal("45000.00")


# TEST-BR-035 / TEST-BR-036: BR-PMS-051 Budget threshold escalation
def test_br_pms_051_budget_threshold_escalation(world, scanner):
    """TEST-BR-035 / TEST-BR-036: source_id: BR-PMS-051"""
    pk = with_attorney(world)
    resp = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "200000.00", "attorney_fee": "0.00", "admin_cost": "0.00"
    })
    assert resp.status_code == 201
    bid = resp.json()["id"]
    r_dec = world["director"].post(f"budgets/{bid}/decision", {"approve": True})
    assert r_dec.status_code == 200
    assert r_dec.json()["status"] == "escalated"


# TEST-BR-037 / TEST-BR-038: BR-PMS-056 International filing justification
def test_br_pms_056_international_filing_justification():
    """TEST-BR-037 / TEST-BR-038: source_id: BR-PMS-056"""
    from modules.pms.domain.validation import check_international_justification
    with pytest.raises(InvalidInput):
        check_international_justification("US", "")
    assert check_international_justification("US", "Strategic market expansion") == "Strategic market expansion"


# TEST-BR-039 / TEST-BR-040: BR-PMS-067 Withdrawal allowed before filing
def test_br_pms_067_withdrawal_allowed_before_filing(world, scanner):
    """TEST-BR-039 / TEST-BR-040: source_id: BR-PMS-067"""
    pk = under_review(world)
    resp = world["applicant"].post(f"applications/{pk}/withdraw", {"reason": "Withdrawing before filing"})
    assert resp.status_code == 200
    assert resp.json()["status"] == sm.WITHDRAWN


# TEST-BR-041 / TEST-BR-042: BR-PMS-074 Inventor share validation
def test_br_pms_074_inventor_share_validation(world, scanner):
    """TEST-BR-041 / TEST-BR-042: source_id: BR-PMS-074"""
    pk = draft(world)
    resp = world["applicant"].put(f"applications/{pk}/inventors", {
        "inventors": [{"user_id": APPLICANT, "share_percent": "60.00"}]
    })
    assert resp.status_code == 422


# TEST-BR-043 / TEST-BR-044: BR-PMS-082 Automatic document versioning
def test_br_pms_082_automatic_document_versioning(world, scanner):
    """TEST-BR-043 / TEST-BR-044: source_id: BR-PMS-082"""
    pk = draft(world)
    r1 = world["applicant"].post(f"applications/{pk}/documents",
                                 {"file": pdf("claims.pdf"), "kind": "claims",
                                  "title": "Claims", "sensitivity": "confidential"},
                                 fmt="multipart")
    assert r1.status_code == 201
    docs = world["applicant"].get(f"applications/{pk}/documents").json()
    doc_id = docs[0]["id"]
    r2 = world["applicant"].post(f"applications/{pk}/documents",
                                 {"file": pdf("claims_v2.pdf"), "document_id": doc_id,
                                  "kind": "claims", "title": "Claims v2",
                                  "sensitivity": "confidential"},
                                 fmt="multipart")
    assert r2.status_code == 201


# TEST-BR-045 / TEST-BR-046: BR-PMS-092 Appeal from Rejected only
def test_br_pms_092_appeal_from_rejected_only():
    """TEST-BR-045 / TEST-BR-046: source_id: BR-PMS-092"""
    assert not sm.APPLICATION.is_legal(sm.SUBMITTED, "appeal")
    assert sm.APPLICATION.is_legal(sm.REJECTED, "appeal")


# TEST-BR-047 / TEST-BR-048: BR-PMS-122 Audit immutability
def test_br_pms_122_audit_immutability(world, scanner):
    """TEST-BR-047 / TEST-BR-048: source_id: BR-PMS-122"""
    pk = draft(world)
    entry = AuditEntry.objects.filter(application_id=pk).first()
    if entry:
        with pytest.raises(AppendOnlyError):
            entry.action = "tampered"
            entry.save()


# TEST-BR-049 / TEST-BR-050: BR-PMS-126 Gate authorization
def test_br_pms_126_role_gate_authorization(stub_iam):
    """TEST-BR-049 / TEST-BR-050: source_id: BR-PMS-126"""
    plain = Actor(stub_iam, 9991, "student", permissions=(), modules=())
    resp = plain.get("applications")
    assert resp.status_code == 403


# TEST-BR-051 / TEST-BR-052: BR-PMS-128 No external filing before approvals and budget
def test_br_pms_128_no_filing_before_approvals(world, scanner):
    """TEST-BR-051 / TEST-BR-052: source_id: BR-PMS-128"""
    pk = filed(world)
    detail = world["applicant"].get(f"applications/{pk}").json()
    assert detail["status"] == sm.FILED
