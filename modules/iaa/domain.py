"""PURE PYTHON. No Django import — CI fails the build on one. BR logic lives here."""


def check_segregation_of_duties(creator_id, actor_id):
    """BR-001: a creator/claimant must not approve their own item."""
    if creator_id == actor_id:
        raise ValueError("Creator cannot approve their own request")


def check_submission_completeness(fields, required_fields, is_draft):
    """BR-101: mandatory fields required on formal submit, not on Draft save."""
    if is_draft:
        return
    missing = [f for f in required_fields if not fields.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")


def check_budget_available(amount, available_budget):
    """BR-102: returns True if sufficient; caller flags an anomaly if not."""
    return amount <= available_budget


def more_approval_levels_required(current_level, levels_required):
    """BR-002: whether another configured approval level remains."""
    return current_level < levels_required


def is_high_value(amount, threshold):
    """BR-202: configured high-value criterion for TA claims."""
    return amount >= threshold


def require_remarks(remarks):
    """BR-005: every approve/reject decision must carry remarks."""
    if not remarks or not remarks.strip():
        raise ValueError("Remarks are required for an approval decision")


def can_close_observation(status):
    """BR-302: only a Responded observation may be closed."""
    if status != "RESPONDED":
        raise ValueError("Only a Responded observation can be closed")
