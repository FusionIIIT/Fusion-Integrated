"""Fusion Clean Architecture - File Tracking System (FTS) Domain Workflow Logic.

This module is strictly pure Python: zero imports of Django, DRF, or database models.
It encapsulates validation rules, status transitions, and business invariant checks.
"""

from typing import Final

# --- Status Constants ---
STATUS_DRAFT: Final[str] = "draft"
STATUS_IN_TRANSIT: Final[str] = "in_transit"
STATUS_RECEIVED: Final[str] = "received"
STATUS_RETURNED: Final[str] = "returned"
STATUS_ARCHIVED: Final[str] = "archived"

VALID_STATUSES: Final[frozenset[str]] = frozenset(
    {STATUS_DRAFT, STATUS_IN_TRANSIT, STATUS_RECEIVED, STATUS_RETURNED, STATUS_ARCHIVED}
)

# --- Action Constants ---
ACTION_CREATED: Final[str] = "created"
ACTION_FORWARDED: Final[str] = "forwarded"
ACTION_RETURNED: Final[str] = "returned"
ACTION_ARCHIVED: Final[str] = "archived"

VALID_ACTIONS: Final[frozenset[str]] = frozenset(
    {ACTION_CREATED, ACTION_FORWARDED, ACTION_RETURNED, ACTION_ARCHIVED}
)

# --- Priority Constants ---
PRIORITY_LOW: Final[str] = "low"
PRIORITY_MEDIUM: Final[str] = "medium"
PRIORITY_HIGH: Final[str] = "high"
PRIORITY_URGENT: Final[str] = "urgent"

VALID_PRIORITIES: Final[frozenset[str]] = frozenset(
    {PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_URGENT}
)


def validate_initial_file_data(
    subject: str,
    initial_comment: str,
    priority: str = PRIORITY_MEDIUM,
    category: str = "general",
) -> dict[str, str]:
    """Validates initial file creation parameters per BR-FTS-003 and BR-FTS-004.

    :param subject: File title/subject.
    :param initial_comment: Mandatory opening comment/remark.
    :param priority: Priority level (low, medium, high, urgent).
    :param category: File category.
    :return: Cleaned dictionary with validated fields.
    :raises ValueError: If subject or initial_comment is empty, or priority invalid.
    """
    clean_subject = subject.strip()
    if not clean_subject:
        raise ValueError("File subject cannot be empty.")

    clean_comment = initial_comment.strip()
    if not clean_comment:
        raise ValueError("Initial comment is mandatory and cannot be empty (BR-FTS-004).")

    clean_priority = priority.strip().lower()
    if clean_priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority '{priority}'. Allowed: {sorted(VALID_PRIORITIES)}")

    clean_category = category.strip() or "general"

    return {
        "subject": clean_subject,
        "initial_comment": clean_comment,
        "priority": clean_priority,
        "category": clean_category,
    }


def generate_file_uin(prefix: str, year: int, sequence_num: int) -> str:
    """Generates an institutional standard Unique Identification Number (UIN) for a file.

    Example: 'FTS-2024-0001'.
    """
    if sequence_num <= 0:
        raise ValueError("Sequence number must be a positive integer.")
    clean_prefix = prefix.strip().upper() or "FTS"
    return f"{clean_prefix}-{year}-{sequence_num:04d}"


def can_forward_file(
    current_status: str,
    sender_id: str,
    current_holder_id: str,
    receiver_id: str,
    comment: str,
) -> tuple[bool, str]:
    """Verifies eligibility to send/forward a file per BR-FTS-006 and BR-FTS-007.

    :param current_status: Current status of the file.
    :param sender_id: ID of the user attempting to forward.
    :param current_holder_id: ID of the current custodian of the file.
    :param receiver_id: ID of the designated recipient.
    :param comment: Mandatory forwarding comment.
    :return: Tuple of (is_valid, error_message).
    """
    if current_status == STATUS_ARCHIVED:
        return False, "Archived files are terminal and cannot be forwarded (BR-FTS-012)."

    if sender_id != current_holder_id:
        return False, "Only the current custodian can forward this file (BR-FTS-001)."

    if sender_id == receiver_id:
        return False, "Cannot forward a file to yourself."

    if not comment or not comment.strip():
        return False, "Movement comment is mandatory when forwarding a file (BR-FTS-006)."

    return True, ""


def can_return_file(
    current_status: str,
    sender_id: str,
    current_holder_id: str,
    previous_senders: list[str],
    comment: str,
) -> tuple[bool, str]:
    """Verifies eligibility to return a file to a previous sender per BR-FTS-007.

    :param current_status: Current status of the file.
    :param sender_id: ID of the user attempting the return.
    :param current_holder_id: ID of the current custodian.
    :param previous_senders: Ordered list of previous sender IDs in movement chain.
    :param comment: Mandatory return comment.
    :return: Tuple of (is_valid, error_message).
    """
    if current_status == STATUS_DRAFT:
        return False, "Draft files cannot be returned."

    if current_status == STATUS_ARCHIVED:
        return False, "Archived files cannot be returned."

    if sender_id != current_holder_id:
        return False, "Only the current custodian can return this file."

    if not previous_senders:
        return False, "No previous sender in movement chain to return to (BR-FTS-007)."

    if not comment or not comment.strip():
        return False, "Movement comment is mandatory when returning a file (BR-FTS-006)."

    return True, ""


def can_archive_file(
    current_status: str,
    user_id: str,
    creator_id: str,
    current_holder_id: str,
) -> tuple[bool, str]:
    """Verifies eligibility to archive a file per BR-FTS-012.

    :param current_status: Current status of the file.
    :param user_id: ID of the user requesting archival.
    :param creator_id: Originator of the file.
    :param current_holder_id: Current custodian of the file.
    :return: Tuple of (is_valid, error_message).
    """
    if current_status == STATUS_ARCHIVED:
        return False, "File is already archived."

    if current_status == STATUS_DRAFT:
        return False, "Draft files cannot be archived; discard the draft instead."

    if user_id not in {creator_id, current_holder_id}:
        return False, "Only the creator or current holder can archive this file (BR-FTS-012)."

    return True, ""


def can_edit_draft(current_status: str, user_id: str, creator_id: str) -> tuple[bool, str]:
    """Verifies eligibility to edit or discard a draft per BR-FTS-005."""
    if current_status != STATUS_DRAFT:
        return False, "Only files in draft status can be modified or discarded (BR-FTS-005)."

    if user_id != creator_id:
        return False, "Only the file creator can edit or discard a draft."

    return True, ""
