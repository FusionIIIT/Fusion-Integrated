"""Pure-Python declarative state machines for Gymkhana.

Adheres strictly to .importlinter contract: domain-is-pure-python.
NO imports of django, rest_framework, or celery.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.gymkhana.domain.exceptions import (
    ActorNotAllowed,
    GuardFailed,
    InvalidTransition,
)


@dataclass(frozen=True)
class Transition:
    frm: str | None
    to: str
    event: str
    allowed_actors: frozenset[str]
    required_permission: str = ""
    guard_name: str = ""


class ClubEstablishmentStateMachine:
    """BW-GYM-03: Student Admin Club Establishment and Confirmation Lifecycle.

    Transitions:
      (None, 'create') -> 'open'
      ('open', 'approve') -> 'confirmed'
    Terminal state: 'confirmed'
    No rejection transition exists in baseline (BR-GYM-004).
    """

    NAME = "ClubEstablishment"
    STATE_OPEN = "open"
    STATE_CONFIRMED = "confirmed"
    TERMINAL = frozenset({STATE_CONFIRMED})

    TRANSITIONS = (
        Transition(
            frm=None,
            to="open",
            event="create",
            allowed_actors=frozenset({"student_admin"}),
            required_permission="gymkhana.club.create",
        ),
        Transition(
            frm="open",
            to="confirmed",
            event="approve",
            allowed_actors=frozenset({"student_admin"}),
            required_permission="gymkhana.club.approve",
        ),
    )

    @classmethod
    def transition(cls, current_state: str | None, event: str, actor: str) -> str:
        for t in cls.TRANSITIONS:
            if t.frm == current_state and t.event == event:
                if actor not in t.allowed_actors:
                    raise ActorNotAllowed(cls.NAME, actor, event)
                return t.to
        raise InvalidTransition(cls.NAME, current_state, event)

    @classmethod
    def can_transition(cls, current_state: str | None, event: str, actor: str) -> bool:
        for t in cls.TRANSITIONS:
            if t.frm == current_state and t.event == event and actor in t.allowed_actors:
                return True
        return False


class ClubMembershipStateMachine:
    """BW-GYM-01: Club Membership Enrollment Lifecycle.

    Transitions:
      (None, 'apply') -> 'open' (Guard: club must be confirmed, BR-GYM-007)
      ('open', 'approve') -> 'confirmed' (Guard: actor is Club Head, BR-GYM-010)
    Terminal state: 'confirmed'
    No rejection transition exists in baseline (BR-GYM-011).
    """

    NAME = "ClubMembership"
    STATE_OPEN = "open"
    STATE_CONFIRMED = "confirmed"
    TERMINAL = frozenset({STATE_CONFIRMED})

    TRANSITIONS = (
        Transition(
            frm=None,
            to="open",
            event="apply",
            allowed_actors=frozenset({"student"}),
            required_permission="gymkhana.membership.create",
            guard_name="club_is_confirmed",
        ),
        Transition(
            frm="open",
            to="confirmed",
            event="approve",
            allowed_actors=frozenset({"club_head"}),
            required_permission="gymkhana.membership.approve",
            guard_name="actor_is_club_head",
        ),
    )

    @classmethod
    def transition(
        cls,
        current_state: str | None,
        event: str,
        actor: str,
        *,
        guards: dict[str, bool] | None = None,
    ) -> str:
        guards = guards or {}
        for t in cls.TRANSITIONS:
            if t.frm == current_state and t.event == event:
                if actor not in t.allowed_actors:
                    raise ActorNotAllowed(cls.NAME, actor, event)
                if t.guard_name and not guards.get(t.guard_name, False):
                    raise GuardFailed(t.guard_name)
                return t.to
        raise InvalidTransition(cls.NAME, current_state, event)


class PollStateMachine:
    """BW-GYM-02: Targeted Poll Lifecycle.

    Transitions:
      (None, 'create') -> 'active'
      ('active', 'vote') -> 'active'
      ('active', 'expire') -> 'expired'
    Terminal state: 'expired'
    """

    NAME = "Poll"
    STATE_ACTIVE = "active"
    STATE_EXPIRED = "expired"
    TERMINAL = frozenset({STATE_EXPIRED})

    TRANSITIONS = (
        Transition(
            frm=None,
            to="active",
            event="create",
            allowed_actors=frozenset({"club_head"}),
            required_permission="gymkhana.poll.create",
        ),
        Transition(
            frm="active",
            to="active",
            event="vote",
            allowed_actors=frozenset({"student"}),
            required_permission="gymkhana.poll.update",
            guard_name="is_unexpired",
        ),
        Transition(
            frm="active",
            to="expired",
            event="expire",
            allowed_actors=frozenset({"system"}),
        ),
    )

    @classmethod
    def transition(
        cls,
        current_state: str | None,
        event: str,
        actor: str,
        *,
        guards: dict[str, bool] | None = None,
    ) -> str:
        guards = guards or {}
        for t in cls.TRANSITIONS:
            if t.frm == current_state and t.event == event:
                if actor not in t.allowed_actors:
                    raise ActorNotAllowed(cls.NAME, actor, event)
                if t.guard_name and not guards.get(t.guard_name, False):
                    raise GuardFailed(t.guard_name)
                return t.to
        raise InvalidTransition(cls.NAME, current_state, event)
