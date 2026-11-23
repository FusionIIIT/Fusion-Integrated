"""Public contract exposed by File Tracking System to other modules."""

from collections.abc import Sequence
from dataclasses import dataclass

from modules.filetracking.models import TrackedFile
from modules.filetracking.services.files import create_file


@dataclass(frozen=True)
class FileStatusDTO:
    file_id: int
    file_number: str
    subject: str
    status: str
    current_holder_user_id: int | None
    is_archived: bool


def get_file_statuses(file_ids: Sequence[int]) -> list[FileStatusDTO]:
    """Bulk-retrieve statuses for specified file IDs."""
    if not file_ids:
        return []
    files = TrackedFile.objects.filter(id__in=file_ids)
    return [
        FileStatusDTO(
            file_id=f.id,
            file_number=f.file_number,
            subject=f.subject,
            status=f.status,
            current_holder_user_id=f.current_holder_user_id,
            is_archived=f.is_archived,
        )
        for f in files
    ]


def get_files_for_holders(holder_user_ids: Sequence[int]) -> list[FileStatusDTO]:
    """Bulk-retrieve active files currently held by given user IDs."""
    if not holder_user_ids:
        return []
    files = TrackedFile.objects.filter(current_holder_user_id__in=holder_user_ids)
    return [
        FileStatusDTO(
            file_id=f.id,
            file_number=f.file_number,
            subject=f.subject,
            status=f.status,
            current_holder_user_id=f.current_holder_user_id,
            is_archived=f.is_archived,
        )
        for f in files
    ]


def initiate_module_tracking_chain(
    *,
    initiator_user_id: int,
    initiator_designation: str,
    subject: str,
    initial_comment: str,
    recipient_user_id: int,
    recipient_designation: str = "",
    external_reference: str = "",
) -> FileStatusDTO:
    """Inter-module command to initiate a file tracking chain."""
    file = create_file(
        creator_user_id=initiator_user_id,
        creator_designation=initiator_designation,
        subject=subject,
        initial_comment=initial_comment,
        is_draft=False,
        recipient_user_id=recipient_user_id,
        recipient_designation=recipient_designation,
    )
    return FileStatusDTO(
        file_id=file.id,
        file_number=file.file_number,
        subject=file.subject,
        status=file.status,
        current_holder_user_id=file.current_holder_user_id,
        is_archived=file.is_archived,
    )
