"""Fusion Clean Architecture - File Tracking System (FTS) Archival Service.

Implements FTS-UC-007 (Archive Completed File) and enforces BR-FTS-012.
"""

from django.db import transaction

from modules.fts.domain.workflow import (
    ACTION_ARCHIVED,
    STATUS_ARCHIVED,
    can_archive_file,
)
from modules.fts.models import FTSComment, FTSFile, FTSMovement


@transaction.atomic
def archive_file(
    file_id: int,
    user_id: str,
    user_role: str,
    remarks: str,
) -> dict:
    """Closes and archives a file, making it permanently terminal and read-only (BR-FTS-012).

    :param file_id: Primary key of the file.
    :param user_id: Employee ID requesting archival.
    :param user_role: Role of the employee.
    :param remarks: Mandatory archival remark.
    :return: Summary dictionary confirming archival.
    """
    try:
        file_obj = FTSFile.objects.select_for_update().get(id=file_id)
    except FTSFile.DoesNotExist as e:
        raise ValueError("File not found.") from e

    clean_remarks = remarks.strip()
    if not clean_remarks:
        raise ValueError("Archival remark is mandatory.")

    # Domain guard
    allowed, msg = can_archive_file(
        current_status=file_obj.status,
        user_id=user_id,
        creator_id=file_obj.creator_id,
        current_holder_id=file_obj.current_holder_id,
    )
    if not allowed:
        raise PermissionError(msg)

    # 1. Update file status
    file_obj.status = STATUS_ARCHIVED
    file_obj.save()

    # 2. Record movement
    movement = FTSMovement.objects.create(
        file=file_obj,
        from_user_id=user_id,
        from_role=user_role,
        to_user_id=user_id,
        to_role=user_role,
        action=ACTION_ARCHIVED,
    )

    # 3. Record closing comment
    FTSComment.objects.create(
        file=file_obj,
        movement=movement,
        author_id=user_id,
        author_role=user_role,
        remarks=clean_remarks,
    )

    return {
        "file_id": file_obj.id,
        "uin": file_obj.uin,
        "status": file_obj.status,
        "archived_by": user_id,
    }
