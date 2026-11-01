from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


class IllegalTransition(ValueError):
    pass


class GuardFailed(ValueError):
    pass


@dataclass(frozen=True)
class Transition:
    from_states: tuple
    action: str
    actors: tuple
    guard: Callable | None
    to_state: str | Callable
    brs: tuple = ()


class Machine:
    def __init__(self, name: str, transitions: tuple[Transition, ...]):
        self.name = name
        self.transitions = transitions


def apply_transition(machine, state, action, actor_role, ctx):
    matches = [
        row
        for row in machine.transitions
        if state in row.from_states and row.action == action and actor_role in row.actors
    ]
    if not matches:
        raise IllegalTransition(state, action, actor_role)
    row = matches[0]
    if row.guard:
        row.guard(ctx)
    return row.to_state(ctx) if callable(row.to_state) else row.to_state
