"""FTS services package."""
from modules.fts.services.file_service import (
    archive_file,
    create_file,
    discard_draft,
    edit_draft,
    forward_file,
    return_file,
)

__all__ = [
    "archive_file",
    "create_file",
    "discard_draft",
    "edit_draft",
    "forward_file",
    "return_file",
]
