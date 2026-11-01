"""Domain layer for File Tracking System (FTS).

Pure Python layer containing entities, value objects, business rules,
and state machine logic.
"""
from .entities import AttachmentInfo, CommentRecord, FileComposite, MovementRecord
from .errors import (
    ArchivalNotAllowedError,
    BusinessRuleViolation,
    DraftBoundaryViolationError,
    FileArchivedError,
    FTSDomainError,
    InitialCommentRequiredError,
    InvalidRecipientError,
    InvalidReturnTargetError,
    MovementCommentRequiredError,
    NotFileHolderError,
    SystemAdminOperationalActionBlockedError,
    UnauthorizedFileActionError,
    ValidationError,
)
from .rules import (
    assert_associated_user,
    assert_current_holder,
    assert_operational_actor,
    validate_forward_recipient,
    validate_initial_comment,
    validate_movement_comment,
    validate_return_recipient,
)
from .state_machine import (
    ALLOWED_TRANSITIONS,
    FileLifecycleState,
    MovementType,
    assert_can_archive,
    assert_can_discard_draft,
    assert_can_edit_draft,
    assert_can_forward_or_return,
    assert_can_transition,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "ArchivalNotAllowedError",
    "AttachmentInfo",
    "BusinessRuleViolation",
    "CommentRecord",
    "DraftBoundaryViolationError",
    "FTSDomainError",
    "FileArchivedError",
    "FileComposite",
    "FileLifecycleState",
    "InitialCommentRequiredError",
    "InvalidRecipientError",
    "InvalidReturnTargetError",
    "MovementCommentRequiredError",
    "MovementRecord",
    "MovementType",
    "NotFileHolderError",
    "SystemAdminOperationalActionBlockedError",
    "UnauthorizedFileActionError",
    "ValidationError",
    "assert_associated_user",
    "assert_can_archive",
    "assert_can_discard_draft",
    "assert_can_edit_draft",
    "assert_can_forward_or_return",
    "assert_can_transition",
    "assert_current_holder",
    "assert_operational_actor",
    "validate_forward_recipient",
    "validate_initial_comment",
    "validate_movement_comment",
    "validate_return_recipient",
]

