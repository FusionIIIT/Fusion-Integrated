"""Convocation Award Lifecycle state machine (CW-SPACS-03, BW-SPACS-08, 09, 11).

Pure Python — no Django, DRF or Celery.
"""
from __future__ import annotations

from dataclasses import dataclass, field

OPEN = "open"
POOL_PREPARED = "pool_prepared"
UNDER_EVALUATION = "under_evaluation"
RESULT_RECORDED = "result_recorded"
AWAITING_APPROVAL = "awaiting_approval"
READY_FOR_PUBLICATION = "ready_for_publication"
PUBLISHED = "published"

ALL_AWARD_STATES = frozenset({
    OPEN,
    POOL_PREPARED,
    UNDER_EVALUATION,
    RESULT_RECORDED,
    AWAITING_APPROVAL,
    READY_FOR_PUBLICATION,
    PUBLISHED,
})

TERMINAL_AWARD = frozenset({PUBLISHED})

CONVENER = "spacs_convener"
COMMITTEE = "award_committee"
SYSTEM = "system"


class InvalidAwardTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move award cycle from {frm!r} to {to!r}.")
        self.frm = frm
        self.to = to


class AwardActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(f"A {actor_kind} may not move award cycle from {frm!r} to {to!r}.")
        self.actor_kind = actor_kind
        self.frm = frm
        self.to = to


class AwardGuardFailed(Exception):
    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard {guard!r} failed.")
        self.guard = guard


@dataclass(frozen=True)
class AwardTransition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


AWARD_TRANSITIONS: tuple[AwardTransition, ...] = (
    # Convener prepares candidate pool (BW-SPACS-08)
    AwardTransition(
        OPEN,
        POOL_PREPARED,
        "spacs.award.manage",
        frozenset({CONVENER}),
        ("has_candidates",),
    ),
    # Committee evaluation begins
    AwardTransition(
        POOL_PREPARED,
        UNDER_EVALUATION,
        "spacs.award.review",
        frozenset({COMMITTEE, CONVENER}),
        (),
    ),
    # Committee records evaluations and recommendations
    AwardTransition(
        UNDER_EVALUATION,
        RESULT_RECORDED,
        "spacs.award.review",
        frozenset({COMMITTEE, CONVENER}),
        ("has_results",),
    ),
    # Finalization path when approval evidence is already available (BW-SPACS-09)
    AwardTransition(
        RESULT_RECORDED,
        READY_FOR_PUBLICATION,
        "spacs.award.approve",
        frozenset({CONVENER}),
        ("has_approval",),
    ),
    # Finalization path when approval evidence is still pending (BW-SPACS-11)
    AwardTransition(
        RESULT_RECORDED,
        AWAITING_APPROVAL,
        "spacs.award.approve",
        frozenset({CONVENER}),
        (),
    ),
    # Later recording of approval evidence (BW-SPACS-11)
    AwardTransition(
        AWAITING_APPROVAL,
        READY_FOR_PUBLICATION,
        "spacs.award.approve",
        frozenset({CONVENER}),
        ("has_approval",),
    ),
    # Publishing approved results (BW-SPACS-09, BW-SPACS-11, BR-SPACS-019)
    AwardTransition(
        READY_FOR_PUBLICATION,
        PUBLISHED,
        "spacs.award.publish",
        frozenset({CONVENER}),
        (),
    ),
)


def is_legal_award_transition(frm: str, to: str, actor_kind: str | None = None) -> bool:
    for t in AWARD_TRANSITIONS:
        if t.frm == frm and t.to == to:
            if actor_kind is None or actor_kind in t.actors:
                return True
    return False


def resolve_award_transition(frm: str, to: str, actor_kind: str | None = None) -> AwardTransition:
    matching = [t for t in AWARD_TRANSITIONS if t.frm == frm and t.to == to]
    if not matching:
        raise InvalidAwardTransition(frm, to)
    if actor_kind is not None:
        allowed = [t for t in matching if actor_kind in t.actors]
        if not allowed:
            raise AwardActorNotAllowed(actor_kind, frm, to)
        return allowed[0]
    return matching[0]


def allowed_award_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    targets = []
    for t in AWARD_TRANSITIONS:
        if t.frm == frm:
            if actor_kind is None or actor_kind in t.actors:
                if t.to not in targets:
                    targets.append(t.to)
    return targets
