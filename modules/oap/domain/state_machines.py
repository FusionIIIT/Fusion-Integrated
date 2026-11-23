"""Declarative transition tables: (state, event, role) -> next state.

An illegal transition is absent from the table, so next_state refuses it.
"""

from __future__ import annotations

from modules.oap.domain.errors import IllegalTransition

LEAVE_SUBMITTED = "submitted"
LEAVE_APPROVED = "approved"
LEAVE_REJECTED = "rejected"

BONAFIDE_SUBMITTED = "submitted"
BONAFIDE_APPROVED = "approved"
BONAFIDE_REJECTED = "rejected"

CLAIM_AWAITING_DUAL = "awaiting_dual_verification"
CLAIM_AWAITING_OTHER = "awaiting_other_verification"
CLAIM_AWAITING_DEPT_REVIEW = "awaiting_department_review"
CLAIM_AWAITING_HOD = "awaiting_hod_decision"
CLAIM_APPROVED = "approved_awaiting_stipend"
CLAIM_REJECTED = "rejected"
CLAIM_STIPEND_PROCESSED = "stipend_processed"

SEMINAR_AWAITING = "awaiting_scheduling"
SEMINAR_SCHEDULED = "scheduled"

LEAVE = {
    (LEAVE_SUBMITTED, "approve", "hod"): LEAVE_APPROVED,
    (LEAVE_SUBMITTED, "reject", "hod"): LEAVE_REJECTED,
}

BONAFIDE = {
    (BONAFIDE_SUBMITTED, "approve", "academic_admin"): BONAFIDE_APPROVED,
    (BONAFIDE_SUBMITTED, "reject", "academic_admin"): BONAFIDE_REJECTED,
}

CLAIM = {
    (CLAIM_AWAITING_DUAL, "verify", "supervisor"): CLAIM_AWAITING_OTHER,
    (CLAIM_AWAITING_OTHER, "verify", "supervisor"): CLAIM_AWAITING_DEPT_REVIEW,
    (CLAIM_AWAITING_DEPT_REVIEW, "forward", "dept_admin"): CLAIM_AWAITING_HOD,
    (CLAIM_AWAITING_HOD, "approve", "hod"): CLAIM_APPROVED,
    (CLAIM_AWAITING_HOD, "reject", "hod"): CLAIM_REJECTED,
    (CLAIM_APPROVED, "process_stipend", "academic_admin"): CLAIM_STIPEND_PROCESSED,
}

SEMINAR = {
    (SEMINAR_AWAITING, "schedule", "dept_admin"): SEMINAR_SCHEDULED,
}

MACHINES = {
    "leave": LEAVE,
    "bonafide": BONAFIDE,
    "claim": CLAIM,
    "seminar": SEMINAR,
}


def next_state(machine: str, state: str, event: str, role: str) -> str:
    table = MACHINES[machine]
    try:
        return table[(state, event, role)]
    except KeyError as exc:
        raise IllegalTransition(
            f"{machine}: '{event}' by {role} is not allowed from '{state}'."
        ) from exc
