"""State transitions and workflow engine for ELM (CW-EL-01 to CW-EL-04).

Authoritative rules according to Workflow Specifications v1.6 and BR-EL-016..028.
"""

from __future__ import annotations

from .errors import InvalidStateTransitionError

# Pending pre-final states from which withdrawal is permitted (BR-EL-022, BR-EL-034)
WITHDRAWABLE_STATES: frozenset[str] = frozenset(
    {
        "awaiting_substitute",
        "applicant_action_required",
        "awaiting_unit_head",
        "awaiting_establishment",
        "awaiting_final_sanction",
        "awaiting_director_self_sanction",
        "awaiting_ext_substitute",
        "ext_applicant_action_required",
        "awaiting_ext_unit_head",
        "ext_pending_establishment",
        "ext_pending_final",
    }
)

# States that represent active leave reservations for overlap checks
ACTIVE_LEAVE_STATES: frozenset[str] = frozenset(
    {
        "awaiting_substitute",
        "applicant_action_required",
        "awaiting_unit_head",
        "awaiting_establishment",
        "awaiting_final_sanction",
        "awaiting_director_self_sanction",
        "approved",
        "cancellation_pending_unit_head",
        "cancellation_pending_establishment",
        "cancellation_pending_final",
        "resumption_review_pending",
        "resumption_reviewed",
    }
)


def determine_initial_state(
    substitute_required: bool,
    is_director: bool,
) -> str:
    """Determine initial state on leave application submission (CW-EL-01)."""
    if substitute_required:
        return "awaiting_substitute"
    if is_director:
        return "awaiting_director_self_sanction"
    return "awaiting_unit_head"


def transition_substitute_response(
    current_state: str,
    accepted: bool,
    is_director: bool,
) -> str:
    """Transition after substitute responds (CW-EL-01, CW-EL-03)."""
    if current_state == "awaiting_substitute":
        if accepted:
            return "awaiting_director_self_sanction" if is_director else "awaiting_unit_head"
        return "applicant_action_required"

    if current_state == "awaiting_ext_substitute":
        if accepted:
            return "awaiting_ext_unit_head"
        return "ext_applicant_action_required"

    raise InvalidStateTransitionError(f"Cannot respond as substitute from state '{current_state}'.")


def transition_replacement_substitute(current_state: str) -> str:
    """Transition when applicant nominates a replacement substitute (EL-UC-019)."""
    if current_state == "applicant_action_required":
        return "awaiting_substitute"
    if current_state == "ext_applicant_action_required":
        return "awaiting_ext_substitute"

    raise InvalidStateTransitionError(
        f"Replacement substitute nomination not allowed from state '{current_state}'."
    )


def transition_unit_head_review(
    current_state: str,
    category: str,
    action: str,  # 'approve', 'reject', 'recommend', 'not_recommend'
    establishment_configured: bool = False,
) -> str:
    """Transition when Unit Head reviews request (CW-EL-01, CW-EL-02, CW-EL-03)."""
    # 1. New Leave Processing (CW-EL-01)
    if current_state == "awaiting_unit_head":
        if category in ("CL", "RH"):
            # Unit Head has final authority (BR-EL-016)
            if action == "approve":
                return "approved"
            if action == "reject":
                return "rejected"
            raise InvalidStateTransitionError(
                f"Action '{action}' is invalid for Unit Head final decision on {category}."
            )
        # SCL, EL, COL, VL require higher sanction (BR-EL-017, BR-EL-018)
        if action in ("recommend", "not_recommend"):
            return (
                "awaiting_establishment" if establishment_configured else "awaiting_final_sanction"
            )
        raise InvalidStateTransitionError(
            f"Unit Head must record recommendation ('recommend' or 'not_recommend') for {category}."
        )

    # 2. Approved-Leave Cancellation (CW-EL-02)
    if current_state == "cancellation_pending_unit_head":
        if category in ("CL", "RH"):
            if action == "approve":
                return "cancelled"
            if action == "reject":
                return "approved"
            raise InvalidStateTransitionError(f"Invalid cancellation action '{action}'.")
        if action in ("recommend", "not_recommend"):
            return (
                "cancellation_pending_establishment"
                if establishment_configured
                else "cancellation_pending_final"
            )
        raise InvalidStateTransitionError(f"Invalid recommendation action '{action}'.")

    # 3. Extension (CW-EL-03)
    if current_state == "awaiting_ext_unit_head":
        if action in ("recommend", "not_recommend"):
            return "ext_pending_establishment" if establishment_configured else "ext_pending_final"
        raise InvalidStateTransitionError(f"Invalid extension review action '{action}'.")

    raise InvalidStateTransitionError(
        f"Unit Head review not applicable for state '{current_state}'."
    )


def transition_establishment_routing(current_state: str) -> str:
    """Transition when Establishment routes request (EL-UC-004)."""
    if current_state == "awaiting_establishment":
        return "awaiting_final_sanction"
    if current_state == "cancellation_pending_establishment":
        return "cancellation_pending_final"
    if current_state == "ext_pending_establishment":
        return "ext_pending_final"

    raise InvalidStateTransitionError(
        f"Establishment routing not applicable for state '{current_state}'."
    )


def transition_final_sanction(
    current_state: str,
    action: str,  # 'approve' or 'reject'
) -> str:
    """Transition when final Sanctioning Authority or Director decides."""
    if action not in ("approve", "reject"):
        raise InvalidStateTransitionError(f"Invalid sanction action '{action}'.")

    # New Leave (CW-EL-01)
    if current_state in ("awaiting_final_sanction", "awaiting_director_self_sanction"):
        return "approved" if action == "approve" else "rejected"

    # Cancellation (CW-EL-02)
    if current_state == "cancellation_pending_final":
        return "cancelled" if action == "approve" else "approved"

    # Extension (CW-EL-03): approval posts incremental period; rejection preserves base leave
    if current_state == "ext_pending_final":
        return "approved"

    raise InvalidStateTransitionError(f"Final sanction not applicable for state '{current_state}'.")


def transition_withdrawal(current_state: str) -> str:
    """Immediate withdrawal of pending request (BR-EL-022, BR-EL-034)."""
    if current_state in WITHDRAWABLE_STATES:
        if current_state.startswith(("ext_", "awaiting_ext_")):
            # Original leave remains approved, extension cancelled
            return "approved"
        return "withdrawn"

    raise InvalidStateTransitionError(
        f"Cannot withdraw request from terminal or non-pending state '{current_state}'."
    )
