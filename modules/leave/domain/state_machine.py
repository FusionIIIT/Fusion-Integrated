"""The request state machine: CW-EL-01 (new), CW-EL-02 (cancellation), CW-EL-03 (extension)."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

NEW, CANCELLATION, EXTENSION = "new", "cancellation", "extension"
KINDS = (NEW, CANCELLATION, EXTENSION)

DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
APPLICANT_ACTION = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_ESTABLISHMENT = "awaiting_establishment"
AWAITING_SANCTION = "awaiting_sanction"
AWAITING_DIRECTOR = "awaiting_director"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
#: Only a new leave reaches this, by its cancellation being approved (BR-EL-023).
CANCELLED = "cancelled"

PENDING = frozenset({AWAITING_SUBSTITUTE, APPLICANT_ACTION, AWAITING_UNIT_HEAD,
                     AWAITING_ESTABLISHMENT, AWAITING_SANCTION, AWAITING_DIRECTOR})
TERMINAL = frozenset({APPROVED, REJECTED, WITHDRAWN, CANCELLED})

SUBMIT = "submit"
SUBSTITUTE_ACCEPT = "substitute_accept"
SUBSTITUTE_DECLINE = "substitute_decline"
RENOMINATE = "renominate"
UNIT_HEAD_APPROVE = "unit_head_approve"
UNIT_HEAD_REJECT = "unit_head_reject"
UNIT_HEAD_RECOMMEND = "unit_head_recommend"
ESTABLISHMENT_FORWARD = "establishment_forward"
SANCTION_APPROVE = "sanction_approve"
SANCTION_REJECT = "sanction_reject"
WITHDRAW = "withdraw"
LAPSE = "lapse"

EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
AUTHORITY = "authority"
DIRECTOR = "director"
SYSTEM = "system"

#: The facts a guard may read, all known before the move is made.
FLAGS = ("needs_substitute", "director", "uh_final", "establishment")

#: Which actor's task each waiting state is.
STEP_OF_STATE = {
    AWAITING_SUBSTITUTE: SUBSTITUTE,
    AWAITING_UNIT_HEAD: UNIT_HEAD,
    AWAITING_ESTABLISHMENT: ESTABLISHMENT,
    AWAITING_SANCTION: AUTHORITY,
    AWAITING_DIRECTOR: DIRECTOR,
}


class InvalidTransition(Exception):
    def __init__(self, kind: str, frm: str, event: str, actor: str):
        super().__init__(f"A {kind} request in {frm!r} has no {event!r} move for {actor!r}.")
        self.kind, self.frm, self.event, self.actor = kind, frm, event, actor


@dataclass(frozen=True)
class Transition:
    kind: str
    frm: str
    event: str
    actor: str
    to: str
    when: tuple[tuple[str, bool], ...] = ()
    rows: str = ""

    def matches(self, flags: Mapping[str, bool]) -> bool:
        return all(bool(flags.get(name, False)) is want for name, want in self.when)


def _t(kind, frm, event, actor, to, rows="", **when) -> Transition:
    return Transition(kind, frm, event, actor, to, tuple(sorted(when.items())), rows)


def _decisions(kind: str, rows: str) -> list[Transition]:
    """The Unit Head, Establishment and final-authority rows (BR-EL-016 to 020)."""
    return [
        _t(kind, AWAITING_UNIT_HEAD, UNIT_HEAD_RECOMMEND, UNIT_HEAD, AWAITING_ESTABLISHMENT,
           rows, uh_final=False, establishment=True),
        _t(kind, AWAITING_UNIT_HEAD, UNIT_HEAD_RECOMMEND, UNIT_HEAD, AWAITING_SANCTION,
           rows, uh_final=False, establishment=False),
        _t(kind, AWAITING_ESTABLISHMENT, ESTABLISHMENT_FORWARD, ESTABLISHMENT,
           AWAITING_SANCTION, rows),
        _t(kind, AWAITING_SANCTION, SANCTION_APPROVE, AUTHORITY, APPROVED, rows),
        _t(kind, AWAITING_SANCTION, SANCTION_REJECT, AUTHORITY, REJECTED, rows),
        _t(kind, AWAITING_DIRECTOR, SANCTION_APPROVE, DIRECTOR, APPROVED, rows),
        _t(kind, AWAITING_DIRECTOR, SANCTION_REJECT, DIRECTOR, REJECTED, rows),
    ]


def _consent(kind: str, rows: str) -> list[Transition]:
    """BR-EL-015: the substitute gate and the decline loop."""
    return [
        _t(kind, AWAITING_SUBSTITUTE, SUBSTITUTE_ACCEPT, SUBSTITUTE, AWAITING_DIRECTOR,
           rows, director=True),
        _t(kind, AWAITING_SUBSTITUTE, SUBSTITUTE_ACCEPT, SUBSTITUTE, AWAITING_UNIT_HEAD,
           rows, director=False),
        _t(kind, AWAITING_SUBSTITUTE, SUBSTITUTE_DECLINE, SUBSTITUTE, APPLICANT_ACTION, rows),
        _t(kind, APPLICANT_ACTION, RENOMINATE, EMPLOYEE, AWAITING_SUBSTITUTE, rows),
    ]


def _submission(kind: str, rows: str, *, consent: bool) -> list[Transition]:
    out = [
        _t(kind, DRAFT, SUBMIT, EMPLOYEE, AWAITING_DIRECTOR, rows,
           **({"needs_substitute": False} if consent else {}), director=True),
        _t(kind, DRAFT, SUBMIT, EMPLOYEE, AWAITING_UNIT_HEAD, rows,
           **({"needs_substitute": False} if consent else {}), director=False),
    ]
    if consent:
        out.append(_t(kind, DRAFT, SUBMIT, EMPLOYEE, AWAITING_SUBSTITUTE, rows,
                      needs_substitute=True))
    return out


def _withdrawals(kind: str, rows: str, states) -> list[Transition]:
    return [_t(kind, s, WITHDRAW, EMPLOYEE, WITHDRAWN, rows) for s in sorted(states)]


TRANSITIONS: tuple[Transition, ...] = (
    *_submission(NEW, "CW-EL-01 1-3", consent=True),
    *_consent(NEW, "CW-EL-01 4-7"),
    _t(NEW, AWAITING_UNIT_HEAD, UNIT_HEAD_APPROVE, UNIT_HEAD, APPROVED, "CW-EL-01 8",
       uh_final=True),
    _t(NEW, AWAITING_UNIT_HEAD, UNIT_HEAD_REJECT, UNIT_HEAD, REJECTED, "CW-EL-01 9",
       uh_final=True),
    *_decisions(NEW, "CW-EL-01 10-16"),
    *_withdrawals(NEW, "CW-EL-01 17", PENDING),

    *_submission(CANCELLATION, "CW-EL-02 1", consent=False),
    _t(CANCELLATION, AWAITING_UNIT_HEAD, UNIT_HEAD_APPROVE, UNIT_HEAD, APPROVED,
       "CW-EL-02 2", uh_final=True),
    _t(CANCELLATION, AWAITING_UNIT_HEAD, UNIT_HEAD_REJECT, UNIT_HEAD, REJECTED,
       "CW-EL-02 3", uh_final=True),
    *_decisions(CANCELLATION, "CW-EL-02 4-8"),
    #: BR-EL-023: once the leave begins the cancellation can never be approved; it lapses.
    *[_t(CANCELLATION, s, LAPSE, SYSTEM, WITHDRAWN, "BR-EL-023")
      for s in (AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, AWAITING_SANCTION, AWAITING_DIRECTOR)],

    *_submission(EXTENSION, "CW-EL-03 1-2", consent=True),
    *_consent(EXTENSION, "CW-EL-03 3-5"),
    *_decisions(EXTENSION, "CW-EL-03 6-10"),
    *_withdrawals(EXTENSION, "CW-EL-03 11", PENDING),
)


def candidates(kind: str, frm: str, event: str, actor: str) -> list[Transition]:
    return [t for t in TRANSITIONS
            if t.kind == kind and t.frm == frm and t.event == event and t.actor == actor]


def resolve(kind: str, frm: str, event: str, actor: str,
            flags: Mapping[str, bool] | None = None) -> Transition:
    """The single lookup every move goes through; exactly one row may match."""
    flags = flags or {}
    unknown = set(flags) - set(FLAGS)
    if unknown:
        raise ValueError(f"Unknown guard flag(s): {sorted(unknown)}")
    matching = [t for t in candidates(kind, frm, event, actor) if t.matches(flags)]
    if len(matching) != 1:
        raise InvalidTransition(kind, frm, event, actor)
    return matching[0]


def events_from(kind: str, frm: str, actor: str | None = None) -> list[str]:
    return sorted({t.event for t in TRANSITIONS
                   if t.kind == kind and t.frm == frm and (actor is None or t.actor == actor)})
