"""Pure domain validation rules for File Tracking System (framework-free)."""


from modules.filetracking.domain.entities import FileStatus
from modules.filetracking.domain.errors import (
    CommentRequiredError,
    DraftDiscardError,
    FileArchivedError,
    InvalidAttachmentError,
    InvalidRecipientError,
    StateTransitionError,
)

DEFAULT_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def validate_initial_comment(comment: str | None) -> None:
    """Validate mandatory initial user comment on file creation (BR-FTS-004)."""
    if not comment or not comment.strip():
        raise CommentRequiredError(
            "An initial mandatory comment is required to create a new file."
        )


def validate_movement_comment(comment: str | None) -> None:
    """Validate mandatory movement comment on forward and return (BR-FTS-006)."""
    if not comment or not comment.strip():
        raise CommentRequiredError(
            "A movement comment is mandatory when forwarding or returning a file."
        )


def validate_forward_recipient(sender_user_id: int, recipient_user_id: int) -> None:
    """Validate that the forward recipient is not the sender themselves (BR-FTS-007)."""
    if sender_user_id == recipient_user_id:
        raise InvalidRecipientError(
            "Self-forwarding is prohibited. You cannot forward a file to yourself."
        )


def validate_return_recipient(expected_sender_id: int, target_recipient_id: int) -> None:
    """Validate returning a file is strictly to immediate previous sender (BR-FTS-007)."""
    if expected_sender_id != target_recipient_id:
        raise InvalidRecipientError(
            "A received file can only be returned to the immediate previous sender."
        )


def validate_draft_for_discard(status: str) -> None:
    """Validate that file is in draft state before discard (BR-FTS-005)."""
    if status != FileStatus.DRAFT:
        raise DraftDiscardError(
            "Only uncirculated draft files may be discarded. Circulated files cannot be deleted."
        )


def validate_file_not_archived(status: str) -> None:
    """Validate that the file is not already archived (BR-FTS-012)."""
    if status == FileStatus.ARCHIVED:
        raise FileArchivedError(
            "The file is archived and cannot receive further actions or comments."
        )


def validate_owner_for_archive(owner_user_id: int, actor_user_id: int) -> None:
    """Validate that only the original creator/owner can archive the file (BR-FTS-012)."""
    if owner_user_id != actor_user_id:
        raise StateTransitionError(
            "Only the file owner (creator) is authorized to archive this file."
        )


def validate_attachment(
    file_name: str,
    file_size: int,
    mime_type: str,
    max_bytes: int = DEFAULT_MAX_ATTACHMENT_BYTES,
) -> None:
    """Validate attachment constraints."""
    if file_size <= 0:
        raise InvalidAttachmentError("Attachment file cannot be empty.")
    if file_size > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise InvalidAttachmentError(f"Attachment exceeds maximum allowed size of {limit_mb}MB.")
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        raise InvalidAttachmentError(f"Attachment MIME type '{mime_type}' is not supported.")
