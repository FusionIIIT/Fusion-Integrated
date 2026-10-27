"""State machine and routing engine for ELM workflows."""
from datetime import date
from typing import Tuple


def determine_initial_status(has_substitute: bool) -> str:
    """Determine initial status on application submission.

    BR-EL-015: Required substitute consent must be accepted before approval routing continues.
    """
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
) -> Tuple[str, str]:
    """Process Unit Head review according to leave category.

    BR-EL-016: For CL and RH, Unit Head is the final authority.
    BR-EL-017: For SCL, EL, COL, and VL, Unit Head records Recommended or Not Recommended,
    and both continue through the higher-sanction path.
    """
    if category in ("CL", "RH"):
        if action == "approve":
            return "recommended", "approved"
        elif action == "reject":
            return "not_recommended", "rejected"
        raise ValueError(f"Unit Head final decision on {category} must be 'approve' or 'reject'.")

    # SCL, EL, COL, VL: proceeds to higher sanction
    if action in ("recommend", "approve"):
        return "recommended", "pending_sanction"
    elif action in ("not_recommend", "reject"):
        return "not_recommended", "pending_sanction"

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
