"""Pure Python domain exceptions for FTS."""


class FtsDomainError(Exception):
    """Base exception for all FTS domain rules."""


class InvalidStateTransitionError(FtsDomainError):
    """Raised when an illegal lifecycle state transition is attempted."""


class MandatoryCommentMissingError(FtsDomainError):
    """Raised when a file creation, forward, or return lacks a mandatory comment."""


class UnauthorizedFileActionError(FtsDomainError):
    """Raised when an actor is not permitted to act on a file in its current state."""


class InvalidRecipientError(FtsDomainError):
    """Raised when a recipient employee is invalid or missing."""


class CirculatedFileDeletionProhibitedError(FtsDomainError):
    """Raised when deletion of a circulated file is attempted."""


class ArchivedFileModificationProhibitedError(FtsDomainError):
    """Raised when modification or movement of an archived file is attempted."""


class OnlyOwnerMayArchiveError(FtsDomainError):
    """Raised when an actor other than the file owner attempts archival."""


class SystemAdminOperationalActionProhibitedError(FtsDomainError):
    """Raised when a System Admin attempts operational file workflows."""
