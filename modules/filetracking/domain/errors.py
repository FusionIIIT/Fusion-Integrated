"""Domain errors for File Tracking System (framework-free)."""


class FTSDomainError(Exception):
    """Base exception for all domain-level errors."""

    def __init__(self, message: str, code: str = "fts_domain_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class DomainValidationError(FTSDomainError):
    def __init__(self, message: str, code: str = "validation_error"):
        super().__init__(message, code=code)


class CommentRequiredError(DomainValidationError):
    def __init__(self, message: str = "A non-empty comment is required for this action."):
        super().__init__(message, code="comment_required")


class InvalidRecipientError(DomainValidationError):
    def __init__(self, message: str = "Invalid recipient specified."):
        super().__init__(message, code="invalid_recipient")


class InvalidAttachmentError(DomainValidationError):
    def __init__(self, message: str = "Attachment exceeds maximum size or invalid format."):
        super().__init__(message, code="invalid_attachment")


class StateTransitionError(FTSDomainError):
    def __init__(
        self,
        message: str = "Illegal lifecycle transition requested.",
        code: str = "illegal_state_transition",
    ):
        super().__init__(message, code=code)


class DraftDiscardError(StateTransitionError):
    def __init__(self, message: str = "Circulated files cannot be discarded as drafts."):
        super().__init__(message, code="cannot_discard_circulated_file")


class FileArchivedError(StateTransitionError):
    def __init__(
        self,
        message: str = "Archived files are permanently closed and cannot be modified or forwarded.",
    ):
        super().__init__(message, code="file_already_archived")


class AuthorizationError(FTSDomainError):
    def __init__(self, message: str = "You are not authorized to perform this action."):
        super().__init__(message, code="unauthorized_action")


class ResourceNotFoundError(FTSDomainError):
    def __init__(self, message: str = "Requested file resource was not found."):
        super().__init__(message, code="resource_not_found")
