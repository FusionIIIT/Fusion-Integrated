"""Guard evaluation: the table says WHICH guards, this says whether they hold.

A transition's guards are names, never inline lambdas — the table stays
declarative and renderable, and every rule gets exactly one implementation
that the tests can reach directly.

`Facts` is the whole picture a service assembles before it moves anything:
policy-derived facts (which category, whose leave, which decision) alongside
data-derived ones (has the leave started, is the nominee eligible). The
functions below are pure over that value object, which is why the interesting
rules test with no database at all.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.leave.domain import categories as cat
from modules.leave.domain import routing
from modules.leave.domain.state_machine import (
    KIND_NEW,
    GuardFailed,
    outgoing,
)

APPROVE = "approve"
REJECT = "reject"
ACCEPT = "accept"
DECLINE = "decline"


@dataclass(frozen=True)
class Facts:
    kind: str = KIND_NEW
    category_code: str = cat.CL
    employee_kind: str = cat.STAFF
    roles: tuple[str, ...] = ()
    #: Does this request need a substitute at all?
    substitute_required: bool = False
    #: approve | reject | recommended | not_recommended | accept | decline
    decision: str = ""
    establishment_configured: bool = False
    #: The leave the request acts on, for extension/cancellation/resumption.
    leave_started: bool = False
    leave_ended: bool = False
    #: Withdrawal is available only before a final decision.
    is_final: bool = False
    replacement_eligible: bool = False
    routing_context_valid: bool = True


def _substitute_required(f: Facts) -> bool:
    return f.substitute_required


def _no_substitute_required(f: Facts) -> bool:
    return not f.substitute_required


def _applicant_is_director(f: Facts) -> bool:
    return routing.is_director(f.roles)


def _applicant_not_director(f: Facts) -> bool:
    return not routing.is_director(f.roles)


def _consent_accepted(f: Facts) -> bool:
    return f.decision == ACCEPT


def _consent_declined(f: Facts) -> bool:
    return f.decision == DECLINE


def _replacement_eligible(f: Facts) -> bool:
    return f.replacement_eligible


def _unit_head_final(f: Facts) -> bool:
    return cat.category(f.category_code).unit_head_final


def _higher_sanction(f: Facts) -> bool:
    return not cat.category(f.category_code).unit_head_final


def _establishment_configured(f: Facts) -> bool:
    return f.establishment_configured


def _decision_approve(f: Facts) -> bool:
    return f.decision == APPROVE


def _decision_reject(f: Facts) -> bool:
    return f.decision == REJECT


def _routing_context_valid(f: Facts) -> bool:
    return f.routing_context_valid


def _not_final(f: Facts) -> bool:
    return not f.is_final


def _pre_start(f: Facts) -> bool:
    """Cancellation is available only before the leave begins (BR-EL-023)."""
    return not f.leave_started


def _leave_ongoing(f: Facts) -> bool:
    """Extension applies to leave already in effect and not yet returned."""
    return f.leave_started and not f.leave_ended


def _extension_eligible(f: Facts) -> bool:
    return cat.category(f.category_code).extension_eligible


def _leave_started(f: Facts) -> bool:
    return f.leave_started


def _resumption_eligible(f: Facts) -> bool:
    return cat.category(f.category_code).resumption_applies


#: Every guard named in the state machine. An unknown name is a loud failure
#: rather than a silently-passing check.
GUARDS = {
    "substitute_required": _substitute_required,
    "no_substitute_required": _no_substitute_required,
    "applicant_is_director": _applicant_is_director,
    "applicant_not_director": _applicant_not_director,
    "consent_accepted": _consent_accepted,
    "consent_declined": _consent_declined,
    "replacement_eligible": _replacement_eligible,
    "unit_head_final": _unit_head_final,
    "higher_sanction": _higher_sanction,
    "establishment_configured": _establishment_configured,
    "decision_approve": _decision_approve,
    "decision_reject": _decision_reject,
    "routing_context_valid": _routing_context_valid,
    "not_final": _not_final,
    "pre_start": _pre_start,
    "leave_ongoing": _leave_ongoing,
    "extension_eligible": _extension_eligible,
    "leave_started": _leave_started,
    "resumption_eligible": _resumption_eligible,
}


def satisfied(name: str, facts: Facts) -> bool:
    try:
        fn = GUARDS[name]
    except KeyError as exc:
        raise LookupError(f"Guard {name!r} has no implementation.") from exc
    return fn(facts)


def check(transition, facts: Facts) -> None:
    """Raise GuardFailed on the first unsatisfied guard."""
    for name in transition.guards:
        if not satisfied(name, facts):
            raise GuardFailed(name)


def select(*, frm: str, permission: str, facts: Facts, actor_kind: str):
    """The transition this caller may actually take.

    Several transitions can share a `frm` and differ only in their guards —
    a CL/RH request and a higher-sanction request both leave the Unit Head, but
    not to the same place. Walking the table and taking the first edge whose
    guards hold is what keeps "which state next?" a property of the rules
    rather than of the calling code.
    """
    for t in outgoing(frm):
        if t.permission != permission or t.actor != actor_kind:
            continue
        try:
            check(t, facts)
        except GuardFailed:
            continue
        return t
    raise GuardFailed("no_transition", _why_not(frm, permission, facts))


def _why_not(frm: str, permission: str, facts: Facts) -> str:
    """A sentence for whoever is holding the request, not a stack trace."""
    tried = [t for t in outgoing(frm)
             if t.permission == permission]
    if not tried:
        return (f"Nothing may be done to a leave request in state {frm!r} with "
                f"{permission!r}.")
    for t in tried:
        for name in t.guards:
            if not satisfied(name, facts):
                return f"{name} is not satisfied for this request."
    return "No transition's guards are satisfied."
