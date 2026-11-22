"""Domain entities and value objects for File Tracking System (framework-free)."""

from dataclasses import dataclass, field
from datetime import datetime


class FileStatus:
    DRAFT = "draft"
    CIRCULATING = "circulating"
    ARCHIVED = "archived"

    ALL = {DRAFT, CIRCULATING, ARCHIVED}


class FileEvent:
    CREATE_DRAFT = "create_draft"
    SUBMIT_INITIAL = "submit_initial"
    UPDATE_DRAFT = "update_draft"
    DISCARD_DRAFT = "discard_draft"
    FORWARD = "forward"
    RETURN = "return"
    ARCHIVE = "archive"


class MovementAction:
    CREATED = "created"
    FORWARDED = "forwarded"
    RETURNED = "returned"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class FileAttachmentDTO:
    id: int | None
    file_id: int
    movement_id: int | None
    uploaded_by_user_id: int
    uploader_designation: str
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    created_at: datetime | None = None


@dataclass(frozen=True)
class FileMovementDTO:
    id: int | None
    file_id: int
    sequence_number: int
    action: str
    sender_user_id: int
    sender_designation: str
    receiver_user_id: int
    receiver_designation: str
    comment: str
    created_at: datetime | None = None
    attachments: list[FileAttachmentDTO] = field(default_factory=list)


@dataclass(frozen=True)
class TrackedFileDTO:
    id: int | None
    file_number: str
    subject: str
    description: str
    status: str
    created_by_user_id: int
    creator_designation: str
    current_holder_user_id: int | None
    current_holder_designation: str | None
    is_archived: bool
    archived_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    movements: list[FileMovementDTO] = field(default_factory=list)


@dataclass(frozen=True)
class FileAuditDTO:
    id: int | None
    file_id: int | None
    action: str
    actor_user_id: int
    actor_designation: str
    payload: dict
    ip_address: str | None = None
    created_at: datetime | None = None
