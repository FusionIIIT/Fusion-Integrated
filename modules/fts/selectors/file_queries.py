from django.db.models import Q, QuerySet

from modules.fts.models import FtsFile, FtsFileAttachment, FtsFileComment, FtsFileMovement


def get_inbox_files(actor_id: str) -> QuerySet:
    return FtsFile.objects.filter(
        Q(current_holder_id=actor_id) |
        Q(ftsfilemovement__receiver_id=actor_id)
    ).distinct().order_by('-updated_at')


def get_outbox_files(actor_id: str) -> QuerySet:
    return FtsFile.objects.filter(
        Q(owner_id=actor_id) |
        Q(ftsfilemovement__sender_id=actor_id)
    ).distinct().order_by('-updated_at')


def get_file_detail(actor_id: str, file_id: str) -> FtsFile:
    file = FtsFile.objects.filter(
        Q(id=file_id) &
        (Q(owner_id=actor_id) |
         Q(current_holder_id=actor_id) |
         Q(ftsfilemovement__sender_id=actor_id) |
         Q(ftsfilemovement__receiver_id=actor_id)
        )
    ).first()
    if not file:
        raise ValueError("File not found.")
    return file


def get_file_comments(file_id: str) -> QuerySet:
    return FtsFileComment.objects.filter(file_id=file_id).order_by('created_at')


def get_file_attachments(file_id: str) -> QuerySet:
    return FtsFileAttachment.objects.filter(file_id=file_id).order_by('created_at')


def get_file_history(actor_id: str, file_id: str) -> QuerySet:
    get_file_detail(actor_id, file_id)  # Verify user is authorized to view the file
    return FtsFileMovement.objects.filter(file_id=file_id).order_by('created_at')
