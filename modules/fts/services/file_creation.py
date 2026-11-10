import uuid

from django.db import transaction

from modules.fts.domain.commands import create_file, discard_draft, edit_draft
from modules.fts.models import FtsAuditLog, FtsFile, FtsFileAttachment, FtsFileComment


@transaction.atomic
def create_file_service(
    actor_id: str, initial_comment: str, attachment_urls: list | None = None
) -> FtsFile:
    # 1. Validate via domain layer
    data = create_file(
        owner_id=actor_id,
        initial_comment=initial_comment,
        attachment_urls=attachment_urls
    )

    # 2. Create the base File record
    file = FtsFile.objects.create(
        id=uuid.UUID(data['file_id']),
        owner_id=actor_id,
        status=data['status'],
        current_holder_id=actor_id  # Owner holds the draft initially
    )

    # 3. Create the Initial Comment
    FtsFileComment.objects.create(
        file_id=str(file.id),
        actor_id=actor_id,
        text=data['initial_comment'],
        is_initial=True
    )

    # 4. Create Attachments
    if data.get('attachment_urls'):
        for url in data['attachment_urls']:
            FtsFileAttachment.objects.create(
                file_id=str(file.id),
                actor_id=actor_id,
                file_url=url
            )

    # 5. Audit Log
    FtsAuditLog.objects.create(
        file_id=str(file.id),
        actor_id=actor_id,
        action='CREATE',
        details={
            'comment': data['initial_comment'],
            'attachment_count': len(data.get('attachment_urls', []))
        }
    )

    return file


@transaction.atomic
def edit_draft_service(
    actor_id: str, file_id: str, new_comment: str, new_attachment_urls: list | None = None
) -> FtsFile:
    try:
        file = FtsFile.objects.get(id=file_id)
    except FtsFile.DoesNotExist as err:
        raise ValueError("File not found.") from err

    if str(file.owner_id) != actor_id:
        raise ValueError("Only the owner can edit the draft.")

    # Validate via domain layer
    data = edit_draft(
        current_status=file.status,
        new_comment=new_comment,
        new_attachment_urls=new_attachment_urls
    )

    # Update the initial comment text
    FtsFileComment.objects.filter(file_id=file_id, is_initial=True).update(text=data['new_comment'])

    # Replace all attachments to reflect the new draft state
    FtsFileAttachment.objects.filter(file_id=file_id).delete()
    if data.get('new_attachment_urls'):
        for url in data['new_attachment_urls']:
            FtsFileAttachment.objects.create(
                file_id=str(file.id),
                actor_id=actor_id,
                file_url=url
            )

    # Audit Log
    FtsAuditLog.objects.create(
        file_id=str(file.id),
        actor_id=actor_id,
        action='EDIT_DRAFT',
        details={
            'comment': data['new_comment'],
            'attachment_count': len(data.get('new_attachment_urls', []))
        }
    )

    return file


@transaction.atomic
def discard_draft_service(actor_id: str, file_id: str) -> None:
    try:
        file = FtsFile.objects.get(id=file_id)
    except FtsFile.DoesNotExist as err:
        raise ValueError("File not found.") from err

    if str(file.owner_id) != actor_id:
        raise ValueError("Only the owner can discard the draft.")

    # Validate via domain layer
    discard_draft(current_status=file.status)

    # Delete associated comments and attachments
    FtsFileComment.objects.filter(file_id=file_id).delete()
    FtsFileAttachment.objects.filter(file_id=file_id).delete()

    # Audit Log (created before deleting the file)
    FtsAuditLog.objects.create(
        file_id=str(file.id),
        actor_id=actor_id,
        action='DISCARD_DRAFT',
        details={'discarded_file_id': str(file.id)}
    )

    # Delete the file itself
    file.delete()
