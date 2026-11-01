"""Domain errors for File Tracking System (FTS).

Pure Python — no framework imports allowed in domain/.
"""


class FTSDomainError(Exception):
    """Base domain exception for FTS."""


class ValidationError(FTSDomainError):
    """Raised when an entity fails validation constraints."""


class BusinessRuleViolation(FTSDomainError):
    """Raised when a file tracking business rule is violated."""


class InitialCommentRequiredError(ValidationError):
    """BR-FTS-004: A new FTS file requires an initial mandatory user comment."""


class MovementCommentRequiredError(ValidationError):
    """BR-FTS-006: Every file-movement action requires a mandatory comment."""


class DraftBoundaryViolationError(BusinessRuleViolation):
    """BR-FTS-005: Draft operations permitted only pre-circulation; cannot discard circulated files.
    """


class UnauthorizedFileActionError(BusinessRuleViolation):
    """BR-FTS-001, BR-FTS-010: Action not permitted by role, authorization or state."""


class SystemAdminOperationalActionBlockedError(BusinessRuleViolation):
    """BR-FTS-001, AFR-FTS-009: System Admin cannot perform operational file workflow actions."""


class InvalidRecipientError(BusinessRuleViolation):
    """BR-FTS-007: Recipient must be a valid institute employee."""


class InvalidReturnTargetError(BusinessRuleViolation):
    """BR-FTS-007: Received file can only be returned to the previous sender."""


class ArchivalNotAllowedError(BusinessRuleViolation):
    """BR-FTS-012: Only the file owner may archive a completed circulated file."""


class FileArchivedError(BusinessRuleViolation):
    """BR-FTS-012: Archived files cannot be modified or forwarded further."""


class NotFileHolderError(BusinessRuleViolation):
    """A user who is not the current holder cannot forward or return the file."""

