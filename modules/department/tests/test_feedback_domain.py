import pytest

from modules.department.domain.feedback import TRANSITIONS, IllegalTransition, next_state


def test_transitions_keys():
    """
    Test that each key in TRANSITIONS has a corresponding value.
    """
    for key in TRANSITIONS:
        assert isinstance(TRANSITIONS[key], str)

def test_next_state_illegal_transition_dept_admin():
    """
    Test that 'new' with 'resolve' by 'dept_admin' raises IllegalTransition.
    """
    with pytest.raises(IllegalTransition):
        next_state("new", "resolve", "dept_admin")

def test_next_state_illegal_transition_hod():
    """
    Test that 'new' with 'review' by 'hod' raises IllegalTransition.
    """
    with pytest.raises(IllegalTransition):
        next_state("new", "review", "hod")

def test_next_state_illegal_transition_hod_close():
    """
    Test that 'resolved' with 'close' by 'hod' raises IllegalTransition.
    """
    # Assuming 'resolved' is a state that might be reached, and we test an invalid transition from it.
    # Based on TRANSITIONS, 'resolved' is a target state, not a source state for the tested invalid transition.
    # We test a transition from 'resolved' that is not defined.
    with pytest.raises(IllegalTransition):
        next_state("resolved", "close", "hod")
