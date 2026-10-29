"""The leave state machine, from the authoritative State-Transition Tables.

Workflow Specifications v1.6 carries one STT per Basis and Composite Workflow;
this module is their union. A declarative table of legal moves, so an illegal
transition is impossible to express rather than merely rejected, and every edge
names the one actor role and the one permission that may perform it.

Citations are the v1.6 STT rows. v1.6 supersedes the v1.5 decomposition, whose
basis-workflow ids meant different things; see the blueprint's open questions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# -- actor roles, from Problem Statement Appendix A (ACT-01..08, EVT-01/02) -----
EMPLOYEE = "employee"                        # ACT-01
SUBSTITUTE = "substitute"                    # ACT-02
UNIT_HEAD = "unit_head"                      # ACT-03
ESTABLISHMENT = "establishment"              # ACT-04
SANCTIONING_AUTHORITY = "sanctioning_authority"  # ACT-05/06
DIRECTOR = "director"                        # ACT-07
LEAVE_ADMIN = "leave_administrator"          # ACT-08
SYSTEM = "system"                            # EVT-01/02, never a UC actor

# -- permission codes, declared once in registry.py ---------------------------
P_VIEW_SELF = "leave.request.view_self"
P_CREATE = "leave.request.create"
P_WITHDRAW = "leave.request.delete"
P_VIEW = "leave.request.view"
P_APPROVE = "leave.request.approve"
P_SUBSTITUTE = "leave.substitute.respond"
P_RECORDS = "leave.record.maintain"
P_BALANCE = "leave.balance.update"
P_YEAR_END = "leave.year_end.process"
P_SLA_ESCALATE = "leave.sla.escalate"

# -- workflow identity --------------------------------------------------------
NEW_LEAVE = "CW-EL-01"
CANCELLATION = "CW-EL-02"
EXTENSION = "CW-EL-03"
RESUMPTION = "CW-EL-04"

# -- LeaveRequest states (CW-EL-01 STT rows 1-17) -----------------------------
DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute_response"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head_review"
AWAITING_ESTABLISHMENT = "awaiting_establishment_routing"
AWAITING_FINAL_DECISION = "awaiting_final_sanction_decision"
AWAITING_DIRECTOR = "awaiting_director_self_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
#: Not a CW-EL-01 row: the parent leave's state after an approved cancellation.
CANCELLED = "cancelled"

LEAVE_STATES: tuple[str, ...] = (
    DRAFT, AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL_DECISION, AWAITING_DIRECTOR,
    APPROVED, REJECTED, WITHDRAWN, CANCELLED,
)

TERMINAL: frozenset[str] = frozenset({REJECTED, WITHDRAWN, CANCELLED})

#: Pending means a task is outstanding somewhere, so SLA clocks run (BR-EL-032).
PENDING: frozenset[str] = frozenset({
    AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL_DECISION, AWAITING_DIRECTOR,
})

#: States in which a leave is still live and must not overlap another: everything
#: pending plus approved-and-not-returned. Defined after PENDING because it is
#: PENDING plus the approved state.
CONSUMING: frozenset[str] = PENDING | {APPROVED}

# -- CancellationRequest states (CW-EL-02 STT rows 1-8) ------------------------
CANCEL_PENDING_UNIT_HEAD = "cancellation_pending_unit_head_review"
CANCEL_PENDING_ESTABLISHMENT = "cancellation_pending_establishment"
CANCEL_PENDING_FINAL = "cancellation_pending_final_decision"
CANCEL_APPROVED = "cancellation_approved"
CANCEL_REJECTED = "cancellation_rejected"
CANCEL_WITHDRAWN = "cancellation_withdrawn"

CANCELLATION_STATES: tuple[str, ...] = (
    CANCEL_PENDING_UNIT_HEAD, CANCEL_PENDING_ESTABLISHMENT, CANCEL_PENDING_FINAL,
    CANCEL_APPROVED, CANCEL_REJECTED, CANCEL_WITHDRAWN,
)
CANCELLATION_PENDING: frozenset[str] = frozenset({
    CANCEL_PENDING_UNIT_HEAD, CANCEL_PENDING_ESTABLISHMENT, CANCEL_PENDING_FINAL,
})

# -- ExtensionRequest states (CW-EL-03 STT rows 1-11) -------------------------
EXT_AWAITING_SUBSTITUTE = "awaiting_extension_substitute_response"
EXT_APPLICANT_ACTION_REQUIRED = "extension_applicant_action_required"
EXT_AWAITING_UNIT_HEAD = "awaiting_extension_unit_head_review"
EXT_PENDING_ESTABLISHMENT = "extension_pending_establishment"
EXT_PENDING_FINAL = "extension_pending_final_decision"
EXT_APPROVED = "extension_approved"
EXT_REJECTED = "extension_rejected"
EXT_WITHDRAWN = "extension_withdrawn"

EXTENSION_STATES: tuple[str, ...] = (
    EXT_AWAITING_SUBSTITUTE, EXT_APPLICANT_ACTION_REQUIRED, EXT_AWAITING_UNIT_HEAD,
    EXT_PENDING_ESTABLISHMENT, EXT_PENDING_FINAL, EXT_APPROVED, EXT_REJECTED,
    EXT_WITHDRAWN,
)
EXTENSION_PENDING: frozenset[str] = frozenset({
    EXT_AWAITING_SUBSTITUTE, EXT_APPLICANT_ACTION_REQUIRED, EXT_AWAITING_UNIT_HEAD,
    EXT_PENDING_ESTABLISHMENT, EXT_PENDING_FINAL,
})

# -- ResumptionRequest states (CW-EL-04 STT rows 1-4) -------------------------
RESUMPTION_PENDING = "resumption_review_pending"
RESUMPTION_NO_ADJUSTMENT = "resumption_reviewed_no_adjustment"
RESUMPTION_EARLY = "resumption_reviewed_early_return_synchronized"
RESUMPTION_LATE = "resumption_reviewed_late_return_synchronized"

RESUMPTION_STATES: tuple[str, ...] = (
    RESUMPTION_PENDING, RESUMPTION_NO_ADJUSTMENT, RESUMPTION_EARLY, RESUMPTION_LATE,
)


class InvalidTransition(Exception):
    def __init__(self, workflow: str, frm: str, to: str):
        super().__init__(
            f"{workflow} does not allow moving from {frm!r} to {to!r}.")
        self.workflow, self.frm, self.to = workflow, frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_role: str, workflow: str, frm: str, to: str):
        super().__init__(
            f"A {actor_role} may not move {workflow} from {frm!r} to {to!r}.")
        self.actor_role, self.workflow, self.frm, self.to = (
            actor_role, workflow, frm, to)


@dataclass(frozen=True)
class Transition:
    workflow: str
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


def _t(workflow, frm, to, permission, actors, *guards) -> Transition:
    return Transition(workflow, frm, to, permission, frozenset(actors), guards)


_EMPLOYEE_ONLY = (EMPLOYEE,)
_AUTHORITIES = (UNIT_HEAD, ESTABLISHMENT, SANCTIONING_AUTHORITY)

#: Every state a pending request can be withdrawn from (CW-EL-01 STT row 17).
_WITHDRAWABLE = (AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
                 AWAITING_ESTABLISHMENT, AWAITING_FINAL_DECISION, AWAITING_DIRECTOR)

TRANSITIONS: tuple[Transition, ...] = (
    # -- CW-EL-01 new leave. Submission lands in one of three states by guard. --
    _t(NEW_LEAVE, DRAFT, AWAITING_SUBSTITUTE, P_CREATE, _EMPLOYEE_ONLY,
       "is_valid", "substitute_required"),
    _t(NEW_LEAVE, DRAFT, AWAITING_DIRECTOR, P_CREATE, _EMPLOYEE_ONLY,
       "is_valid", "applicant_is_director"),
    _t(NEW_LEAVE, DRAFT, AWAITING_UNIT_HEAD, P_CREATE, _EMPLOYEE_ONLY,
       "is_valid", "has_unit_head"),

    # CW-EL-01 rows 4-6: the substitute's answer, then the decline recovery.
    _t(NEW_LEAVE, AWAITING_SUBSTITUTE, AWAITING_DIRECTOR, P_SUBSTITUTE,
       (SUBSTITUTE,), "accepted", "applicant_is_director"),
    _t(NEW_LEAVE, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, P_SUBSTITUTE,
       (SUBSTITUTE,), "accepted"),
    _t(NEW_LEAVE, AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, P_SUBSTITUTE,
       (SUBSTITUTE,), "declined"),
    _t(NEW_LEAVE, APPLICANT_ACTION_REQUIRED, AWAITING_SUBSTITUTE, P_CREATE,
       _EMPLOYEE_ONLY, "nominee_eligible"),

    # CW-EL-01 rows 8-9: CL/RH is Unit-Head-final (BR-EL-016).
    _t(NEW_LEAVE, AWAITING_UNIT_HEAD, APPROVED, P_APPROVE, (UNIT_HEAD,),
       "is_unit_head_final", "has_note"),
    _t(NEW_LEAVE, AWAITING_UNIT_HEAD, REJECTED, P_APPROVE, (UNIT_HEAD,),
       "is_unit_head_final", "has_note"),
    # CW-EL-01 rows 10-11: a recommendation, never a final rejection (BR-EL-017).
    _t(NEW_LEAVE, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT, P_APPROVE,
       (UNIT_HEAD,), "is_higher_sanction", "establishment_configured", "has_note"),
    _t(NEW_LEAVE, AWAITING_UNIT_HEAD, AWAITING_FINAL_DECISION, P_APPROVE,
       (UNIT_HEAD,), "is_higher_sanction", "establishment_bypassed", "has_note"),

    # CW-EL-01 row 12.
    _t(NEW_LEAVE, AWAITING_ESTABLISHMENT, AWAITING_FINAL_DECISION, P_APPROVE,
       (ESTABLISHMENT,), "routing_valid", "has_note"),

    # CW-EL-01 rows 13-14.
    _t(NEW_LEAVE, AWAITING_FINAL_DECISION, APPROVED, P_APPROVE,
       (SANCTIONING_AUTHORITY,), "has_note"),
    _t(NEW_LEAVE, AWAITING_FINAL_DECISION, REJECTED, P_APPROVE,
       (SANCTIONING_AUTHORITY,), "has_note"),

    # CW-EL-01 rows 15-16, the Director's own leave (BR-EL-020).
    _t(NEW_LEAVE, AWAITING_DIRECTOR, APPROVED, P_APPROVE, (DIRECTOR,), "has_note"),
    _t(NEW_LEAVE, AWAITING_DIRECTOR, REJECTED, P_APPROVE, (DIRECTOR,), "has_note"),

    # CW-EL-01 row 17: immediate, terminal, cross-cutting (BR-EL-022).
    *(_t(NEW_LEAVE, state, WITHDRAWN, P_WITHDRAW, _EMPLOYEE_ONLY)
      for state in _WITHDRAWABLE),

    # -- CW-EL-02 cancellation, through the same hierarchy (BR-EL-023) --------
    _t(CANCELLATION, CANCEL_PENDING_UNIT_HEAD, CANCEL_APPROVED, P_APPROVE,
       (UNIT_HEAD,), "is_unit_head_final", "has_note"),
    _t(CANCELLATION, CANCEL_PENDING_UNIT_HEAD, CANCEL_REJECTED, P_APPROVE,
       (UNIT_HEAD,), "is_unit_head_final", "has_note"),
    _t(CANCELLATION, CANCEL_PENDING_UNIT_HEAD, CANCEL_PENDING_ESTABLISHMENT,
       P_APPROVE, (UNIT_HEAD,), "is_higher_sanction", "establishment_configured"),
    _t(CANCELLATION, CANCEL_PENDING_UNIT_HEAD, CANCEL_PENDING_FINAL, P_APPROVE,
       (UNIT_HEAD,), "is_higher_sanction", "establishment_bypassed"),
    _t(CANCELLATION, CANCEL_PENDING_ESTABLISHMENT, CANCEL_PENDING_FINAL, P_APPROVE,
       (ESTABLISHMENT,), "routing_valid", "has_note"),
    _t(CANCELLATION, CANCEL_PENDING_FINAL, CANCEL_APPROVED, P_APPROVE,
       (SANCTIONING_AUTHORITY,), "has_note"),
    _t(CANCELLATION, CANCEL_PENDING_FINAL, CANCEL_REJECTED, P_APPROVE,
       (SANCTIONING_AUTHORITY,), "has_note"),
    *(_t(CANCELLATION, state, CANCEL_WITHDRAWN, P_WITHDRAW, _EMPLOYEE_ONLY)
      for state in CANCELLATION_PENDING),

    # -- CW-EL-03 extension. Approval posts only the increment (BR-EL-025). ---
    _t(EXTENSION, EXT_AWAITING_SUBSTITUTE, EXT_AWAITING_UNIT_HEAD, P_SUBSTITUTE,
       (SUBSTITUTE,), "accepted"),
    _t(EXTENSION, EXT_AWAITING_SUBSTITUTE, EXT_APPLICANT_ACTION_REQUIRED,
       P_SUBSTITUTE, (SUBSTITUTE,), "declined"),
    _t(EXTENSION, EXT_APPLICANT_ACTION_REQUIRED, EXT_AWAITING_SUBSTITUTE, P_CREATE,
       _EMPLOYEE_ONLY, "nominee_eligible"),
    _t(EXTENSION, EXT_AWAITING_UNIT_HEAD, EXT_PENDING_ESTABLISHMENT, P_APPROVE,
       (UNIT_HEAD,), "establishment_configured", "has_note"),
    _t(EXTENSION, EXT_AWAITING_UNIT_HEAD, EXT_PENDING_FINAL, P_APPROVE,
       (UNIT_HEAD,), "establishment_bypassed", "has_note"),
    _t(EXTENSION, EXT_PENDING_ESTABLISHMENT, EXT_PENDING_FINAL, P_APPROVE,
       (ESTABLISHMENT,), "routing_valid", "has_note"),
    _t(EXTENSION, EXT_PENDING_FINAL, EXT_APPROVED, P_APPROVE,
       (SANCTIONING_AUTHORITY,), "has_note"),
    _t(EXTENSION, EXT_PENDING_FINAL, EXT_REJECTED, P_APPROVE,
       (SANCTIONING_AUTHORITY,), "has_note"),
    *(_t(EXTENSION, state, EXT_WITHDRAWN, P_WITHDRAW, _EMPLOYEE_ONLY)
      for state in EXTENSION_PENDING),

    # -- CW-EL-04 resumption. No generic closure state exists (BR-EL-028). ----
    _t(RESUMPTION, RESUMPTION_PENDING, RESUMPTION_NO_ADJUSTMENT, P_APPROVE,
       (SANCTIONING_AUTHORITY,), "resumed_on_approved_end_date"),
    _t(RESUMPTION, RESUMPTION_PENDING, RESUMPTION_EARLY, P_APPROVE,
       (SANCTIONING_AUTHORITY,), "resumed_before_approved_end_date"),
    _t(RESUMPTION, RESUMPTION_PENDING, RESUMPTION_LATE, P_APPROVE,
       (SANCTIONING_AUTHORITY,), "resumed_after_approved_end_date"),

    # -- XTP-EL-01: escalation reassigns an open task without moving the
    #    business state, which is why it is not an edge above (BR-EL-033).
    _t(NEW_LEAVE, AWAITING_FINAL_DECISION, AWAITING_FINAL_DECISION, P_SLA_ESCALATE,
       (SYSTEM,), "still_pending"),
)

_INDEX: dict[tuple[str, str, str], Transition] = {
    (t.workflow, t.frm, t.to): t for t in TRANSITIONS
}


def resolve(workflow: str, frm: str, to: str,
            actor_role: str | None = None) -> Transition:
    """The single lookup every write goes through."""
    t = _INDEX.get((workflow, frm, to))
    if t is None:
        raise InvalidTransition(workflow, frm, to)
    if actor_role is not None and actor_role not in t.actors:
        raise ActorNotAllowed(actor_role, workflow, frm, to)
    return t


def is_legal(workflow: str, frm: str, to: str) -> bool:
    return (workflow, frm, to) in _INDEX


def allowed_targets(workflow: str, frm: str,
                    actor_role: str | None = None) -> list[str]:
    return sorted({t.to for t in TRANSITIONS
                   if t.workflow == workflow and t.frm == frm
                   and (actor_role is None or actor_role in t.actors)})


def states_for(workflow: str) -> tuple[str, ...]:
    return {
        NEW_LEAVE: LEAVE_STATES,
        CANCELLATION: CANCELLATION_STATES,
        EXTENSION: EXTENSION_STATES,
        RESUMPTION: RESUMPTION_STATES,
    }[workflow]