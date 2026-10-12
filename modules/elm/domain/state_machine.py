"""The leave-request state machine (CW-EL-01 .. CW-EL-04).

A declarative table of legal moves, so an illegal transition is impossible to
express rather than merely rejected, and "who may do this?" has exactly one
answer per edge. Pure Python: the whole workflow tests with no DB.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from modules.elm.domain import enums as e
from modules.elm.domain.errors import ActorNotAllowed, InvalidTransition


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


def _pending_withdrawals() -> tuple[Transition, ...]:
    """A pending request may be withdrawn before final approval (BR-EL-022)."""
    return tuple(
        Transition(s, e.WITHDRAWN, "elm.leave_request.withdraw",
                   frozenset({e.EMPLOYEE}))
        for s in e.PENDING_APPROVAL
    )


TRANSITIONS: tuple[Transition, ...] = (
    # -- submission (EL-UC-001) --------------------------------------------
    Transition(e.DRAFT, e.AWAITING_SUBSTITUTE, "elm.leave_request.create",
               frozenset({e.EMPLOYEE}), ("substitute_required",)),
    Transition(e.DRAFT, e.AWAITING_UNIT_HEAD, "elm.leave_request.create",
               frozenset({e.EMPLOYEE}), ("no_substitute", "not_director")),
    Transition(e.DRAFT, e.AWAITING_DIRECTOR_SANCTION, "elm.leave_request.create",
               frozenset({e.DIRECTOR}),
               ("no_substitute", "applicant_is_director")),

    # -- substitute response (EL-UC-002) -----------------------------------
    Transition(e.AWAITING_SUBSTITUTE, e.AWAITING_UNIT_HEAD,
               "elm.substitute.respond", frozenset({e.SUBSTITUTE}),
               ("accepted", "not_director")),
    Transition(e.AWAITING_SUBSTITUTE, e.AWAITING_DIRECTOR_SANCTION,
               "elm.substitute.respond", frozenset({e.SUBSTITUTE}),
               ("accepted", "applicant_is_director")),
    Transition(e.AWAITING_SUBSTITUTE, e.APPLICANT_ACTION_REQUIRED,
               "elm.substitute.respond", frozenset({e.SUBSTITUTE}),
               ("declined",)),

    # -- replacement nomination (EL-UC-019) --------------------------------
    Transition(e.APPLICANT_ACTION_REQUIRED, e.AWAITING_SUBSTITUTE,
               "elm.leave_request.create", frozenset({e.EMPLOYEE}),
               ("replacement",)),

    # -- unit head review (EL-UC-003) --------------------------------------
    Transition(e.AWAITING_UNIT_HEAD, e.APPROVED, "elm.leave_request.review",
               frozenset({e.UNIT_HEAD}), ("unit_head_final",)),
    Transition(e.AWAITING_UNIT_HEAD, e.REJECTED, "elm.leave_request.review",
               frozenset({e.UNIT_HEAD}), ("unit_head_final", "has_reason")),
    Transition(e.AWAITING_UNIT_HEAD, e.AWAITING_ESTABLISHMENT,
               "elm.leave_request.review", frozenset({e.UNIT_HEAD}),
               ("higher_sanction", "establishment_required")),
    Transition(e.AWAITING_UNIT_HEAD, e.AWAITING_FINAL_SANCTION,
               "elm.leave_request.review", frozenset({e.UNIT_HEAD}),
               ("higher_sanction", "no_establishment")),

    # -- establishment routing (EL-UC-004) ---------------------------------
    Transition(e.AWAITING_ESTABLISHMENT, e.AWAITING_FINAL_SANCTION,
               "elm.leave_request.establishment", frozenset({e.ESTABLISHMENT})),

    # -- final sanction (EL-UC-005) ----------------------------------------
    Transition(e.AWAITING_FINAL_SANCTION, e.APPROVED,
               "elm.leave_request.sanction", frozenset({e.SANCTION})),
    Transition(e.AWAITING_FINAL_SANCTION, e.REJECTED,
               "elm.leave_request.sanction", frozenset({e.SANCTION}),
               ("has_reason",)),
    Transition(e.AWAITING_DIRECTOR_SANCTION, e.APPROVED,
               "elm.leave_request.sanction", frozenset({e.DIRECTOR})),
    Transition(e.AWAITING_DIRECTOR_SANCTION, e.REJECTED,
               "elm.leave_request.sanction", frozenset({e.DIRECTOR}),
               ("has_reason",)),

    # -- withdrawal (EL-UC-007, BR-EL-022) ---------------------------------
    *_pending_withdrawals(),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, actor_role: str | None = None) -> Transition:
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if actor_role is not None and actor_role not in t.actors:
        raise ActorNotAllowed(actor_role, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    return (frm, to) in _INDEX


def allowed_targets(frm: str, actor_role: str | None = None) -> list[str]:
    return sorted(t.to for t in TRANSITIONS
                  if t.frm == frm
                  and (actor_role is None or actor_role in t.actors))
