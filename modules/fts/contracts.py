"""FTS public contracts for inter-module integration."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from modules.fts.models.files import File
from modules.fts.services.files import create_file


@dataclass(frozen=True)
class FileStatusDTO:
    file_id: int
    reference_number: str
    status: str
    current_holder_user_id: int
    current_holder_username: str


@dataclass(frozen=True)
class FileSummaryDTO:
    file_id: int
    reference_number: str
    subject: str
    status: str


def get_file_statuses(file_ids: Sequence[int]) -> dict[int, FileStatusDTO]:
    """Returns status DTOs for the requested file IDs in a single batch query."""
    ids = {int(fid) for fid in file_ids if fid is not None}
    if not ids:
        return {}
    files = File.objects.filter(id__in=ids)
    return {
        f.id: FileStatusDTO(
            file_id=f.id,
            reference_number=f.reference_number,
            status=f.status,
            current_holder_user_id=f.current_holder_user_id,
            current_holder_username=f.current_holder_username,
        )
        for f in files
    }


def get_files_for_users(user_ids: Sequence[int]) -> dict[int, list[FileSummaryDTO]]:
    """Returns summaries of files held by the requested user IDs."""
    ids = {int(uid) for uid in user_ids if uid is not None}
    if not ids:
        return {}
    files = File.objects.filter(current_holder_user_id__in=ids).exclude(status="DISCARDED")
    result: dict[int, list[FileSummaryDTO]] = {uid: [] for uid in ids}
    for f in files:
        result[f.current_holder_user_id].append(
            FileSummaryDTO(
                file_id=f.id,
                reference_number=f.reference_number,
                subject=f.subject,
                status=f.status,
            )
        )
    return result


def create_module_tracked_file(
    *,
    subject: str,
    description: str = "",
    comment_text: str,
    creator_user_id: int,
    creator_username: str,
    creator_role: str,
    recipient_user_id: int,
    recipient_username: str,
    recipient_role: str,
    attachments: list[dict[str, Any]] | None = None,
) -> FileStatusDTO:
    """Creates and immediately circulates an institutional file for another module."""
    file_obj = create_file(
        subject=subject,
        description=description,
        comment_text=comment_text,
        actor_user_id=creator_user_id,
        actor_username=creator_username,
        actor_role=creator_role,
        actor_kind="faculty",
        is_draft=False,
        recipient_user_id=recipient_user_id,
        recipient_username=recipient_username,
        recipient_role=recipient_role,
        attachments=attachments,
    )
    return FileStatusDTO(
        file_id=file_obj.id,
        reference_number=file_obj.reference_number,
        status=file_obj.status,
        current_holder_user_id=file_obj.current_holder_user_id,
        current_holder_username=file_obj.current_holder_username,
    )
