"""Pure transition rules for the leave substitute workflow."""

from dataclasses import dataclass

from .states import LeaveWorkflowState as State


@dataclass(frozen=True)
class LeaveWorkflowTransition:
    """A legal state change, optionally restricted to an actor."""

    source: State
    target: State
    actor: str | None = None

    def allows(self, current_state: State, actor: str | None = None) -> bool:
        """Return whether this transition applies in the given context."""
        return (
            current_state == self.source
            and (self.actor is None or actor == self.actor)
        )


TRANSITIONS = (
    LeaveWorkflowTransition(State.APPROVED, State.SUBSTITUTE_DECLINED),
    LeaveWorkflowTransition(State.SUBSTITUTE_DECLINED, State.SUBSTITUTE_ACCEPTED),
    LeaveWorkflowTransition(State.SUBSTITUTE_ACCEPTED, State.END),
)


def resolve_transition(current_state: State, target_state: State) -> LeaveWorkflowTransition:
    """Return the declared transition or raise ``ValueError`` if it is illegal."""
    for transition in TRANSITIONS:
        if transition.source == current_state and transition.target == target_state:
            return transition
    raise ValueError(f"Illegal leave workflow transition: {current_state} -> {target_state}")
