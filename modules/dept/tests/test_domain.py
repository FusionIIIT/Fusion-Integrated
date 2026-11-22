import pytest

from modules.dept.domain import InvalidTransition, has_overlap, transition


def test_stock_state_machine_rejects_wrong_actor_and_terminal_transition():
    assert transition("pending", "approve", "HOD") == "approved"
    assert transition("approved", "issue", "Dept_Admin") == "issued"
    with pytest.raises(InvalidTransition):
        transition("pending", "issue", "Dept_Admin")
    with pytest.raises(InvalidTransition):
        transition("issued", "approve", "HOD")


def test_feedback_requires_initial_review_before_hod_resolution():
    assert transition("new", "review", "Dept_Admin") == "under_review"
    assert transition("under_review", "resolve", "HOD") == "resolved"
    with pytest.raises(InvalidTransition):
        transition("new", "resolve", "HOD")


def test_half_open_timetable_intervals_allow_touching_edges():
    assert has_overlap(9, 10, 9.5, 11)
    assert not has_overlap(9, 10, 10, 11)
