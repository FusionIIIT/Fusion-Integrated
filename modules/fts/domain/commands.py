import uuid
from datetime import datetime

from .states import FileStatus


def create_file(
        owner_id: str,
        initial_comment: str,
        attachment_urls: list[str] | None = None
    ) -> dict:

    if not initial_comment:
        raise ValueError("Initial comment is mandatory.")

    file_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    return {
        "file_id": file_id,
        "owner_id": owner_id,
        "status": FileStatus.DRAFT.value,
        "initial_comment": initial_comment,
        "attachment_urls": attachment_urls or [],
        "created_at": created_at,
    }


def edit_draft(
        current_status: str,
        new_comment: str,
        new_attachment_urls: list[str] | None = None
    ) -> dict:

    if current_status != FileStatus.DRAFT.value:
        raise ValueError("Can only edit a draft file.")

    if not new_comment:
        raise ValueError("Comment cannot be empty.")

    updated_at = datetime.now().isoformat()

    return {
        "new_comment": new_comment,
        "new_attachment_urls": new_attachment_urls or [],
        "updated_at": updated_at,
    }


def discard_draft(current_status: str) -> None:
    if current_status != FileStatus.DRAFT.value:
        raise ValueError("Can only discard a draft file.")

    return


def forward_file(
        current_status: str,
        sender_id: str,
        receiver_id: str,
        movement_comment: str,
        attachment_urls: list[str] | None = None
    ) -> dict:

    if current_status in [FileStatus.ARCHIVED.value, FileStatus.DISCARDED.value]:
        raise ValueError("Cannot forward an archived or discarded file.")

    if not movement_comment:
        raise ValueError("Movement comment is mandatory.")

    created_at = datetime.now().isoformat()

    return {
        "movement_type": "FORWARD",
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "movement_comment": movement_comment,
        "attachment_urls": attachment_urls or [],
        "created_at": created_at,
    }


def return_file(
        current_status: str,
        sender_id: str,
        receiver_id: str,
        movement_comment: str,
        attachment_urls: list[str] | None = None
    ) -> dict:

    if current_status != FileStatus.CIRCULATED.value:
        raise ValueError("Can only return a circulated file.")

    if not movement_comment:
        raise ValueError("Movement comment is mandatory.")

    created_at = datetime.now().isoformat()

    return {
        "movement_type": "RETURN",
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "movement_comment": movement_comment,
        "attachment_urls": attachment_urls or [],
        "created_at": created_at,
    }


def archive_file(current_status: str, owner_id: str, actor_id: str) -> dict:
    if current_status == FileStatus.ARCHIVED.value:
        raise ValueError("File is already archived.")
    if current_status == FileStatus.DRAFT.value:
        raise ValueError("Cannot archive a draft file. File must be circulated first.")
    if owner_id != actor_id:
        raise ValueError("Only the file owner can archive the file.")

    archived_at = datetime.now().isoformat()

    return {
        "new_status": FileStatus.ARCHIVED.value,
        "archived_at": archived_at,
    }
