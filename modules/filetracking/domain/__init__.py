"""Domain package for File Tracking System (pure Python, framework-free)."""

from modules.filetracking.domain.entities import (
    FileAttachmentDTO,
    FileAuditDTO,
    FileEvent,
    FileMovementDTO,
    FileStatus,
    MovementAction,
    TrackedFileDTO,
)
from modules.filetracking.domain.errors import (
    AuthorizationError,
    CommentRequiredError,
    DomainValidationError,
    DraftDiscardError,
    FileArchivedError,
    FTSDomainError,
    InvalidAttachmentError,
    InvalidRecipientError,
    ResourceNotFoundError,
    StateTransitionError,
)
from modules.filetracking.domain.rules import (
    validate_attachment,
    validate_draft_for_discard,
    validate_file_not_archived,
    validate_forward_recipient,
    validate_initial_comment,
    validate_movement_comment,
    validate_owner_for_archive,
    validate_return_recipient,
)
from modules.filetracking.domain.state_machine import (
    can_transition,
    get_next_state,
)

__all__ = [
    "AuthorizationError",
    "CommentRequiredError",
    "DomainValidationError",
    "DraftDiscardError",
    "FTSDomainError",
    "FileArchivedError",
    "FileAttachmentDTO",
    "FileAuditDTO",
    "FileEvent",
    "FileMovementDTO",
    "FileStatus",
    "InvalidAttachmentError",
    "InvalidRecipientError",
    "MovementAction",
    "ResourceNotFoundError",
    "StateTransitionError",
    "TrackedFileDTO",
    "can_transition",
    "get_next_state",
    "validate_attachment",
    "validate_draft_for_discard",
    "validate_file_not_archived",
    "validate_forward_recipient",
    "validate_initial_comment",
    "validate_movement_comment",
    "validate_owner_for_archive",
    "validate_return_recipient",
]
