"""Request state transitions (WF-EL-01, WF-EL-02; BR-EL-015..022).

Pure functions: given the current state and the facts of the case, return the next
state or raise TransitionError. Nothing here touches the database or notifies anyone;
the caller applies the result.
"""
from modules.elm.models import Decision, LeaveRequest

S = LeaveRequest.Status
Outcome = Decision.Outcome

#: Categories where the Unit Head is the final authority (BR-EL-016).
UNIT_HEAD_FINAL = {"CL", "RH"}

#: States in which a request is pending and may still be withdrawn or modified
#: (BR-EL-021, BR-EL-022). Approved and later states are excluded.
PENDING = {
    S.AWAITING_SUBSTITUTE, S.AWAITING_UNIT_HEAD, S.AWAITING_ESTABLISHMENT,
    S.AWAITING_FINAL, S.AWAITING_DIRECTOR_SELF,
}


class TransitionError(Exception):
    pass


def _require(current, allowed, action: str) -> None:
    if current not in allowed:
        raise TransitionError(f"Cannot {action} a request in state '{current}'.")


def _first_gate(director_applicant: bool) -> str:
    """After all pre-routing gates are satisfied (BR-EL-020)."""
    return S.AWAITING_DIRECTOR_SELF if director_applicant else S.AWAITING_UNIT_HEAD


def submit(current, substitute_required: bool, director_applicant: bool) -> str:
    """WF-EL-01 steps 2 to 4. Validation must already have passed."""
    _require(current, {S.DRAFT}, "submit")
    if substitute_required:
        return S.AWAITING_SUBSTITUTE
    return _first_gate(director_applicant)


def substitute_accepted(current, director_applicant: bool) -> str:
    """WF-EL-01 steps 5 and 6; releases the consent gate (BR-EL-015)."""
    _require(current, {S.AWAITING_SUBSTITUTE}, "accept substitution on")
    return _first_gate(director_applicant)


def substitute_declined(current) -> str:
    """WF-EL-01 step 7: routing stays blocked; the applicant renominates or withdraws."""
    _require(current, {S.AWAITING_SUBSTITUTE}, "decline substitution on")
    return S.AWAITING_SUBSTITUTE


def unit_head_decision(current, leave_type: str, outcome: str,
                       establishment_configured: bool) -> str:
    """WF-EL-01 steps 8 to 11 (BR-EL-016, BR-EL-017)."""
    _require(current, {S.AWAITING_UNIT_HEAD}, "review")
    if leave_type in UNIT_HEAD_FINAL:
        if outcome == Outcome.APPROVED:
            return S.APPROVED
        if outcome == Outcome.REJECTED:
            return S.REJECTED
        raise TransitionError("Unit Head must approve or reject CL/RH.")
    # SCL, EL, COL, VL: the Unit Head recommends, never finally rejects.
    if outcome not in (Outcome.RECOMMENDED, Outcome.NOT_RECOMMENDED):
        raise TransitionError("Unit Head must record Recommended or Not Recommended.")
    return S.AWAITING_ESTABLISHMENT if establishment_configured else S.AWAITING_FINAL


def establishment_routed(current) -> str:
    """WF-EL-01 step 12."""
    _require(current, {S.AWAITING_ESTABLISHMENT}, "route")
    return S.AWAITING_FINAL


def final_decision(current, outcome: str) -> str:
    """WF-EL-01 steps 13 to 16; also covers the Director self-sanction case."""
    _require(current, {S.AWAITING_FINAL, S.AWAITING_DIRECTOR_SELF}, "decide")
    if outcome == Outcome.APPROVED:
        return S.APPROVED
    if outcome == Outcome.REJECTED:
        return S.REJECTED
    raise TransitionError("Final decision must be approve or reject.")


def can_modify(current) -> bool:
    return current in PENDING


def withdraw(current) -> str:
    """WF-EL-02 step 4 (BR-EL-022): effective immediately, only before final approval."""
    if current not in PENDING:
        raise TransitionError(
            "Only a pending request can be withdrawn; use cancellation after approval.")
    return S.WITHDRAWN


def modify_restart_state(substitute_required: bool, director_applicant: bool) -> str:
    """WF-EL-02 step 3: a modified request is re-routed from the start of the path
    (assumption: any material change restarts at the substitute gate or first gate)."""
    if substitute_required:
        return S.AWAITING_SUBSTITUTE
    return _first_gate(director_applicant)
