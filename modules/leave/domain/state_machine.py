"""The ELM state machine, straight from the authoritative STT.

CW-EL-01..04 and BW-EL-01..17 each carry a State-Transition Table, and those
tables are normative. They are transcribed here once, as declarative data, so:

  * an illegal move is impossible to express rather than merely rejected;
  * "who may do this, and what does it need?" has exactly one answer per row;
  * the branch points the STT expresses as alternative rows (substitute or not,
    Director or not, Establishment configured or not) are resolved from facts
    rather than from `if` chains scattered through the service layer.

`when` names the facts a row needs. The service computes those facts from the
resolved route and submits them to `resolve`, which picks the first row whose
facts hold. Order therefore matters: list the more specific fact set first.

Pure Python — no Django, no DRF, no Celery (CI enforces it).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

# -- Statuses (the "Resulting State" column, verbatim) -------------------------
DRAFT = "draft"

#: CW-EL-01 — new leave.
AWAITING_SUBSTITUTE = "awaiting_substitute_response"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head_review"
AWAITING_ESTABLISHMENT = "awaiting_establishment_routing"
AWAITING_SANCTION = "awaiting_final_sanction_decision"
AWAITING_DIRECTOR_SELF_SANCTION = "awaiting_director_self_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

#: CW-EL-03 — extension of ongoing leave.
AWAITING_EXT_SUBSTITUTE = "awaiting_extension_substitute_response"
EXT_APPLICANT_ACTION_REQUIRED = "extension_applicant_action_required"
AWAITING_EXT_UNIT_HEAD = "awaiting_extension_unit_head_review"
EXT_ESTABLISHMENT = "extension_pending_establishment"
EXT_FINAL = "extension_pending_final_decision"
EXTENDED = "extended"
EXTENSION_REJECTED = "extension_rejected"
EXTENSION_WITHDRAWN = "extension_withdrawn"

#: CW-EL-02 — cancellation of an approved leave.
CANCELLATION_UNIT_HEAD = "cancellation_pending_unit_head_review"
CANCELLATION_ESTABLISHMENT = "cancellation_pending_establishment"
CANCELLATION_FINAL = "cancellation_pending_final_decision"
CANCELLED = "cancelled"
CANCELLATION_REJECTED = "cancellation_rejected"

NEW = "new"
EXTENSION = "extension"
CANCELLATION = "cancellation"
KINDS = (NEW, EXTENSION, CANCELLATION)

TERMINAL: frozenset[str] = frozenset({
    APPROVED, REJECTED, WITHDRAWN,
    EXTENDED, EXTENSION_REJECTED, EXTENSION_WITHDRAWN,
    CANCELLED, CANCELLATION_REJECTED,
})

#: Still actionable, so the SLA sweep and the withdrawal rule can both ask.
PENDING: frozenset[str] = frozenset({
    AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_SANCTION, AWAITING_DIRECTOR_SELF_SANCTION,
    AWAITING_EXT_SUBSTITUTE, EXT_APPLICANT_ACTION_REQUIRED,
    AWAITING_EXT_UNIT_HEAD, EXT_ESTABLISHMENT, EXT_FINAL,
    CANCELLATION_UNIT_HEAD, CANCELLATION_ESTABLISHMENT, CANCELLATION_FINAL,
})

# -- Actions -------------------------------------------------------------------
SUBMIT = "submit"
SEND = "send"                      # an extension or a cancellation request leaves Draft
SUBSTITUTE_ACCEPT = "substitute_accept"
SUBSTITUTE_DECLINE = "substitute_decline"
NOMINATE_REPLACEMENT = "nominate_replacement"
APPROVE = "approve"
REJECT = "reject"
RECOMMEND = "recommend"            # the Unit Head's recommendation
VERIFY = "verify"                  # Establishment verification and routing
WITHDRAW = "withdraw"
APPROVE_CANCELLATION = "approve_cancellation"
REJECT_CANCELLATION = "reject_cancellation"

# -- Actor kinds (the "Actor" column) ------------------------------------------
EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
SANCTION = "sanctioning_authority"
DIRECTOR = "director"
SYSTEM = "system"

#: Permission codes the domain itself states, so authority is declared once.
P_APPLY = "leave.request.create"
P_WITHDRAW = "leave.request.delete"
P_DECIDE = "leave.request.approve"
#: A substitute holds no permission: the assignment is the authority (BR-EL-014).
P_ASSIGNMENT = None


class InvalidTransition(Exception):
    def __init__(self, kind: str, frm: str, action: str):
        super().__init__(
            f"A {kind} request in {frm!r} cannot perform {action!r}.")
        self.kind, self.frm, self.action = kind, frm, action


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, action: str):
        super().__init__(
            f"A {actor_kind} may not perform {action!r} from {frm!r}.")
        self.actor_kind, self.frm, self.action = actor_kind, frm, action


@dataclass(frozen=True)
class Transition:
    kind: str
    frm: str
    action: str
    to: str
    actors: frozenset[str]
    permission: str | None = P_DECIDE
    step_kind: str = ""
    #: Facts that must all hold for this row to be the one taken.
    when: Mapping[str, bool] = field(default_factory=dict)


def _t(kind: str, frm: str, action: str, to: str, actors, *, permission=P_DECIDE,
       step_kind: str = "", when: Mapping[str, bool] | None = None) -> Transition:
    return Transition(kind, frm, action, to, frozenset(actors), permission,
                      step_kind, when or {})


_DECIDERS = (UNIT_HEAD, ESTABLISHMENT, SANCTION, DIRECTOR)

NEW_TRANSITIONS: tuple[Transition, ...] = (
    # BW-EL-02/05/08 M1 — whether consent is needed, and the Director exception.
    _t(NEW, DRAFT, SUBMIT, AWAITING_SUBSTITUTE, (EMPLOYEE,),
       permission=P_APPLY, step_kind="applicant",
       when={"substitute_required": True}),
    _t(NEW, DRAFT, SUBMIT, AWAITING_DIRECTOR_SELF_SANCTION, (EMPLOYEE,),
       permission=P_APPLY, step_kind="applicant",
       when={"substitute_required": False, "applicant_is_director": True}),
    _t(NEW, DRAFT, SUBMIT, AWAITING_UNIT_HEAD, (EMPLOYEE,),
       permission=P_APPLY, step_kind="applicant",
       when={"substitute_required": False, "applicant_is_director": False}),

    # EL-UC-002 — consent releases the gate; the Director still self-sanctions.
    _t(NEW, AWAITING_SUBSTITUTE, SUBSTITUTE_ACCEPT,
       AWAITING_DIRECTOR_SELF_SANCTION, (SUBSTITUTE,), permission=P_ASSIGNMENT,
       step_kind="substitute", when={"applicant_is_director": True}),
    _t(NEW, AWAITING_SUBSTITUTE, SUBSTITUTE_ACCEPT, AWAITING_UNIT_HEAD,
       (SUBSTITUTE,), permission=P_ASSIGNMENT, step_kind="substitute",
       when={"applicant_is_director": False}),
    _t(NEW, AWAITING_SUBSTITUTE, SUBSTITUTE_DECLINE, APPLICANT_ACTION_REQUIRED,
       (SUBSTITUTE,), permission=P_ASSIGNMENT, step_kind="substitute"),
    _t(NEW, APPLICANT_ACTION_REQUIRED, NOMINATE_REPLACEMENT, AWAITING_SUBSTITUTE,
       (EMPLOYEE,), permission=P_APPLY, step_kind="applicant"),

    # EL-UC-003 — Unit Head final for CL/RH, recommendation above that.
    _t(NEW, AWAITING_UNIT_HEAD, APPROVE, APPROVED, (UNIT_HEAD,),
       step_kind="unit_head", when={"unit_head_final": True}),
    _t(NEW, AWAITING_UNIT_HEAD, REJECT, REJECTED, (UNIT_HEAD,),
       step_kind="unit_head", when={"unit_head_final": True}),
    _t(NEW, AWAITING_UNIT_HEAD, RECOMMEND, AWAITING_ESTABLISHMENT, (UNIT_HEAD,),
       step_kind="unit_head", when={"establishment_configured": True}),
    _t(NEW, AWAITING_UNIT_HEAD, RECOMMEND, AWAITING_SANCTION, (UNIT_HEAD,),
       step_kind="unit_head", when={"establishment_configured": False}),

    # EL-UC-004 — Establishment verifies and forwards.
    _t(NEW, AWAITING_ESTABLISHMENT, VERIFY, AWAITING_SANCTION, (ESTABLISHMENT,),
       step_kind="establishment"),

    # EL-UC-005 — the final decision, and the Director's own.
    _t(NEW, AWAITING_SANCTION, APPROVE, APPROVED, (SANCTION,),
       step_kind="sanction"),
    _t(NEW, AWAITING_SANCTION, REJECT, REJECTED, (SANCTION,),
       step_kind="sanction"),
    _t(NEW, AWAITING_DIRECTOR_SELF_SANCTION, APPROVE, APPROVED, (DIRECTOR,),
       step_kind="director"),
    _t(NEW, AWAITING_DIRECTOR_SELF_SANCTION, REJECT, REJECTED, (DIRECTOR,),
       step_kind="director"),

    # EL-UC-007 — withdrawal, cross-cutting over every pending pre-final state.
    *(_t(NEW, s, WITHDRAW, WITHDRAWN, (EMPLOYEE,), permission=P_WITHDRAW,
        step_kind="applicant")
      for s in (AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED,
                AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, AWAITING_SANCTION,
                AWAITING_DIRECTOR_SELF_SANCTION)),
)

EXTENSION_TRANSITIONS: tuple[Transition, ...] = (
    # BW-EL-12/13 M1.
    _t(EXTENSION, DRAFT, SEND, AWAITING_EXT_SUBSTITUTE, (EMPLOYEE,),
       permission=P_APPLY, step_kind="applicant",
       when={"substitute_required": True}),
    _t(EXTENSION, DRAFT, SEND, AWAITING_EXT_UNIT_HEAD, (EMPLOYEE,),
       permission=P_APPLY, step_kind="applicant",
       when={"substitute_required": False}),
    _t(EXTENSION, AWAITING_EXT_SUBSTITUTE, SUBSTITUTE_ACCEPT,
       AWAITING_EXT_UNIT_HEAD, (SUBSTITUTE,), permission=P_ASSIGNMENT,
       step_kind="substitute"),
    _t(EXTENSION, AWAITING_EXT_SUBSTITUTE, SUBSTITUTE_DECLINE,
       EXT_APPLICANT_ACTION_REQUIRED, (SUBSTITUTE,), permission=P_ASSIGNMENT,
       step_kind="substitute"),
    _t(EXTENSION, EXT_APPLICANT_ACTION_REQUIRED, NOMINATE_REPLACEMENT,
       AWAITING_EXT_SUBSTITUTE, (EMPLOYEE,), permission=P_APPLY,
       step_kind="applicant"),

    _t(EXTENSION, AWAITING_EXT_UNIT_HEAD, RECOMMEND, EXT_ESTABLISHMENT,
       (UNIT_HEAD,), step_kind="unit_head",
       when={"establishment_configured": True}),
    _t(EXTENSION, AWAITING_EXT_UNIT_HEAD, RECOMMEND, EXT_FINAL, (UNIT_HEAD,),
       step_kind="unit_head", when={"establishment_configured": False}),
    _t(EXTENSION, EXT_ESTABLISHMENT, VERIFY, EXT_FINAL, (ESTABLISHMENT,),
       step_kind="establishment"),

    # BR-EL-025 — approval posts the incremental period only.
    _t(EXTENSION, EXT_FINAL, APPROVE, EXTENDED, (SANCTION,), step_kind="sanction"),
    _t(EXTENSION, EXT_FINAL, REJECT, EXTENSION_REJECTED, (SANCTION,),
       step_kind="sanction"),

    *(_t(EXTENSION, s, WITHDRAW, EXTENSION_WITHDRAWN, (EMPLOYEE,),
        permission=P_WITHDRAW, step_kind="applicant")
      for s in (AWAITING_EXT_SUBSTITUTE, EXT_APPLICANT_ACTION_REQUIRED,
                AWAITING_EXT_UNIT_HEAD, EXT_ESTABLISHMENT, EXT_FINAL)),
)

CANCELLATION_TRANSITIONS: tuple[Transition, ...] = (
    # CW-EL-02 row 1 — no withdrawal row exists for a cancellation request.
    _t(CANCELLATION, DRAFT, SEND, CANCELLATION_UNIT_HEAD, (EMPLOYEE,),
       permission=P_WITHDRAW, step_kind="applicant"),

    # BR-EL-016 — CL/RH cancellations are decided by the Unit Head.
    _t(CANCELLATION, CANCELLATION_UNIT_HEAD, APPROVE_CANCELLATION, CANCELLED,
       (UNIT_HEAD,), step_kind="unit_head", when={"unit_head_final": True}),
    _t(CANCELLATION, CANCELLATION_UNIT_HEAD, REJECT_CANCELLATION,
       CANCELLATION_REJECTED, (UNIT_HEAD,), step_kind="unit_head",
       when={"unit_head_final": True}),
    _t(CANCELLATION, CANCELLATION_UNIT_HEAD, RECOMMEND,
       CANCELLATION_ESTABLISHMENT, (UNIT_HEAD,), step_kind="unit_head",
       when={"establishment_configured": True}),
    _t(CANCELLATION, CANCELLATION_UNIT_HEAD, RECOMMEND, CANCELLATION_FINAL,
       (UNIT_HEAD,), step_kind="unit_head", when={"establishment_configured": False}),
    _t(CANCELLATION, CANCELLATION_ESTABLISHMENT, VERIFY, CANCELLATION_FINAL,
       (ESTABLISHMENT,), step_kind="establishment"),
    _t(CANCELLATION, CANCELLATION_FINAL, APPROVE_CANCELLATION, CANCELLED,
       (SANCTION,), step_kind="sanction"),
    _t(CANCELLATION, CANCELLATION_FINAL, REJECT_CANCELLATION,
       CANCELLATION_REJECTED, (SANCTION,), step_kind="sanction"),
)

_TRANSITIONS: dict[str, tuple[Transition, ...]] = {
    NEW: NEW_TRANSITIONS,
    EXTENSION: EXTENSION_TRANSITIONS,
    CANCELLATION: CANCELLATION_TRANSITIONS,
}

#: Permission per actor kind, for a caller that needs authority without a row.
STEP_PERMISSIONS: dict[str, str | None] = {
    EMPLOYEE: P_APPLY,
    SUBSTITUTE: P_ASSIGNMENT,
    UNIT_HEAD: P_DECIDE,
    ESTABLISHMENT: P_DECIDE,
    SANCTION: P_DECIDE,
    DIRECTOR: P_DECIDE,
    SYSTEM: None,
}


def is_pending(status: str) -> bool:
    return status in PENDING


def is_terminal(status: str) -> bool:
    return status in TERMINAL


def resolve(kind: str, frm: str, action: str, actor_kind: str | None = None, *,
            facts: Mapping[str, bool] | None = None) -> Transition:
    """The single lookup every write goes through.

    Rows are tried in declaration order and the first one whose `when` facts
    all hold wins, so the more specific branch must be declared first.
    """
    given = dict(facts or {})
    candidates = [t for t in _TRANSITIONS.get(kind, ())
                  if t.frm == frm and t.action == action]
    if not candidates:
        raise InvalidTransition(kind, frm, action)

    matched = [t for t in candidates
               if all(given.get(k) is v for k, v in t.when.items())]
    if not matched:
        # Every branch from here needs a fact the caller did not supply, which
        # is a wiring bug rather than a policy refusal.
        raise InvalidTransition(kind, frm, action)

    t = matched[0]
    if actor_kind is not None and actor_kind not in t.actors:
        raise ActorNotAllowed(actor_kind, frm, action)
    return t


def is_legal(kind: str, frm: str, action: str) -> bool:
    return any(t.frm == frm and t.action == action for t in _TRANSITIONS.get(kind, ()))


def allowed_actions(kind: str, frm: str,
                    actor_kind: str | None = None) -> list[str]:
    return sorted({
        t.action for t in _TRANSITIONS.get(kind, ())
        if t.frm == frm and (actor_kind is None or actor_kind in t.actors)
    })
