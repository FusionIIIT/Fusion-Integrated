"""Declarative state machine for ELM workflows (WF-EL-01..17)."""
from dataclasses import dataclass

class InvalidTransition(ValueError):
    pass

@dataclass(frozen=True)
class Transition:
    source: str
    event: str
    target: str
    actor: str

TRANSITIONS = (
    Transition("", "submit", "awaiting_unit_head", "employee"),
    Transition("", "submit_with_substitute", "awaiting_substitute", "employee"),
    Transition("", "director_submit", "awaiting_director", "director"),
    Transition("", "offline_record_sync", "approved", "leave_administrator"),
    Transition("awaiting_substitute", "substitute_accept", "awaiting_unit_head", "substitute"),
    Transition("awaiting_substitute", "substitute_accept_director", "awaiting_director", "substitute"),
    Transition("awaiting_substitute", "substitute_decline", "substitute_declined", "substitute"),
    Transition("awaiting_substitute", "withdraw", "withdrawn", "employee"),
    Transition("substitute_declined", "withdraw", "withdrawn", "employee"),
    Transition("substitute_declined", "nominate_replacement", "awaiting_substitute", "employee"),
    Transition("awaiting_unit_head", "withdraw", "withdrawn", "employee"),
    Transition("awaiting_establishment", "withdraw", "withdrawn", "employee"),
    Transition("awaiting_sanction", "withdraw", "withdrawn", "employee"),
    Transition("awaiting_director", "withdraw", "withdrawn", "employee"),
    Transition("awaiting_unit_head", "unit_recommend", "awaiting_sanction", "unit_head"),
    Transition("awaiting_unit_head", "unit_approve", "approved", "unit_head"),
    Transition("awaiting_unit_head", "unit_reject", "rejected", "unit_head"),
    Transition("awaiting_establishment", "establishment_forward", "awaiting_sanction", "establishment"),
    Transition("awaiting_establishment", "establishment_reject", "rejected", "establishment"),
    Transition("awaiting_sanction", "sanction_approve", "approved", "sanctioning"),
    Transition("awaiting_sanction", "sanction_reject", "rejected", "sanctioning"),
    Transition("awaiting_director", "director_self_sanction", "approved", "director"),
    Transition("approved", "request_cancellation", "cancellation_pending", "employee"),
    Transition("", "extension_submit", "awaiting_unit_head", "employee"),
    Transition("", "director_extension_submit", "awaiting_director", "director"),
    Transition("cancellation_pending", "cancellation_approve", "cancelled", "sanctioning"),
    Transition("cancellation_pending", "cancellation_reject", "approved", "sanctioning"),
    Transition("approved", "submit_resumption", "resumption_pending", "employee"),
    Transition("resumption_pending", "verify_resumption_normal", "resumption_reviewed_no_adjustment", "sanctioning"),
    Transition("resumption_pending", "verify_resumption_early", "resumption_reviewed_early", "sanctioning"),
    Transition("resumption_pending", "verify_resumption_late", "resumption_reviewed_late", "sanctioning"),
)
_INDEX = {(t.source, t.event): t for t in TRANSITIONS}

def transition(source: str, event: str, actor: str | None = None) -> Transition:
    result = _INDEX.get((source, event))
    if result is None or (actor is not None and result.actor != actor):
        raise InvalidTransition(f"Event {event!r} is not allowed from {source!r} for {actor or 'this actor'}.")
    return result
