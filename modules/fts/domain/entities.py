"""Pure Python domain entities and validation rules for FTS."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from modules.fts.domain.errors import (
    InvalidRecipientError,
    MandatoryCommentMissingError,
    OnlyOwnerMayArchiveError,
    SystemAdminOperationalActionProhibitedError,
)


@dataclass(frozen=True)
class FileDTO:
    id: int
    reference_number: str
    subject: str
    description: str
    status: str
    owner_user_id: int
    owner_username: str
    owner_role: str
    current_holder_user_id: int
    current_holder_username: str
    current_holder_role: str


@dataclass(frozen=True)
class MovementRecordDTO:
    id: int
    sequence: int
    movement_type: str
    from_user_id: int
    from_username: str
    from_role: str
    to_user_id: int
    to_username: str
    to_role: str
    comment_text: str
    attachments: tuple[dict[str, Any], ...]


def validate_mandatory_comment(comment_text: str | None) -> str:
    """Enforces non-empty mandatory comments at file creation and movement."""
    if not comment_text or not comment_text.strip():
        raise MandatoryCommentMissingError("A non-empty comment is required for this file action.")
    return comment_text.strip()


def validate_recipient(to_user_id: int | None) -> int:
    """Enforces a valid positive recipient user ID."""
    if to_user_id is None or to_user_id <= 0:
        raise InvalidRecipientError("A valid recipient Institute Employee must be selected.")
    return to_user_id


def validate_owner_archival(owner_user_id: int, actor_user_id: int) -> None:
    """Enforces that only the file owner may archive a circulated file."""
    if owner_user_id != actor_user_id:
        raise OnlyOwnerMayArchiveError("Only the file owner may archive a completed file.")


def validate_employee_operational_actor(actor_kind: str | None, is_admin_actor: bool) -> None:
    """Enforces that operational file actions are performed by employees, not admin."""
    if is_admin_actor:
        raise SystemAdminOperationalActionProhibitedError(
            "System Admin cannot perform operational file workflows."
        )
    if actor_kind not in ("faculty", "staff"):
        raise SystemAdminOperationalActionProhibitedError(
            "Only faculty and staff Institute Employees may perform operational file actions."
        )
