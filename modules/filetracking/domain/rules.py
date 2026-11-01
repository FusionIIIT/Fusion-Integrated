"""Domain business rules for File Tracking System (FTS).

Pure Python — no framework imports allowed in domain/.
Implements BR-FTS-001 through BR-FTS-014.
"""
from collections.abc import Sequence

from .errors import (
    InitialCommentRequiredError,
    InvalidRecipientError,
    InvalidReturnTargetError,
    MovementCommentRequiredError,
    NotFileHolderError,
    SystemAdminOperationalActionBlockedError,
    UnauthorizedFileActionError,
)


def validate_initial_comment(comment: str | None) -> str:
    """BR-FTS-004 / AFR-FTS-012: Initial comment is mandatory for file creation."""
    if not comment or not comment.strip():
        raise InitialCommentRequiredError(
            "A new FTS file requires an initial mandatory comment (BR-FTS-004)."
        )
    return comment.strip()


def validate_movement_comment(comment: str | None) -> str:
    """BR-FTS-006 / AFR-FTS-022: Every movement action requires a mandatory comment."""
    if not comment or not comment.strip():
        raise MovementCommentRequiredError(
            "Every file-movement action requires a mandatory comment (BR-FTS-006)."
        )
    return comment.strip()


def assert_operational_actor(is_system_admin: bool) -> None:
    """BR-FTS-001 / AFR-FTS-009: System Admin has no operational involvement in file workflows."""
    if is_system_admin:
        raise SystemAdminOperationalActionBlockedError(
            "System Admin cannot perform operational file workflow actions on behalf of "
            "Institute Employees (BR-FTS-001, AFR-FTS-009)."
        )


def assert_current_holder(actor_user_id: int, current_holder_id: int) -> None:
    """Ensure acting user currently holds the file before forwarding or returning."""
    if actor_user_id != current_holder_id:
        raise NotFileHolderError(
            f"User {actor_user_id} is not the current holder of the file ({current_holder_id}). "
            "Only the holder can forward or return it."
        )


def validate_forward_recipient(recipient_user_id: int, sender_user_id: int) -> None:
    """BR-FTS-007 / AFR-FTS-020, AFR-FTS-021: Recipient must be an employee and not self."""
    if recipient_user_id <= 0:
        raise InvalidRecipientError(
            "A valid recipient Institute Employee must be selected (BR-FTS-007)."
        )
    if recipient_user_id == sender_user_id:
        raise InvalidRecipientError("Cannot forward a file to oneself.")


def validate_return_recipient(recipient_user_id: int, previous_sender_id: int | None) -> None:
    """BR-FTS-007 / AFR-FTS-025: Returned file must be routed to previous sender."""
    if not previous_sender_id:
        raise InvalidReturnTargetError("File has no previous sender to return to (BR-FTS-007).")
    if recipient_user_id != previous_sender_id:
        raise InvalidReturnTargetError(
            f"Returned file must be routed to previous sender ({previous_sender_id}), "
            f"got {recipient_user_id} (BR-FTS-007)."
        )


def assert_associated_user(user_id: int, associated_user_ids: Sequence[int]) -> None:
    """BR-FTS-009 / AFR-FTS-049: File exposed only to associated users."""
    if user_id not in associated_user_ids:
        raise UnauthorizedFileActionError(
            f"User {user_id} is not associated with this file and cannot access it (BR-FTS-009)."
        )

