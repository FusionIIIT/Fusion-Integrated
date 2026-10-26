from dataclasses import dataclass

DRAFT = "draft"
AWAITING_SUBSTITUTE = "awaiting_substitute"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
AWAITING_UNIT_HEAD = "awaiting_unit_head"
AWAITING_FINAL_SANCTION = "awaiting_final_sanction"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

TERMINAL = frozenset({APPROVED, REJECTED, WITHDRAWN})

SANCTIONING_AUTHORITY = "sanctioning_authority"

EMPLOYEE = "employee"
SUBSTITUTE = "substitute"
UNIT_HEAD = "unit_head"

class InvalidTransition(Exception):
    def __init__(self, frm: str, event: str):
        super().__init__(f"Cannot apply {event!r} to a leave request in status {frm!r}.")
        self.frm, self.event = frm, event


@dataclass(frozen=True)
class Transition:
    frm: str
    event: str
    actor: str
    to: str


TRANSITIONS = (
    Transition(DRAFT, "submit_with_substitute", EMPLOYEE, AWAITING_SUBSTITUTE),
    Transition(DRAFT, "submit_without_substitute", EMPLOYEE, AWAITING_UNIT_HEAD),
    Transition(AWAITING_SUBSTITUTE, "substitute_accept", SUBSTITUTE, AWAITING_UNIT_HEAD),
    Transition(AWAITING_SUBSTITUTE, "substitute_decline", SUBSTITUTE, APPLICANT_ACTION_REQUIRED),
    Transition(AWAITING_UNIT_HEAD, "unit_head_approve", UNIT_HEAD, APPROVED),
    Transition(AWAITING_UNIT_HEAD, "unit_head_reject", UNIT_HEAD, REJECTED),
    Transition(AWAITING_UNIT_HEAD, "unit_head_recommend", UNIT_HEAD, AWAITING_FINAL_SANCTION),
    Transition(AWAITING_FINAL_SANCTION, "sanction_approve", SANCTIONING_AUTHORITY, APPROVED),
    Transition(AWAITING_FINAL_SANCTION, "sanction_reject", SANCTIONING_AUTHORITY, REJECTED),
    Transition(AWAITING_SUBSTITUTE, "withdraw", EMPLOYEE, WITHDRAWN),
    Transition(APPLICANT_ACTION_REQUIRED, "withdraw", EMPLOYEE, WITHDRAWN),
    Transition(AWAITING_UNIT_HEAD, "withdraw", EMPLOYEE, WITHDRAWN),
    Transition(AWAITING_FINAL_SANCTION, "withdraw", EMPLOYEE, WITHDRAWN),
)

_INDEX = {(t.frm, t.event, t.actor): t for t in TRANSITIONS}


def can_transition(current_status: str, event: str, actor: str) -> bool:
    return (current_status, event, actor) in _INDEX


def next_status(current_status: str, event: str, actor: str) -> str:
    if not can_transition(current_status, event, actor):
        raise InvalidTransition(current_status, event)
    return _INDEX[(current_status, event, actor)].to
