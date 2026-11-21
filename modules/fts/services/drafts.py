"""Fusion Clean Architecture - File Tracking System (FTS) Draft Services.

Implements FTS-UC-001 (Create New File Draft) and FTS-UC-002 (Edit or Discard Draft File).
Enforces business rules BR-FTS-003, BR-FTS-004, and BR-FTS-005.
"""

from datetime import datetime

from django.db import transaction

from modules.fts.domain.workflow import (
    ACTION_CREATED,
    STATUS_DRAFT,
    can_edit_draft,
    generate_file_uin,
    validate_initial_file_data,
)
from modules.fts.models import FTSComment, FTSFile, FTSMovement


@transaction.atomic
def create_file_draft(
    creator_id: str,
    creator_role: str,
    subject: str,
    initial_comment: str,
    priority: str = "medium",
    category: str = "general",
    description: str = "",
) -> dict:
    """Creates a new FTS file in Draft state with mandatory initial comment (FTS-UC-001).

    :param creator_id: Employee ID creating the file.
    :param creator_role: Role under which the file is created.
    :param subject: Title of the file.
    :param initial_comment: Mandatory initial remark.
    :param priority: Priority level.
    :param category: File category.
    :param description: Optional file body description.
    :return: Created file summary dictionary.
    """
    # 1. Domain validation (BR-FTS-003, BR-FTS-004)
    cleaned = validate_initial_file_data(
        subject=subject,
        initial_comment=initial_comment,
        priority=priority,
        category=category,
    )

    # 2. Sequence UIN generation
    current_year = datetime.now().year
    count_this_year = FTSFile.objects.filter(created_at__year=current_year).count()
    uin = generate_file_uin(prefix="FTS", year=current_year, sequence_num=count_this_year + 1)

    # 3. Create persistent file record in DRAFT status (BR-FTS-005)
    file_record = FTSFile.objects.create(
        uin=uin,
        subject=cleaned["subject"],
        description=description.strip(),
        priority=cleaned["priority"],
        category=cleaned["category"],
        status=STATUS_DRAFT,
        creator_id=creator_id,
        creator_role=creator_role,
        current_holder_id=creator_id,
        current_holder_role=creator_role,
        is_draft=True,
    )

    # 4. Record initial creation movement
    movement = FTSMovement.objects.create(
        file=file_record,
        from_user_id=creator_id,
        from_role=creator_role,
        to_user_id=creator_id,
        to_role=creator_role,
        action=ACTION_CREATED,
    )

    # 5. Record mandatory initial comment
    FTSComment.objects.create(
        file=file_record,
        movement=movement,
        author_id=creator_id,
        author_role=creator_role,
        remarks=cleaned["initial_comment"],
    )

    return {
        "file_id": file_record.id,
        "uin": file_record.uin,
        "subject": file_record.subject,
        "status": file_record.status,
        "is_draft": file_record.is_draft,
    }


@transaction.atomic
def update_file_draft(
    file_id: int,
    user_id: str,
    subject: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    category: str | None = None,
) -> dict:
    """Edits a saved draft before circulation (FTS-UC-002, BR-FTS-005)."""
    try:
        file_record = FTSFile.objects.get(id=file_id)
    except FTSFile.DoesNotExist as e:
        raise ValueError("File not found.") from e

    # Domain guard
    allowed, msg = can_edit_draft(
        current_status=file_record.status,
        user_id=user_id,
        creator_id=file_record.creator_id,
    )
    if not allowed:
        raise PermissionError(msg)

    if subject is not None:
        clean_subject = subject.strip()
        if not clean_subject:
            raise ValueError("File subject cannot be empty.")
        file_record.subject = clean_subject

    if description is not None:
        file_record.description = description.strip()

    if priority is not None:
        file_record.priority = priority.strip().lower()

    if category is not None:
        file_record.category = category.strip()

    file_record.save()

    return {
        "file_id": file_record.id,
        "uin": file_record.uin,
        "subject": file_record.subject,
        "status": file_record.status,
    }


@transaction.atomic
def discard_file_draft(file_id: int, user_id: str) -> dict:
    """Discards/deletes a saved draft before circulation (FTS-UC-002, BR-FTS-005)."""
    try:
        file_record = FTSFile.objects.get(id=file_id)
    except FTSFile.DoesNotExist as e:
        raise ValueError("File not found.") from e

    # Domain guard
    allowed, msg = can_edit_draft(
        current_status=file_record.status,
        user_id=user_id,
        creator_id=file_record.creator_id,
    )
    if not allowed:
        raise PermissionError(msg)

    uin = file_record.uin
    file_record.delete()

    return {"file_id": file_id, "uin": uin, "status": "discarded"}
