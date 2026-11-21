"""Fusion Clean Architecture - File Tracking System (FTS) Movement Engine Services.

Implements FTS-UC-003 (Forward File) and FTS-UC-004 (Return File).
Enforces business rules BR-FTS-006, BR-FTS-007, and BR-FTS-008.
"""

from django.db import transaction

from modules.fts.domain.workflow import (
    ACTION_FORWARDED,
    ACTION_RETURNED,
    STATUS_IN_TRANSIT,
    STATUS_RETURNED,
    can_forward_file,
    can_return_file,
)
from modules.fts.models import FTSComment, FTSFile, FTSMovement
from modules.fts.selectors.movements import get_previous_senders_for_file


@transaction.atomic
def forward_file(
    file_id: int,
    sender_id: str,
    sender_role: str,
    receiver_id: str,
    receiver_role: str,
    comment: str,
) -> dict:
    """Forwards an active or draft file to another employee (FTS-UC-003).

    :param file_id: Primary key of the file to forward.
    :param sender_id: Employee ID of the sender (must be current holder).
    :param sender_role: Role of the sender.
    :param receiver_id: Employee ID of the recipient.
    :param receiver_role: Role of the recipient.
    :param comment: Mandatory forwarding comment/remark (BR-FTS-006).
    :return: Summary dictionary of the movement.
    """
    try:
        file_obj = FTSFile.objects.select_for_update().get(id=file_id)
    except FTSFile.DoesNotExist as e:
        raise ValueError("File not found.") from e

    # 1. Domain guard check
    allowed, msg = can_forward_file(
        current_status=file_obj.status,
        sender_id=sender_id,
        current_holder_id=file_obj.current_holder_id,
        receiver_id=receiver_id,
        comment=comment,
    )
    if not allowed:
        raise PermissionError(msg)

    clean_comment = comment.strip()

    # 2. Update File state (transitions out of draft if applicable)
    file_obj.status = STATUS_IN_TRANSIT
    file_obj.is_draft = False
    file_obj.current_holder_id = receiver_id
    file_obj.current_holder_role = receiver_role
    file_obj.save()

    # 3. Create movement record (BR-FTS-008)
    movement = FTSMovement.objects.create(
        file=file_obj,
        from_user_id=sender_id,
        from_role=sender_role,
        to_user_id=receiver_id,
        to_role=receiver_role,
        action=ACTION_FORWARDED,
    )

    # 4. Attach mandatory movement comment
    FTSComment.objects.create(
        file=file_obj,
        movement=movement,
        author_id=sender_id,
        author_role=sender_role,
        remarks=clean_comment,
    )

    return {
        "file_id": file_obj.id,
        "uin": file_obj.uin,
        "new_status": file_obj.status,
        "current_holder_id": file_obj.current_holder_id,
        "movement_id": movement.id,
    }


@transaction.atomic
def return_file(
    file_id: int,
    sender_id: str,
    sender_role: str,
    comment: str,
    target_receiver_id: str | None = None,
) -> dict:
    """Returns a received file to a previous sender in the movement chain (FTS-UC-004, BR-FTS-007).

    :param file_id: Primary key of the file.
    :param sender_id: Employee ID returning the file (must be current holder).
    :param sender_role: Role of the sender.
    :param comment: Mandatory return comment.
    :param target_receiver_id: Optional specific recipient from previous senders list.
    :return: Summary dictionary of the return movement.
    """
    try:
        file_obj = FTSFile.objects.select_for_update().get(id=file_id)
    except FTSFile.DoesNotExist as e:
        raise ValueError("File not found.") from e

    previous_senders = get_previous_senders_for_file(file_id=file_id)

    # 1. Domain guard check
    allowed, msg = can_return_file(
        current_status=file_obj.status,
        sender_id=sender_id,
        current_holder_id=file_obj.current_holder_id,
        previous_senders=previous_senders,
        comment=comment,
    )
    if not allowed:
        raise PermissionError(msg)

    # Determine recipient: return to immediate predecessor if not specified
    if target_receiver_id:
        if target_receiver_id not in previous_senders:
            raise ValueError(
                f"Recipient '{target_receiver_id}' is not in the historical movement chain."
            )
        return_to_id = target_receiver_id
    else:
        # Default to the most recent sender who isn't the current user
        candidate_senders = [s for s in previous_senders if s != sender_id]
        if not candidate_senders:
            raise ValueError("No eligible predecessor found to return the file to.")
        return_to_id = candidate_senders[-1]

    clean_comment = comment.strip()

    # 2. Update File state
    file_obj.status = STATUS_RETURNED
    file_obj.current_holder_id = return_to_id
    file_obj.save()

    # 3. Create movement record
    movement = FTSMovement.objects.create(
        file=file_obj,
        from_user_id=sender_id,
        from_role=sender_role,
        to_user_id=return_to_id,
        to_role="",
        action=ACTION_RETURNED,
    )

    # 4. Attach comment
    FTSComment.objects.create(
        file=file_obj,
        movement=movement,
        author_id=sender_id,
        author_role=sender_role,
        remarks=clean_comment,
    )

    return {
        "file_id": file_obj.id,
        "uin": file_obj.uin,
        "new_status": file_obj.status,
        "returned_to_id": return_to_id,
        "movement_id": movement.id,
    }
