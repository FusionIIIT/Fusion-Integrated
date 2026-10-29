"""Pure Python tests for the leave workflow."""

import pytest

from modules.leave_elm.domain.states import LeaveWorkflowState as State
from modules.leave_elm.domain.transitions import TRANSITIONS, resolve_transition
from modules.leave_elm.domain.validation import is_valid_transition, validate_transition


def test_declared_flow_has_three_steps_in_order():
    assert [(step.source, step.target) for step in TRANSITIONS] == [
        (State.APPROVED, State.SUBSTITUTE_DECLINED),
        (State.SUBSTITUTE_DECLINED, State.SUBSTITUTE_ACCEPTED),
        (State.SUBSTITUTE_ACCEPTED, State.END),
    ]


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (State.APPROVED, State.SUBSTITUTE_DECLINED),
        (State.SUBSTITUTE_DECLINED, State.SUBSTITUTE_ACCEPTED),
        (State.SUBSTITUTE_ACCEPTED, State.END),
    ],
)
def test_valid_steps_resolve_and_validate(source, target):
    assert is_valid_transition(source, target)
    assert resolve_transition(source, target).source == source
    validate_transition(source, target)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (State.APPROVED, State.SUBSTITUTE_ACCEPTED),
        (State.SUBSTITUTE_DECLINED, State.END),
        (State.END, State.APPROVED),
    ],
)
def test_skipped_or_reversed_steps_are_rejected(source, target):
    assert not is_valid_transition(source, target)
    with pytest.raises(ValueError):
        resolve_transition(source, target)
    with pytest.raises(ValueError):
        validate_transition(source, target)
