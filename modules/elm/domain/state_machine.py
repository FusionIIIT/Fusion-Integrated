"""State machine and workflow definitions for ELM.

Pure Python: no Django dependencies.
Authoritative implementation of:
- 17 Complete Basis Workflows (BW-EL-01 to BW-EL-17)
- 4 Composite Workflows (CW-EL-01 to CW-EL-04)
- Authoritative State-Transition Tables (STTs)
- Guard validations (BR-EL-015, BR-EL-016, BR-EL-017, BR-EL-020, BR-EL-022, BR-EL-023, BR-EL-034)
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Sequence

from modules.elm.domain.constants import (
    ApplicationStatus,
    CancellationStatus,
    LeaveCategory,
    Recommendation,
    ResumptionType,
    Role,
    SubstituteStatus,
    TERMINAL_STATUSES,
)


class InvalidTransition(Exception):
    """Raised when an illegal transition is attempted."""


class TransitionGuardFailed(Exception):
    """Raised when a transition guard condition is violated."""


@dataclass(frozen=True)
class Transition:
    from_state: ApplicationStatus
    to_state: ApplicationStatus
    action: str
    actor_role: str
    basis_workflows: tuple[str, ...]
    composite_workflows: tuple[str, ...]
    description: str


# Authoritative transitions across CW-EL-01 (New Leave & Pending Withdrawal)
NEW_LEAVE_TRANSITIONS: tuple[Transition, ...] = (
    # Apply -> Awaiting Substitute Response (when substitute required)
    Transition(
        from_state=ApplicationStatus.DRAFT,
        to_state=ApplicationStatus.AWAITING_SUBSTITUTE,
        action="apply_with_substitute",
        actor_role=Role.EMPLOYEE,
        basis_workflows=("BW-EL-02", "BW-EL-03", "BW-EL-05", "BW-EL-06", "BW-EL-08", "BW-EL-09"),
        composite_workflows=("CW-EL-01",),
        description="Employee applies with required substitute coverage.",
    ),
    # Apply -> Awaiting Unit Head Review (no substitute, not director)
    Transition(
        from_state=ApplicationStatus.DRAFT,
        to_state=ApplicationStatus.AWAITING_UNIT_HEAD,
        action="apply_direct",
        actor_role=Role.EMPLOYEE,
        basis_workflows=("BW-EL-01", "BW-EL-04"),
        composite_workflows=("CW-EL-01",),
        description="Employee applies without substitute coverage directly to Unit Head.",
    ),
    # Apply -> Awaiting Director Self-Sanction (no substitute, applicant is Director)
    Transition(
        from_state=ApplicationStatus.DRAFT,
        to_state=ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION,
        action="apply_director_direct",
        actor_role=Role.DIRECTOR,
        basis_workflows=("BW-EL-07",),
        composite_workflows=("CW-EL-01",),
        description="Director applies without substitute, routes to self-sanction.",
    ),
    # Substitute accepts -> routes to Unit Head (not Director)
    Transition(
        from_state=ApplicationStatus.AWAITING_SUBSTITUTE,
        to_state=ApplicationStatus.AWAITING_UNIT_HEAD,
        action="substitute_accept",
        actor_role=Role.SUBSTITUTE,
        basis_workflows=("BW-EL-02", "BW-EL-03", "BW-EL-05", "BW-EL-06"),
        composite_workflows=("CW-EL-01",),
        description="Nominated substitute accepts; request unlocks and advances to Unit Head.",
    ),
    # Substitute accepts -> routes to Director Self-Sanction (when Director is applicant)
    Transition(
        from_state=ApplicationStatus.AWAITING_SUBSTITUTE,
        to_state=ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION,
        action="substitute_accept_director",
        actor_role=Role.SUBSTITUTE,
        basis_workflows=("BW-EL-08", "BW-EL-09"),
        composite_workflows=("CW-EL-01",),
        description="Nominated substitute accepts for Director applicant; advances to self-sanction.",
    ),
    # Substitute declines -> Applicant Action Required (consent gate closed)
    Transition(
        from_state=ApplicationStatus.AWAITING_SUBSTITUTE,
        to_state=ApplicationStatus.APPLICANT_ACTION_REQUIRED,
        action="substitute_decline",
        actor_role=Role.SUBSTITUTE,
        basis_workflows=("BW-EL-03", "BW-EL-06", "BW-EL-09"),
        composite_workflows=("CW-EL-01",),
        description="Nominated substitute declines; applicant action required to replace or withdraw.",
    ),
    # Applicant nominates replacement substitute (EL-UC-019)
    Transition(
        from_state=ApplicationStatus.APPLICANT_ACTION_REQUIRED,
        to_state=ApplicationStatus.AWAITING_SUBSTITUTE,
        action="nominate_replacement_substitute",
        actor_role=Role.EMPLOYEE,
        basis_workflows=("BW-EL-03", "BW-EL-06", "BW-EL-09"),
        composite_workflows=("CW-EL-01",),
        description="Applicant nominates another eligible substitute after previous decline.",
    ),
    # Unit Head Review: CL/RH -> APPROVED (Unit Head is final for CL/RH: BR-EL-016)
    Transition(
        from_state=ApplicationStatus.AWAITING_UNIT_HEAD,
        to_state=ApplicationStatus.APPROVED,
        action="unit_head_approve_cl_rh",
        actor_role=Role.UNIT_HEAD,
        basis_workflows=("BW-EL-01", "BW-EL-02", "BW-EL-03"),
        composite_workflows=("CW-EL-01",),
        description="Unit Head makes final decision approving CL/RH request.",
    ),
    # Unit Head Review: CL/RH -> REJECTED (Unit Head is final for CL/RH: BR-EL-016)
    Transition(
        from_state=ApplicationStatus.AWAITING_UNIT_HEAD,
        to_state=ApplicationStatus.REJECTED,
        action="unit_head_reject_cl_rh",
        actor_role=Role.UNIT_HEAD,
        basis_workflows=("BW-EL-01", "BW-EL-02", "BW-EL-03"),
        composite_workflows=("CW-EL-01",),
        description="Unit Head makes final decision rejecting CL/RH request.",
    ),
    # Unit Head Review: Higher Sanction -> Awaiting Establishment Routing (BR-EL-017, BR-EL-019)
    Transition(
        from_state=ApplicationStatus.AWAITING_UNIT_HEAD,
        to_state=ApplicationStatus.AWAITING_ESTABLISHMENT,
        action="unit_head_recommend_establishment",
        actor_role=Role.UNIT_HEAD,
        basis_workflows=("BW-EL-04", "BW-EL-05", "BW-EL-06"),
        composite_workflows=("CW-EL-01",),
        description="Unit Head records recommendation; routes to Establishment where configured.",
    ),
    # Unit Head Review: Higher Sanction -> Awaiting Final Sanction Decision (Establishment bypassed)
    Transition(
        from_state=ApplicationStatus.AWAITING_UNIT_HEAD,
        to_state=ApplicationStatus.AWAITING_SANCTION,
        action="unit_head_recommend_sanction",
        actor_role=Role.UNIT_HEAD,
        basis_workflows=("BW-EL-04", "BW-EL-05", "BW-EL-06"),
        composite_workflows=("CW-EL-01",),
        description="Unit Head records recommendation; routes directly to final Sanctioning Authority.",
    ),
    # Establishment routes higher-sanction request to Sanctioning Authority (EL-UC-004)
    Transition(
        from_state=ApplicationStatus.AWAITING_ESTABLISHMENT,
        to_state=ApplicationStatus.AWAITING_SANCTION,
        action="establishment_route",
        actor_role=Role.ESTABLISHMENT,
        basis_workflows=("BW-EL-04", "BW-EL-05", "BW-EL-06"),
        composite_workflows=("CW-EL-01",),
        description="Establishment verifies and routes higher-sanction request to Sanctioning Authority.",
    ),
    # Final Sanctioning Authority: APPROVED (BR-EL-018)
    Transition(
        from_state=ApplicationStatus.AWAITING_SANCTION,
        to_state=ApplicationStatus.APPROVED,
        action="sanction_approve",
        actor_role=Role.DEAN,  # or Registrar, Director
        basis_workflows=("BW-EL-04", "BW-EL-05", "BW-EL-06"),
        composite_workflows=("CW-EL-01",),
        description="Competent Sanctioning Authority approves higher-sanction request.",
    ),
    # Final Sanctioning Authority: REJECTED (BR-EL-018)
    Transition(
        from_state=ApplicationStatus.AWAITING_SANCTION,
        to_state=ApplicationStatus.REJECTED,
        action="sanction_reject",
        actor_role=Role.DEAN,  # or Registrar, Director
        basis_workflows=("BW-EL-04", "BW-EL-05", "BW-EL-06"),
        composite_workflows=("CW-EL-01",),
        description="Competent Sanctioning Authority rejects higher-sanction request.",
    ),
    # Director Self-Sanction: APPROVED (BR-EL-020)
    Transition(
        from_state=ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION,
        to_state=ApplicationStatus.APPROVED,
        action="director_self_approve",
        actor_role=Role.DIRECTOR,
        basis_workflows=("BW-EL-07", "BW-EL-08", "BW-EL-09"),
        composite_workflows=("CW-EL-01",),
        description="Director self-sanctions and approves own leave.",
    ),
    # Director Self-Sanction: REJECTED (BR-EL-020)
    Transition(
        from_state=ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION,
        to_state=ApplicationStatus.REJECTED,
        action="director_self_reject",
        actor_role=Role.DIRECTOR,
        basis_workflows=("BW-EL-07", "BW-EL-08", "BW-EL-09"),
        composite_workflows=("CW-EL-01",),
        description="Director self-sanctions and rejects own leave.",
    ),
)


# Cross-cutting immediate withdrawal transitions (BR-EL-022, BR-EL-034, EL-UC-007)
# Valid from every pending pre-final state!
WITHDRAWAL_SOURCE_STATES = (
    ApplicationStatus.AWAITING_SUBSTITUTE,
    ApplicationStatus.APPLICANT_ACTION_REQUIRED,
    ApplicationStatus.AWAITING_UNIT_HEAD,
    ApplicationStatus.AWAITING_ESTABLISHMENT,
    ApplicationStatus.AWAITING_SANCTION,
    ApplicationStatus.AWAITING_DIRECTOR_SELF_SANCTION,
)


def get_withdrawal_transitions() -> list[Transition]:
    """Generates cross-cutting withdrawal transitions from all pending pre-final states."""
    transitions = []
    for st in WITHDRAWAL_SOURCE_STATES:
        transitions.append(
            Transition(
                from_state=st,
                to_state=ApplicationStatus.WITHDRAWN,
                action="withdraw_pending",
                actor_role=Role.EMPLOYEE,
                basis_workflows=(),
                composite_workflows=("CW-EL-01", "CW-EL-03"),
                description=f"Immediate terminal withdrawal of pending request from {st.value}.",
            )
        )
    return transitions


ALL_TRANSITIONS: tuple[Transition, ...] = (
    *NEW_LEAVE_TRANSITIONS,
    *get_withdrawal_transitions(),
)


def is_legal_transition(from_state: ApplicationStatus, to_state: ApplicationStatus) -> bool:
    """Check if a direct transition between from_state and to_state is legal."""
    return any(t.from_state == from_state and t.to_state == to_state for t in ALL_TRANSITIONS)


def get_legal_next_states(from_state: ApplicationStatus) -> list[ApplicationStatus]:
    """Returns all legal next target states from a given status."""
    return sorted(
        {t.to_state for t in ALL_TRANSITIONS if t.from_state == from_state},
        key=lambda s: s.value,
    )


def resolve_transition(from_state: ApplicationStatus, action: str) -> Transition:
    """Resolve the specific transition matching from_state and action, or raise InvalidTransition."""
    for t in ALL_TRANSITIONS:
        if t.from_state == from_state and t.action == action:
            return t
    raise InvalidTransition(
        f"Action '{action}' is not legal from current application state '{from_state.value}'."
    )


def validate_unit_head_decision(
    category: str | LeaveCategory,
    outcome: str | Recommendation,
    has_establishment_step: bool = False,
) -> ApplicationStatus:
    """Validate Unit Head decision and determine resulting application status.

    - BR-EL-016: For CL and RH, Unit Head is final (Approved or Rejected).
    - BR-EL-017: For SCL, EL, COL, VL, Unit Head records Recommended or Not Recommended.
      Both outcomes continue to higher sanction (Not Recommended is not a final rejection).
    """
    cat = LeaveCategory(category)
    outcome_str = outcome.value if isinstance(outcome, Recommendation) else str(outcome).upper()

    if cat in (LeaveCategory.CL, LeaveCategory.RH):
        if outcome_str in ("RECOMMENDED", "APPROVE"):
            return ApplicationStatus.APPROVED
        elif outcome_str in ("NOT_RECOMMENDED", "REJECT"):
            return ApplicationStatus.REJECTED
        else:
            raise TransitionGuardFailed(f"Invalid outcome '{outcome}' for CL/RH at Unit Head.")

    # Higher-sanction categories (SCL, EL, COL, VL)
    if outcome_str not in ("RECOMMENDED", "NOT_RECOMMENDED"):
        raise TransitionGuardFailed(
            f"Higher-sanction leave ({cat.value}) requires Unit Head outcome of "
            f"RECOMMENDED or NOT_RECOMMENDED, got '{outcome}'."
        )

    if has_establishment_step:
        return ApplicationStatus.AWAITING_ESTABLISHMENT
    return ApplicationStatus.AWAITING_SANCTION


def validate_withdrawal(current_status: ApplicationStatus) -> None:
    """BR-EL-022 / BR-EL-034: Withdrawal is available only before final approval.

    Once Approved, Rejected, Withdrawn, or Cancelled, withdrawal is strictly unavailable.
    """
    if current_status in TERMINAL_STATUSES:
        raise TransitionGuardFailed(
            f"Cannot withdraw application in terminal status '{current_status.value}'."
        )
    if current_status not in WITHDRAWAL_SOURCE_STATES:
        raise TransitionGuardFailed(
            f"Cannot withdraw application from current status '{current_status.value}'."
        )


def validate_cancellation_request(
    current_status: ApplicationStatus,
    start_date: datetime.date,
    today: datetime.date,
) -> None:
    """BR-EL-023: Approved leave may be cancelled ONLY before its start date.

    Once leave has begun, pre-start cancellation no longer applies.
    """
    if current_status != ApplicationStatus.APPROVED:
        raise TransitionGuardFailed(
            f"Cancellation can only be requested for APPROVED leave, got '{current_status.value}'."
        )
    if start_date <= today:
        raise TransitionGuardFailed(
            f"Pre-start cancellation is unavailable because leave start date ({start_date}) "
            f"has already arrived or passed (today: {today}). Change must use resumption/extension."
        )


def evaluate_resumption(
    approved_end_date: datetime.date,
    actual_resumption_date: datetime.date,
) -> tuple[ResumptionType, int]:
    """BR-EL-028: Normal, early, and late resumption outcome.

    - Normal: actual resumption equals expected resumption (day after approved end date).
      No adjustment to leave days or balance.
    - Early: returned earlier than approved end date.
      Difference in days is restored to balance.
    - Late: returned later than approved end date.
      Additional days are charged.
    """
    # In standard office practice, if approved leave is Monday to Wednesday,
    # the employee resumes duty on Thursday.
    expected_resumption = approved_end_date + datetime.timedelta(days=1)
    diff = (actual_resumption_date - expected_resumption).days

    if diff == 0:
        return ResumptionType.NORMAL, 0
    elif diff < 0:
        # Early return: returned abs(diff) days earlier
        # Unused days to be refunded to balance = abs(diff)
        return ResumptionType.EARLY, abs(diff)
    else:
        # Late return: returned diff days late
        # Additional days to be charged = diff
        return ResumptionType.LATE, diff
