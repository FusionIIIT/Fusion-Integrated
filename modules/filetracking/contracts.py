"""Public inter-module API for File Tracking System (FTS).

Other modules may import ONLY this file from modules.filetracking.
Enforces BR-FTS-014, FTS-UC-010, AFR-FTS-067..072.
All getters take plural sequences to prevent N+1 queries.
"""
from collections.abc import Sequence
from dataclasses import dataclass

from modules.filetracking.models import TrackedFile
from modules.filetracking.services.files import (
    create_draft,
    forward_file,
)


@dataclass(frozen=True)
class FileTrackingStatusDTO:
    id: int
    file_code: str
    subject: str
    status: str
    owner_user_id: int
    current_holder_user_id: int
    current_holder_role: str
    source_module: str
    external_reference: str


def get_file_tracking_statuses(file_ids: Sequence[int]) -> dict[int, FileTrackingStatusDTO]:
    """Plural getter: retrieve current status for multiple files (AFR-FTS-069)."""
    rows = TrackedFile.objects.filter(pk__in=file_ids)
    return {
        row.id: FileTrackingStatusDTO(
            id=row.id,
            file_code=row.file_code,
            subject=row.subject,
            status=row.status,
            owner_user_id=row.owner_user_id,
            current_holder_user_id=row.current_holder_user_id,
            current_holder_role=row.current_holder_role,
            source_module=row.source_module,
            external_reference=row.external_reference,
        )
        for row in rows
    }


def get_files_by_external_references(
    external_references: Sequence[str],
) -> dict[str, FileTrackingStatusDTO]:
    """Plural getter: retrieve tracking status by external module references."""
    rows = TrackedFile.objects.filter(external_reference__in=external_references)
    return {
        row.external_reference: FileTrackingStatusDTO(
            id=row.id,
            file_code=row.file_code,
            subject=row.subject,
            status=row.status,
            owner_user_id=row.owner_user_id,
            current_holder_user_id=row.current_holder_user_id,
            current_holder_role=row.current_holder_role,
            source_module=row.source_module,
            external_reference=row.external_reference,
        )
        for row in rows
    }


def create_module_tracked_file(
    source_module: str,
    external_reference: str,
    subject: str,
    description: str,
    creator_user_id: int,
    creator_role: str,
    initial_comment: str,
) -> FileTrackingStatusDTO:
    """Create a tracked file on behalf of another module (FTS-UC-010, BR-FTS-014)."""
    tracked_file = create_draft(
        subject=subject,
        description=description,
        creator_user_id=creator_user_id,
        creator_role=creator_role,
        initial_comment=initial_comment,
        source_module=source_module,
        external_reference=external_reference,
    )
    return FileTrackingStatusDTO(
        id=tracked_file.id,
        file_code=tracked_file.file_code,
        subject=tracked_file.subject,
        status=tracked_file.status,
        owner_user_id=tracked_file.owner_user_id,
        current_holder_user_id=tracked_file.current_holder_user_id,
        current_holder_role=tracked_file.current_holder_role,
        source_module=tracked_file.source_module,
        external_reference=tracked_file.external_reference,
    )


def forward_module_tracked_file(
    file_id: int,
    sender_user_id: int,
    sender_role: str,
    receiver_user_id: int,
    receiver_role: str,
    comment: str,
) -> None:
    """Advance a module-integrated approval chain / file movement (AFR-FTS-068)."""
    forward_file(
        file_id=file_id,
        sender_user_id=sender_user_id,
        sender_role=sender_role,
        receiver_user_id=receiver_user_id,
        receiver_role=receiver_role,
        comment=comment,
    )
