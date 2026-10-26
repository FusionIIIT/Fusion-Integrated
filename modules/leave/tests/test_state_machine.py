from itertools import product

import pytest

from modules.leave.domain.state_machine import InvalidTransition, can_transition, next_status

# Constants
LEGAL = [
    ("draft", "submit_with_substitute", "employee", "awaiting_substitute"),
    ("draft", "submit_without_substitute", "employee", "awaiting_unit_head"),
    ("awaiting_substitute", "substitute_accept", "substitute", "awaiting_unit_head"),
    ("awaiting_substitute", "substitute_decline", "substitute", "applicant_action_required"),
    ("awaiting_unit_head", "unit_head_approve", "unit_head", "approved"),
    ("awaiting_unit_head", "unit_head_reject", "unit_head", "rejected"),
    ("awaiting_unit_head", "unit_head_recommend", "unit_head", "awaiting_final_sanction"),
    ("awaiting_final_sanction", "sanction_approve", "sanctioning_authority", "approved"),
    ("awaiting_final_sanction", "sanction_reject", "sanctioning_authority", "rejected"),
    ("awaiting_substitute", "withdraw", "employee", "withdrawn"),
    ("applicant_action_required", "withdraw", "employee", "withdrawn"),
    ("awaiting_unit_head", "withdraw", "employee", "withdrawn"),
    ("awaiting_final_sanction", "withdraw", "employee", "withdrawn")
]

STATUSES = ["draft", "awaiting_substitute", "applicant_action_required", "awaiting_unit_head", "awaiting_final_sanction", "approved", "rejected", "withdrawn"]
EVENTS = ["submit_with_substitute", "submit_without_substitute", "substitute_accept", "substitute_decline", "unit_head_approve", "unit_head_reject", "unit_head_recommend", "sanction_approve", "sanction_reject", "withdraw"]
ACTORS = ["employee", "substitute", "unit_head", "sanctioning_authority"]

LEGAL_TRIPLES = {(s, e, a) for s, e, a, _ in LEGAL}
ILLEGAL = [c for c in product(STATUSES, EVENTS, ACTORS) if c not in LEGAL_TRIPLES]

# Parametrized test for all ten legal transitions
@pytest.mark.parametrize("current_status,event,actor,next_expected", LEGAL)
def test_legal_transitions(current_status, event, actor, next_expected):
    assert can_transition(current_status, event, actor)
    assert next_status(current_status, event, actor) == next_expected

# Parametrized test for all illegal transitions
@pytest.mark.parametrize("current_status,event,actor", ILLEGAL)
def test_illegal_transitions(current_status, event, actor):
    assert not can_transition(current_status, event, actor)
    with pytest.raises(InvalidTransition):
        next_status(current_status, event, actor)

# Test that approved, rejected and withdrawn have no legal events
@pytest.mark.parametrize("current_status", ["approved", "rejected", "withdrawn"])
def test_no_legal_events(current_status):
    for event in EVENTS:
        assert not can_transition(current_status, event, "employee")

# Test that an employee cannot do unit_head_approve and a unit_head cannot do withdraw
@pytest.mark.parametrize("actor,event", [("employee", "unit_head_approve"), ("unit_head", "withdraw")])
def test_invalid_actor_events(actor, event):
    for current_status in STATUSES:
        assert not can_transition(current_status, event, actor)
