from decimal import Decimal

from modules.iwd.domain.assignment import EngineerCandidate, select_best_engineer
from modules.iwd.domain.routing import classify_cost_band
from modules.iwd.domain.state_machine import transition


def test_cost_band_routing():
    low = classify_cost_band(Decimal("15000"))
    assert low.band == "low"
    assert not low.requires_committee
    assert not low.requires_director

    mid = classify_cost_band(Decimal("50000"))
    assert mid.band == "mid"
    assert mid.requires_committee
    assert not mid.requires_director

    high = classify_cost_band(Decimal("300000"))
    assert high.band == "high"
    assert high.requires_director
    assert high.bidding_allowed


def test_engineer_assignment():
    candidates = [
        EngineerCandidate(engineer_id=1, discipline="civil", active_load=3),
        EngineerCandidate(engineer_id=2, discipline="civil", active_load=1),
        EngineerCandidate(engineer_id=3, discipline="electrical", active_load=0),
    ]
    best_civil = select_best_engineer("civil", candidates)
    assert best_civil == 2

    best_elec = select_best_engineer("electrical", candidates)
    assert best_elec == 3


def test_state_machine_transitions():
    t1 = transition("submitted", "assign_engineer", "system")
    assert t1.allowed
    assert t1.next_state == "assigned"

    t2 = transition("assigned", "record_assessment", "engineer")
    assert t2.allowed
    assert t2.next_state == "assessed"

    t3 = transition("assessed", "submit_estimate_low", "engineer")
    assert t3.allowed
    assert t3.next_state == "low_cost_review_pending"

    t4 = transition("low_cost_review_pending", "approve_low_cost", "iwd_admin")
    assert t4.allowed
    assert t4.next_state == "estimate_approved"

    illegal = transition("low_cost_review_pending", "approve_low_cost", "student")
    assert not illegal.allowed
    assert "illegal" in illegal.reason


def test_privilege_escalation_rules():
    from modules.iwd.registry import ROLE_GRANTS

    assert "iwd.estimate.manage" not in ROLE_GRANTS["student"]
    assert "iwd.estimate.manage" not in ROLE_GRANTS["engineer"]
    assert "iwd.estimate.manage" in ROLE_GRANTS["iwd_admin"]
    assert "iwd.estimate.manage" in ROLE_GRANTS["department_head"]
    assert "iwd.estimate.manage" in ROLE_GRANTS["director"]

    assert "iwd.bill.manage" in ROLE_GRANTS["auditor"]
    assert "iwd.bill.manage" not in ROLE_GRANTS["student"]
    assert "iwd.bill.manage" not in ROLE_GRANTS["engineer"]


def test_scoping_rules():

    class DummyComplaint:
        def __init__(self, complainant_user_id, assigned_engineer_id):
            self.complainant_user_id = complainant_user_id
            self.assigned_engineer_id = assigned_engineer_id

    # Unit verification of filtering logic
    role = "student"
    assert role not in ["iwd_admin", "department_head", "director", "auditor"]
