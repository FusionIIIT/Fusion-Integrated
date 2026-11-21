"""FTS domain validation rules (BR-FTS-001..014, CFR-FTS-001..012)."""
from __future__ import annotations


class FTSValidationError(Exception):
    """Raised when a business rule or validation precondition fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_initial_comment(comment: str | None) -> None:
    """Ensure file creation has a mandatory initial comment (BR-FTS-004)."""
    if not comment or not comment.strip():
        raise FTSValidationError(
            "initial_comment_required",
            "An initial comment is mandatory when creating or saving a file.",
        )


def validate_movement_comment(comment: str | None) -> None:
    """Ensure forward/return actions include a mandatory comment (BR-FTS-006)."""
    if not comment or not comment.strip():
        raise FTSValidationError(
            "movement_comment_required",
            "A comment is mandatory when forwarding or returning a file.",
        )


def validate_forward_recipient(sender_id: int, receiver_id: int) -> None:
    """Ensure recipient is specified and distinct from current sender (BR-FTS-007)."""
    if not receiver_id:
        raise FTSValidationError("recipient_required", "A recipient must be specified.")
    if sender_id == receiver_id:
        raise FTSValidationError(
            "self_forwarding_prohibited",
            "A file cannot be forwarded to yourself.",
        )


def validate_return_recipient(
    current_holder_id: int,
    target_receiver_id: int,
    expected_previous_sender_id: int | None,
) -> None:
    """Ensure returned file targets the immediate previous sender (BR-FTS-007, BW-FTS-03)."""
    if not expected_previous_sender_id:
        raise FTSValidationError(
            "no_previous_sender",
            "File cannot be returned because no previous sender exists in movement history.",
        )
    if target_receiver_id != expected_previous_sender_id:
        raise FTSValidationError(
            "invalid_return_target",
            "A received file can only be returned to its previous sender.",
        )
    if current_holder_id == target_receiver_id:
        raise FTSValidationError(
            "self_return_prohibited",
            "Cannot return file to yourself.",
        )


def validate_owner_archival(owner_id: int, actor_id: int, current_status: str) -> None:
    """Ensure only the file owner can archive a circulating file (BR-FTS-012, AFR-FTS-042)."""
    if actor_id != owner_id:
        raise FTSValidationError(
            "owner_archival_only",
            "Only the file owner is permitted to archive a completed file.",
        )
    if current_status != "circulating":
        raise FTSValidationError(
            "invalid_archival_state",
            f"Only circulating files can be archived; current status is '{current_status}'.",
        )


def validate_operational_role(is_employee: bool, is_system_admin: bool) -> None:
    """Ensure only employees operate files; Admin is governance-only (BR-FTS-001, AFR-FTS-009)."""
    if is_system_admin:
        raise FTSValidationError(
            "admin_operational_forbidden",
            "System Admin cannot perform operational file workflow actions.",
        )
    if not is_employee:
        raise FTSValidationError(
            "employee_required",
            "Only authorized institute employees (faculty/staff) may process files.",
        )
