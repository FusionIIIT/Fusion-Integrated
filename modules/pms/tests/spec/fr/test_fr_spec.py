"""Specification-based tests for Functional Requirements (FR).
Strategy: FR
Design source: docs/11-pms/spec-tests/FR_DESIGN.json
"""

import pytest

from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Application,
    AuditEntry,
)
from modules.pms.tests.conftest import (
    ATTORNEY,
    DIRECTOR,
    Actor,
    pdf,
)
from modules.pms.tests.test_journeys import (
    JUSTIFY,
    decided,
    draft,
    filed,
    submitted,
    under_review,
    with_attorney,
)

pytestmark = pytest.mark.django_db


# TEST-FR-001: CFR-PMS-001 / PMS-AFR-010 Applicant tracking
def test_cfr_pms_001_applicant_tracking(world, scanner):
    """TEST-FR-001: source_id: CFR-PMS-001, PMS-AFR-010"""
    pk = submitted(world)
    r = world["applicant"].get(f"applications/{pk}")
    assert r.status_code == 200
    assert r.json()["status"] == sm.SUBMITTED


# TEST-FR-002: CFR-PMS-002 / PMS-AFR-023 Director oversight
def test_cfr_pms_002_director_oversight(world, scanner):
    """TEST-FR-002: source_id: CFR-PMS-002, PMS-AFR-023"""
    under_review(world)
    r = world["director"].get("oversight")
    assert r.status_code == 200
    assert "workflow_summary" in r.json() or "counts" in r.json() or len(r.json()) > 0


# TEST-FR-003: CFR-PMS-004 / PMS-AFR-037 Attorney legal advice
def test_cfr_pms_004_attorney_legal_advice(world, scanner):
    """TEST-FR-003: source_id: CFR-PMS-004, PMS-AFR-037"""
    pk = with_attorney(world)
    r = world["attorney"].post(f"applications/{pk}/legal-advice", {
        "advice": "Recommended strategy: file provisional first."
    })
    assert r.status_code in (200, 201)


# TEST-FR-004: CFR-PMS-005 / PMS-AFR-038 Application submission completeness
def test_cfr_pms_005_submission_validation(world, scanner):
    """TEST-FR-004: source_id: CFR-PMS-005, PMS-AFR-038"""
    pk = draft(world)
    # Missing documents
    resp = world["applicant"].post(f"applications/{pk}/submit")
    assert resp.status_code == 422


# TEST-FR-005: CFR-PMS-006 / PMS-AFR-049 Director routing
def test_cfr_pms_006_director_assignment(world, scanner):
    """TEST-FR-005: source_id: CFR-PMS-006, PMS-AFR-049"""
    pk = submitted(world)
    r = world["pcc"].post(f"applications/{pk}/assign-director", {"director_user_id": DIRECTOR})
    assert r.status_code == 200
    assert r.json()["status"] == sm.UNDER_REVIEW


# TEST-FR-006: CFR-PMS-007 / PMS-AFR-058 Director review and justification
def test_cfr_pms_007_director_review_decision(world, scanner):
    """TEST-FR-006: source_id: CFR-PMS-007, PMS-AFR-058"""
    pk = under_review(world)
    r = world["director"].post(f"applications/{pk}/review", {"decision": "approve", "justification": JUSTIFY})
    assert r.status_code == 200
    assert r.json()["status"] == sm.APPROVED


# TEST-FR-007: CFR-PMS-008 / PMS-AFR-066 Revision and resubmission
def test_cfr_pms_008_resubmission(world, scanner):
    """TEST-FR-007: source_id: CFR-PMS-008, PMS-AFR-066"""
    pk = decided(world, "needs_revision")
    a = world["applicant"]
    a.patch(f"applications/{pk}", {"claims": "1. Narrowed claims"})
    r = a.post(f"applications/{pk}/resubmit", {
        "responses": {"review": "Feedback thoroughly addressed in claim 1 by narrowing scope significantly."}
    })
    assert r.status_code == 200
    assert r.json()["status"] == sm.RESUBMITTED


# TEST-FR-008: CFR-PMS-009 / PMS-AFR-074 Attorney assignment
def test_cfr_pms_009_attorney_assignment(world, scanner):
    """TEST-FR-008: source_id: CFR-PMS-009, PMS-AFR-074"""
    pk = decided(world, "approve")
    r = world["pcc"].post(f"applications/{pk}/assign-attorney", {"attorney_user_id": ATTORNEY})
    assert r.status_code == 200
    offer = r.json()["attorney_assignments"][0]["id"]
    r_acc = world["attorney"].post(f"attorney-assignments/{offer}/respond", {"accept": True})
    assert r_acc.status_code == 200
    assert r_acc.json()["status"] == "accepted"


# TEST-FR-009: CFR-PMS-010 / PMS-AFR-082 Patentability assessment
def test_cfr_pms_010_patentability_assessment(world, scanner):
    """TEST-FR-009: source_id: CFR-PMS-010, PMS-AFR-082"""
    pk = with_attorney(world)
    r = world["attorney"].post(f"applications/{pk}/assessments", {
        "analysis": "Analysis", "novelty": "Novel", "non_obviousness": "Non-obvious",
        "utility": "Useful", "recommendation": "file_patent"
    })
    assert r.status_code in (200, 201)
    aid = r.json()["assessments"][0]["id"]
    r_fin = world["attorney"].post(f"assessments/{aid}/finalize")
    assert r_fin.status_code == 200


# TEST-FR-010: CFR-PMS-011 / PMS-AFR-090 Budget review
def test_cfr_pms_011_budget_review(world, scanner):
    """TEST-FR-010: source_id: CFR-PMS-011, PMS-AFR-090"""
    pk = with_attorney(world)
    b = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "6000", "attorney_fee": "20000", "admin_cost": "1000"
    }).json()["id"]
    r = world["director"].post(f"budgets/{b}/decision", {"approve": True})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


# TEST-FR-011: CFR-PMS-012 / PMS-AFR-101 External filing
def test_cfr_pms_012_filing(world, scanner):
    """TEST-FR-011: source_id: CFR-PMS-012, PMS-AFR-101"""
    pk = filed(world)
    assert Application.objects.get(pk=pk).status == sm.FILED


# TEST-FR-012: CFR-PMS-015 / PMS-AFR-125 Withdrawal
def test_cfr_pms_015_withdrawal(world, scanner):
    """TEST-FR-012: source_id: CFR-PMS-015, PMS-AFR-125"""
    pk = under_review(world)
    r = world["applicant"].post(f"applications/{pk}/withdraw", {"reason": "Withdrawn"})
    assert r.status_code == 200
    assert r.json()["status"] == sm.WITHDRAWN


# TEST-FR-013: CFR-PMS-016 / PMS-AFR-132 Inventors and shares
def test_cfr_pms_016_inventor_management(world, scanner):
    """TEST-FR-013: source_id: CFR-PMS-016, PMS-AFR-132"""
    pk = draft(world)
    r = world["applicant"].put(f"applications/{pk}/inventors", {
        "inventors": [
            {"user_id": 1001, "share_percent": "50"},
            {"user_id": 1002, "share_percent": "50"}
        ]
    })
    assert r.status_code == 200


# TEST-FR-014: CFR-PMS-017 / PMS-AFR-141 Prior art query
def test_cfr_pms_017_prior_art(world, scanner):
    """TEST-FR-014: source_id: CFR-PMS-017, PMS-AFR-141"""
    pk = draft(world)
    r = world["applicant"].post("prior-art/searches", {"query": "novel coating", "application_id": pk})
    assert r.status_code == 200


# TEST-FR-015: CFR-PMS-018 / PMS-AFR-150 Document versions
def test_cfr_pms_018_document_versions(world, scanner):
    """TEST-FR-015: source_id: CFR-PMS-018, PMS-AFR-150"""
    pk = draft(world)
    r = world["applicant"].post(f"applications/{pk}/documents",
                                {"file": pdf(), "kind": "specification",
                                 "title": "Complete spec", "sensitivity": "confidential"},
                                fmt="multipart")
    assert r.status_code == 201


# TEST-FR-016: CFR-PMS-020 / PMS-AFR-165 Appeals
def test_cfr_pms_020_appeals(world, scanner):
    """TEST-FR-016: source_id: CFR-PMS-020, PMS-AFR-165"""
    pk = decided(world, "reject")
    r = world["applicant"].post(f"applications/{pk}/appeal", {
        "grounds": "examination_error", "justification": "Prior art cited in error."
    })
    assert r.status_code == 200
    assert r.json()["status"] == sm.APPEAL_SUBMITTED


# TEST-FR-017: CFR-PMS-024 / PMS-AFR-207 Audit log
def test_cfr_pms_024_audit_log(world, scanner):
    """TEST-FR-017: source_id: CFR-PMS-024, PMS-AFR-207"""
    pk = draft(world)
    assert AuditEntry.objects.filter(application_id=pk).exists()


# TEST-FR-018: CFR-PMS-025 / PMS-AFR-216 Role gate requirement
def test_cfr_pms_025_role_required(stub_iam):
    """TEST-FR-018: source_id: CFR-PMS-025, PMS-AFR-216"""
    unauthorized = Actor(stub_iam, 9993, "student", permissions=(), modules=())
    assert unauthorized.get("applications").status_code == 403
