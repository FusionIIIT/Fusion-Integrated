import pytest

from modules.cms import domain


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("submitted", "resolved"),
        ("submitted", "rejected"),
        ("in_progress", "resolved"),
        ("in_progress", "rejected"),
        ("resolved", "closed"),
        ("closed", "submitted"),
        ("closed", "in_progress"),
    ],
)
def test_supported_state_transitions(source, target):
    assert domain.transition(source, target) == domain.Transition(source, target)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("submitted", "in_progress"),
        ("submitted", "closed"),
        ("rejected", "closed"),
        ("closed", "resolved"),
    ],
)
def test_undefined_state_transitions_are_rejected(source, target):
    with pytest.raises(domain.InvalidTransition):
        domain.transition(source, target)


def test_unresolved_states_match_the_sla_scope():
    assert domain.is_unresolved("submitted")
    assert domain.is_unresolved("in_progress")
    assert not domain.is_unresolved("resolved")
    assert not domain.is_unresolved("rejected")
    assert not domain.is_unresolved("closed")
