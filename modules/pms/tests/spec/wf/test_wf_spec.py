"""Specification-based tests for Workflows (WF).
Strategy: WF
Design source: docs/11-pms/spec-tests/WF_DESIGN.json
"""
import pytest

from modules.pms.domain import state_machine as sm
from modules.pms.models import Application
from modules.pms.tests.conftest import (
    ATTORNEY,
    DIRECTOR,
    DIRECTOR_2,
)
from modules.pms.tests.test_journeys import (
    JUSTIFY,
    decided,
    filed,
    under_review,
    with_attorney,
)

pytestmark = pytest.mark.django_db


# TEST-WF-001: BW-PMS-01 Initial review approval path
def test_bw_pms_01_initial_approval_path(world, scanner):
    """TEST-WF-001: source_id: BW-PMS-01 main-path"""
    pk = decided(world, "approve")
    assert Application.objects.get(pk=pk).status == sm.APPROVED


# TEST-WF-002: BW-PMS-02 Revision and re-approval path
def test_bw_pms_02_revision_reapproval_path(world, scanner):
    """TEST-WF-002: source_id: BW-PMS-02 main-path"""
    pk = decided(world, "needs_revision")
    a = world["applicant"]
    assert a.patch(f"applications/{pk}", {"claims": "1. A narrower claim."}).status_code == 200
    r_res = a.post(f"applications/{pk}/resubmit", {
        "responses": {"review": "Claim 1 is narrowed to the coating temperature the Director asked about."}
    })
    assert r_res.status_code == 200
    assert r_res.json()["status"] == sm.RESUBMITTED
    # PCC assigns director again
    r_dir = world["pcc"].post(f"applications/{pk}/assign-director", {"director_user_id": DIRECTOR})
    assert r_dir.status_code == 200
    assert r_dir.json()["status"] == sm.UNDER_REVIEW
    # Director approves
    r_app = world["director"].post(f"applications/{pk}/review", {"decision": "approve", "justification": JUSTIFY})
    assert r_app.status_code == 200
    assert r_app.json()["status"] == sm.APPROVED


def _appeal_setup(world):
    pk = decided(world, "reject")
    r_app = world["applicant"].post(f"applications/{pk}/appeal", {
        "grounds": "The cited art is a different field.", "justification": "See claim 4."
    })
    assert r_app.status_code == 200
    appeal = r_app.json()["appeals"][0]["id"]
    world["pcc"].post(f"appeals/{appeal}/assign", {"director_user_id": DIRECTOR_2})
    return pk, appeal


# TEST-WF-003: BW-PMS-03 Appeal remand path
def test_bw_pms_03_appeal_remand_path(world, scanner):
    """TEST-WF-003: source_id: BW-PMS-03 main-path"""
    pk, appeal = _appeal_setup(world)
    r_dec = world["director2"].post(f"appeals/{appeal}/decision", {
        "outcome": "remand", "modified_decision": None, "note": JUSTIFY
    })
    assert r_dec.status_code == 200
    assert r_dec.json()["outcome"] == "remand"
    assert Application.objects.get(pk=pk).status == sm.NEEDS_REVISION


# TEST-WF-004: BW-PMS-04 Appeal rejection-upheld path
def test_bw_pms_04_appeal_upheld_path(world, scanner):
    """TEST-WF-004: source_id: BW-PMS-04 main-path"""
    pk, appeal = _appeal_setup(world)
    r_dec = world["director2"].post(f"appeals/{appeal}/decision", {
        "outcome": "uphold", "modified_decision": None, "note": JUSTIFY
    })
    assert r_dec.status_code == 200
    assert r_dec.json()["outcome"] == "uphold"
    assert Application.objects.get(pk=pk).status == sm.REJECTION_UPHELD


# TEST-WF-005: BW-PMS-05 Appeal modified-decision path
def test_bw_pms_05_appeal_modify_path(world, scanner):
    """TEST-WF-005: source_id: BW-PMS-05 main-path"""
    pk, appeal = _appeal_setup(world)
    r_dec = world["director2"].post(f"appeals/{appeal}/decision", {
        "outcome": "modify", "modified_decision": "approve", "note": JUSTIFY
    })
    assert r_dec.status_code == 200
    assert r_dec.json()["outcome"] == "modify"
    assert Application.objects.get(pk=pk).status == sm.APPROVED


# TEST-WF-006: BW-PMS-06 Attorney assignment acceptance path
def test_bw_pms_06_attorney_acceptance_path(world, scanner):
    """TEST-WF-006: source_id: BW-PMS-06 main-path"""
    pk = with_attorney(world)
    assert Application.objects.get(pk=pk).status == sm.ATTORNEY_ASSIGNED


# TEST-WF-007: BW-PMS-07 Attorney decline path
def test_bw_pms_07_attorney_decline_path(world, scanner):
    """TEST-WF-007: source_id: BW-PMS-07 main-path"""
    pk = decided(world, "approve")
    r = world["pcc"].post(f"applications/{pk}/assign-attorney", {"attorney_user_id": ATTORNEY})
    offer = r.json()["attorney_assignments"][0]["id"]
    r_dec = world["attorney"].post(f"attorney-assignments/{offer}/respond", {"accept": False, "reason": "Conflict"})
    assert r_dec.status_code == 200
    assert r_dec.json()["status"] == "declined"
    assert Application.objects.get(pk=pk).status == sm.PENDING_REVIEW


# TEST-WF-008: BW-PMS-08 Budget approval path
def test_bw_pms_08_budget_approval_path(world, scanner):
    """TEST-WF-008: source_id: BW-PMS-08 main-path"""
    pk = with_attorney(world)
    b = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "7000", "attorney_fee": "25000", "admin_cost": "1500"
    }).json()["id"]
    r = world["director"].post(f"budgets/{b}/decision", {"approve": True})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


# TEST-WF-009: BW-PMS-09 Budget rejection path
def test_bw_pms_09_budget_rejection_path(world, scanner):
    """TEST-WF-009: source_id: BW-PMS-09 main-path"""
    pk = with_attorney(world)
    b = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "8000", "attorney_fee": "30000", "admin_cost": "2000"
    }).json()["id"]
    r = world["director"].post(f"budgets/{b}/decision", {"approve": False})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


# TEST-WF-010: BW-PMS-10 Budget escalation path
def test_bw_pms_10_budget_escalation_path(world, scanner):
    """TEST-WF-010: source_id: BW-PMS-10 main-path"""
    pk = with_attorney(world)
    b = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "150000", "attorney_fee": "0", "admin_cost": "0"
    }).json()["id"]
    r = world["director"].post(f"budgets/{b}/decision", {"approve": True})
    assert r.status_code == 200
    assert r.json()["status"] == "escalated"


# TEST-WF-011: BW-PMS-11 External filing path
def test_bw_pms_11_filing_path(world, scanner):
    """TEST-WF-011: source_id: BW-PMS-11 main-path"""
    pk = filed(world)
    assert Application.objects.get(pk=pk).status == sm.FILED


# TEST-WF-012: BW-PMS-16 Withdrawal transition
def test_bw_pms_16_withdrawal_transition(world, scanner):
    """TEST-WF-012: source_id: BW-PMS-16 main-path"""
    pk = under_review(world)
    r = world["applicant"].post(f"applications/{pk}/withdraw", {"reason": "Withdrawn by applicant"})
    assert r.status_code == 200
    assert r.json()["status"] == sm.WITHDRAWN


# TEST-WF-013: CW-PMS-01 Review and disposition
def test_cw_pms_01_composite_review(world, scanner):
    """TEST-WF-013: source_id: CW-PMS-01 approval-path"""
    pk = under_review(world)
    r = world["director"].post(f"applications/{pk}/review", {"decision": "approve", "justification": JUSTIFY})
    assert r.status_code == 200
    assert r.json()["status"] == sm.APPROVED


# TEST-WF-014: CW-PMS-02 Pre-filing assignment and budget governance
def test_cw_pms_02_composite_prefiling_governance(world, scanner):
    """TEST-WF-014: source_id: CW-PMS-02 parallel-tracks"""
    pk = with_attorney(world)
    b = world["attorney"].post(f"applications/{pk}/budgets", {
        "filing_fee": "5000", "attorney_fee": "15000", "admin_cost": "1000"
    }).json()["id"]
    assert world["director"].post(f"budgets/{b}/decision", {"approve": True}).status_code == 200


# TEST-WF-015: CW-PMS-05 Cross-cutting withdrawal
def test_cw_pms_05_composite_withdrawal():
    """TEST-WF-015: source_id: CW-PMS-05 candidate-statuses"""
    for s in sm.WITHDRAWAL_CANDIDATES:
        assert sm.APPLICATION.is_legal(s, "withdraw")
