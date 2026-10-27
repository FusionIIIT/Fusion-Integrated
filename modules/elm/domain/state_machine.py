"""State machine and routing engine for ELM workflows.

Implements all state transitions for new leave, substitute consent gate,
Unit Head review, higher sanction, Director self-sanction (BR-EL-020),
immediate withdrawal (BR-EL-022), cancellation (BR-EL-023),
extension (BR-EL-025), and resumption (BR-EL-027, BR-EL-028).
"""
from datetime import date
from typing import Tuple


def determine_initial_status(has_substitute: bool, is_director: bool = False) -> str:
    """Determine initial status on application submission.

    - BR-EL-020: Director self-sanction rule. When the Director is the applicant,
      the Director-specific self-sanction path replaces the normal route and marks
      the request immediately approved.
    - BR-EL-015: Required substitute consent must be accepted before approval routing continues.
    """
    if is_director:
        return "approved"
    if has_substitute:
        return "pending_substitute"
    return "pending_unit_head"


def process_substitute_action(action: str) -> Tuple[str, str]:
    """Process substitute response (accept or decline).

    Returns (new_substitute_status, new_workflow_status).
    """
    if action == "accept":
        return "accepted", "pending_unit_head"
    elif action == "decline":
        return "declined", "pending_substitute"
    raise ValueError(f"Unknown substitute action: {action}")


def process_unit_head_action(
    category: str,
    action: str,  # "approve", "reject", "recommend", "not_recommend"
    has_establishment_step: bool = False,
) -> Tuple[str, str]:
    """Process Unit Head review according to leave category.

    BR-EL-016: For CL and RH, Unit Head is the final authority.
    BR-EL-017: For SCL, EL, COL, and VL, Unit Head records Recommended or Not Recommended,
    and both continue through the higher-sanction path.
    BR-EL-019: An Establishment step occurs where configured.
    """
    if category in ("CL", "RH"):
        if action == "approve":
            return "recommended", "approved"
        elif action == "reject":
            return "not_recommended", "rejected"
        raise ValueError(f"Unit Head final decision on {category} must be 'approve' or 'reject'.")

    # SCL, EL, COL, VL: proceeds to establishment or higher sanction
    next_stage = "pending_estt" if has_establishment_step else "pending_sanction"
    if action in ("recommend", "approve"):
        return "recommended", next_stage
    elif action in ("not_recommend", "reject"):
        return "not_recommended", next_stage

    raise ValueError(f"Invalid Unit Head action for {category}: {action}")


def process_sanction_action(action: str) -> str:
    """Process final sanctioning authority decision."""
    if action == "approve":
        return "approved"
    elif action == "reject":
        return "rejected"
    raise ValueError(f"Sanctioning authority decision must be 'approve' or 'reject', got {action}")


def can_withdraw(current_status: str) -> bool:
    """Check if request can be withdrawn (BR-EL-022).

    Withdrawal is immediate at any time before final approval.
    """
    pending_statuses = {
        "pending_substitute",
        "pending_unit_head",
        "pending_estt",
        "pending_sanction",
    }
    return current_status in pending_statuses


def can_request_cancellation(current_status: str, start_date: date, today: date) -> bool:
    """Check if approved leave can be cancelled (BR-EL-023).

    Approved leave may be cancelled only before its start date.
    """
    return current_status == "approved" and today < start_date


def can_request_extension(
    current_status: str, category: str, start_date: date, today: date
) -> bool:
    """Check if leave extension can be requested (BR-EL-025, WF-EL-04).

    Extension is available only for ongoing EL/COL/VL after the start date.
    """
    return (
        current_status == "approved"
        and category in ("EL", "COL", "VL")
        and today >= start_date
    )


def can_submit_resumption(
    current_status: str, category: str, start_date: date, today: date
) -> bool:
    """Check if duty resumption can be declared (BR-EL-027, WF-EL-05).

    Formal resumption applies to EL, COL, and VL after leave has commenced.
    """
    return (
        current_status == "approved"
        and category in ("EL", "COL", "VL")
        and today >= start_date
    )
