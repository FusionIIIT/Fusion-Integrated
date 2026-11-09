from django.db import transaction
from django.utils import timezone

from modules.fts.domain import commands
from modules.fts.models import (
    FtsAuditLog,
    FtsFile,
    FtsFileAttachment,
    FtsFileComment,
    FtsFileMovement,
)


def forward_file_service(
        actor_id: str,
        file_id: str,
        receiver_id: str,
        movement_comment: str,
        attachment_urls: list[str] | None = None
    ) -> FtsFile:
    file = FtsFile.objects.filter(id=file_id).first()
    if not file:
        raise ValueError("File not found.")

    if file.current_holder_id is None:
        if str(file.owner_id) != actor_id:
            raise ValueError("You are not the current holder of this file.")
    else:
        if str(file.current_holder_id) != actor_id:
            raise ValueError("You are not the current holder of this file.")

    movement_details = commands.forward_file(
        file.status,
        actor_id,
        receiver_id,
        movement_comment,
        attachment_urls
    )

    with transaction.atomic():
        FtsFileMovement.objects.create(
            file_id=file.id,
            sender_id=actor_id,
            receiver_id=receiver_id,
            comment=movement_comment,
            movement_type='FORWARD',
            created_at=timezone.now()
        )

        file.current_holder_id = receiver_id
        file.status = 'CIRCULATED'
        file.updated_at = timezone.now()
        file.save()

        FtsFileComment.objects.create(
            file_id=file.id,
            actor_id=actor_id,
            text=movement_comment,
            is_initial=False,
            created_at=timezone.now()
        )

        if attachment_urls:
            for url in attachment_urls:
                FtsFileAttachment.objects.create(
                    file_id=file.id,
                    actor_id=actor_id,
                    file_url=url,
                    created_at=timezone.now()
                )

        FtsAuditLog.objects.create(
            file_id=file.id,
            actor_id=actor_id,
            action='FORWARD',
            details=movement_details,
            created_at=timezone.now()
        )

    return file


def return_file_service(
        actor_id: str,
        file_id: str,
        movement_comment: str,
        attachment_urls: list[str] | None = None
    ) -> FtsFile:

    file = FtsFile.objects.filter(id=file_id).first()
    if not file:
        raise ValueError("File not found.")

    if file.current_holder_id != actor_id:
        raise ValueError("You are not the current holder of this file.")

    if not FtsFileMovement.objects.filter(file_id=file_id).exists():
        raise ValueError("Cannot return a file that has not been forwarded.")

    previous_movement = (
        FtsFileMovement.objects
        .filter(file_id=file_id)
        .order_by('-created_at')
        .first()
    )

    receiver_id = previous_movement.sender_id

    movement_details = commands.return_file(
        file.status,
        actor_id,
        receiver_id,
        movement_comment,
        attachment_urls
    )

    with transaction.atomic():
        FtsFileMovement.objects.create(
            file_id=file.id,
            sender_id=actor_id,
            receiver_id=receiver_id,
            comment=movement_comment,
            movement_type='RETURN',
            created_at=timezone.now()
        )

        file.current_holder_id = receiver_id
        file.updated_at = timezone.now()
        file.save()

        FtsFileComment.objects.create(
            file_id=file.id,
            actor_id=actor_id,
            text=movement_comment,
            is_initial=False,
            created_at=timezone.now()
        )

        if attachment_urls:
            for url in attachment_urls:
                FtsFileAttachment.objects.create(
                    file_id=file.id,
                    actor_id=actor_id,
                    file_url=url,
                    created_at=timezone.now()
                )

        FtsAuditLog.objects.create(
            file_id=file.id,
            actor_id=actor_id,
            action='RETURN',
            details=movement_details,
            created_at=timezone.now()
        )

    return file
