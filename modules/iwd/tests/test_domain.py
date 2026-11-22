from decimal import Decimal
import pytest
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
    # For civil, engineer 2 has lowest load (1 < 3)
    best_civil = select_best_engineer("civil", candidates)
    assert best_civil == 2

    # For electrical, engineer 3 matches
    best_elec = select_best_engineer("electrical", candidates)
    assert best_elec == 3


def test_state_machine_transitions():
    # Valid low-cost path
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

    # Illegal transition rejected
    illegal = transition("low_cost_review_pending", "approve_low_cost", "student")
    assert not illegal.allowed
    assert "illegal" in illegal.reason
