class FtsDomainError(ValueError):
    """Custom domain validation exception for FTS rules."""
    pass


def validate_file_creation(comment: str) -> None:
    """Enforces BR-FTS-004: Initial tracking comment is mandatory upon file creation."""
    if not comment or not comment.strip():
        raise FtsDomainError("Initial comment is mandatory when creating a file.")


def validate_movement_action(comment: str, target_user_id: int) -> None:
    """Enforces BR-FTS-006: Movement requires a valid recipient and mandatory comment."""
    if not comment or not comment.strip():
        raise FtsDomainError("A mandatory movement comment is required to forward or return a file.")
    if not target_user_id or target_user_id <= 0:
        raise FtsDomainError("A valid recipient must be specified for file movement.")


def validate_archival(is_owner: bool, is_already_archived: bool) -> None:
    """Enforces BR-FTS-012: Only the original file owner can archive an active file."""
    if is_already_archived:
        raise FtsDomainError("File is already archived.")
    if not is_owner:
        raise FtsDomainError("Only the file owner is authorized to archive this file.")