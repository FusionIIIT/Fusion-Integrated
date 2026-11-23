"""Specification-based tests for Use Cases (UC).
Strategy: UC
Design source: docs/11-pms/spec-tests/UC_DESIGN.json
"""
import pytest

from modules.pms.domain import state_machine as sm
from modules.pms.models import Application
from modules.pms.tests.conftest import (
    ATTORNEY,
    DIRECTOR,
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


# TEST-UC-001 / 002: UC-PMS-001 Submit Patent Application
def test_uc_pms_001_submit_application(world, scanner):
    """TEST-UC-001: source_id: UC-PMS-001 Main Flow"""
    pk = submitted(world)
    app = Application.objects.get(pk=pk)
    assert app.status == sm.SUBMITTED
    assert app.reference.startswith("PMS-2026-")


def test_uc_pms_001_alternative_incomplete(world, scanner):
    """TEST-UC-002: source_id: UC-PMS-001 Alternative A1"""
    pk = draft(world)
    resp = world["applicant"].post(f"applications/{pk}/submit")
    assert resp.status_code == 422


# TEST-UC-003 / 004: UC-PMS-002 Track Own Status
def test_uc_pms_002_track_status(world, scanner):
    """TEST-UC-003: source_id: UC-PMS-002 Main Flow"""
    pk = submitted(world)
    r = world["applicant"].get(f"applications/{pk}")
    assert r.status_code == 200
    assert r.json()["status"] == sm.SUBMITTED


def test_uc_pms_002_alternative_other_applicant(world, scanner):
    """TEST-UC-004: source_id: UC-PMS-002 Alternative A1"""
    pk = submitted(world)
    # Other applicant cannot view
    assert world["other"].get(f"applications/{pk}").status_code == 404


# TEST-UC-005 / 006: UC-PMS-003 Manage Co-Inventors
def test_uc_pms_003_manage_co_inventors(world, scanner):
    """TEST-UC-005: source_id: UC-PMS-003 Main Flow"""
    pk = draft(world)
    r = world["applicant"].put(f"applications/{pk}/inventors", {
        "inventors": [
            {"user_id": 1001, "share_percent": "70"},
            {"user_id": 1002, "share_percent": "30"}
        ]
    })
    assert r.status_code == 200


def test_uc_pms_003_alternative_invalid_shares(world, scanner):
    """TEST-UC-006: source_id: UC-PMS-003 Alternative A1"""
    pk = draft(world)
    r = world["applicant"].put(f"applications/{pk}/inventors", {
        "inventors": [
            {"user_id": 1001, "share_percent": "80"},
            {"user_id": 1002, "share_percent": "30"}
        ]
    })
    assert r.status_code == 422


# TEST-UC-007 / 008: UC-PMS-004 Prior Art Search
def test_uc_pms_004_prior_art_search(world, scanner):
    """TEST-UC-007: source_id: UC-PMS-004 Main Flow"""
    pk = draft(world)
    a = world["applicant"]
    r1 = a.post(f"applications/{pk}/prior-art", {"kind": "patent", "identifier": "US1",
                                                "title": "Graphene anode coating"})
    assert r1.status_code == 201
    r2 = a.post("prior-art/searches", {"query": "graphene coating", "application_id": pk})
    assert r2.status_code == 200


# TEST-UC-009 / 010: UC-PMS-005 Revise and Resubmit
def test_uc_pms_005_revise_and_resubmit(world, scanner):
    """TEST-UC-009: source_id: UC-PMS-005 Main Flow"""
    pk = decided(world, "needs_revision")
    a = world["applicant"]
    assert a.patch(f"applications/{pk}", {"claims": "1. A narrower claim."}).status_code == 200
    r_rev = a.post(f"applications/{pk}/resubmit", {
        "responses": {"review": "Narrowed claims to tested range as requested by Director"}
    })
    assert r_rev.status_code == 200
    assert r_rev.json()["status"] == sm.RESUBMITTED


def test_uc_pms_005_alternative_unchanged(world, scanner):
    """TEST-UC-010: source_id: UC-PMS-005 Alternative A1"""
    pk = decided(world, "needs_revision")
    # Empty responses
    r = world["applicant"].post(f"applications/{pk}/resubmit", {"responses": {}})
    assert r.status_code == 422


# TEST-UC-011 / 012: UC-PMS-006 Withdraw
def test_uc_pms_006_withdraw(world, scanner):
    """TEST-UC-011: source_id: UC-PMS-006 Main Flow"""
    pk = under_review(world)
    r = world["applicant"].post(f"applications/{pk}/withdraw", {"reason": "Cancelled research"})
    assert r.status_code == 200
    assert r.json()["status"] == sm.WITHDRAWN


def test_uc_pms_006_alternative_post_filing(world, scanner):
    """TEST-UC-012: source_id: UC-PMS-006 Alternative A1"""
    pk = filed(world)
    r = world["applicant"].post(f"applications/{pk}/withdraw", {"reason": "Too late"})
    assert r.status_code == 409


# TEST-UC-013 / 014: UC-PMS-007 Assign Director
def test_uc_pms_007_assign_director(world, scanner):
    """TEST-UC-013: source_id: UC-PMS-007 Main Flow"""
    pk = submitted(world)
    r = world["pcc"].post(f"applications/{pk}/assign-director", {"director_user_id": DIRECTOR})
    assert r.status_code == 200
    assert r.json()["status"] == sm.UNDER_REVIEW


def test_uc_pms_007_alternative_unauthorized(world, scanner):
    """TEST-UC-014: source_id: UC-PMS-007 Alternative A1"""
    pk = submitted(world)
    # Plain applicant cannot assign director
    assert world["applicant"].post(f"applications/{pk}/assign-director", {"director_user_id": DIRECTOR}).status_code == 403


# TEST-UC-015 / 016: UC-PMS-008 Review Application
def test_uc_pms_008_review_application(world, scanner):
    """TEST-UC-015: source_id: UC-PMS-008 Main Flow"""
    pk = under_review(world)
    r = world["director"].post(f"applications/{pk}/review", {"decision": "approve", "justification": JUSTIFY})
    assert r.status_code == 200
    assert r.json()["status"] == sm.APPROVED


def test_uc_pms_008_alternative_unassigned_director(world, scanner):
    """TEST-UC-016: source_id: UC-PMS-008 Alternative A1"""
    pk = under_review(world)
    # Director 2 was not assigned
    r = world["director2"].post(f"applications/{pk}/review", {"decision": "approve", "justification": JUSTIFY})
    assert r.status_code == 403


# TEST-UC-017 / 018: UC-PMS-009 Review and Decide Budget
def test_uc_pms_009_budget_decision(world, scanner):
    """TEST-UC-017: source_id: UC-PMS-009 Main Flow"""
    pk = with_attorney(world)
    r_b = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "5000", "attorney_fee": "20000", "admin_cost": "1000"
    })
    bid = r_b.json()["id"]
    r_dec = world["director"].post(f"budgets/{bid}/decision", {"approve": True})
    assert r_dec.status_code == 200
    assert r_dec.json()["status"] == "approved"


# TEST-UC-019 / 020: UC-PMS-010 / 011 Assign and Accept Attorney
def test_uc_pms_010_011_attorney_assignment(world, scanner):
    """TEST-UC-019 / TEST-UC-020: source_id: UC-PMS-010, UC-PMS-011"""
    pk = decided(world, "approve")
    r = world["pcc"].post(f"applications/{pk}/assign-attorney", {"attorney_user_id": ATTORNEY})
    assert r.status_code == 200
    offer = r.json()["attorney_assignments"][0]["id"]
    r_acc = world["attorney"].post(f"attorney-assignments/{offer}/respond", {"accept": True})
    assert r_acc.status_code == 200
    assert r_acc.json()["status"] == "accepted"
    assert Application.objects.get(pk=pk).status == sm.ATTORNEY_ASSIGNED


# TEST-UC-021: UC-PMS-012 Patentability Assessment
def test_uc_pms_012_patentability_assessment(world, scanner):
    """TEST-UC-021: source_id: UC-PMS-012 Main Flow"""
    pk = with_attorney(world)
    r = world["attorney"].post(f"applications/{pk}/assessments", {
        "analysis": "Solid claim scope.", "novelty": "Novel", "non_obviousness": "Inventive",
        "utility": "Applicable", "recommendation": "file_patent"
    })
    aid = r.json()["assessments"][0]["id"]
    r_fin = world["attorney"].post(f"assessments/{aid}/finalize")
    assert r_fin.status_code == 200
    assert r_fin.json()["status"] == "final"


# TEST-UC-022: UC-PMS-013 Prepare and Record Filing
def test_uc_pms_013_external_filing(world, scanner):
    """TEST-UC-022: source_id: UC-PMS-013 Main Flow"""
    pk = filed(world)
    app = Application.objects.get(pk=pk)
    assert app.status == sm.FILED


# TEST-UC-023: UC-PMS-022 File an Appeal
def test_uc_pms_022_file_appeal(world, scanner):
    """TEST-UC-023: source_id: UC-PMS-022 Main Flow"""
    pk = decided(world, "reject")
    r = world["applicant"].post(f"applications/{pk}/appeal", {
        "grounds": "prior_art_distinction", "justification": "Novelty was misunderstood by reviewer."
    })
    assert r.status_code == 200
    assert r.json()["status"] == sm.APPEAL_SUBMITTED


# TEST-UC-024: UC-PMS-024 System-wide Reports
def test_uc_pms_024_reports(world, scanner):
    """TEST-UC-024: source_id: UC-PMS-024 Main Flow"""
    submitted(world)
    r = world["pcc"].get("reports/status")
    assert r.status_code == 200
    assert any(row["title"] == "Graphene anode" for row in r.json()["rows"])
