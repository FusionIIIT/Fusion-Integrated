from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from modules.fts.domain.commands import create_file, edit_draft, discard_draft
from modules.fts.models import FtsFile, FtsFileComment, FtsFileAttachment, FtsAuditLog


def create_file_service(actor_id: str, initial_comment: str, attachment_urls: list[str] = None) -> FtsFile:
    file_state = create_file(actor_id, initial_comment, attachment_urls)
    
    with transaction.atomic():
        file = FtsFile.objects.create(
            id=file_state["file_id"],
            owner_id=file_state["owner_id"],
            status=file_state["status"],
            initial_comment=file_state["initial_comment"],
            attachment_urls=file_state["attachment_urls"],
            created_at=file_state["created_at"],
        )
        
        FtsFileComment.objects.create(
            file=file,
            actor_id=actor_id,
            text=file_state["initial_comment"],
            is_initial=True,
            created_at=file_state["created_at"],
        )
        
        if file_state["attachment_urls"]:
            for url in file_state["attachment_urls"]:
                FtsFileAttachment.objects.create(
                    file=file,
                    actor_id=actor_id,
                    file_url=url,
                    created_at=file_state["created_at"],
                )
        
        FtsAuditLog.objects.create(
            file=file,
            actor_id=actor_id,
            action='CREATE',
            details={
                'initial_comment': file_state["initial_comment"],
                'attachment_count': len(file_state["attachment_urls"]),
            },
        )
    
    return file


def edit_draft_service(actor_id: str, file_id: str, new_comment: str, new_attachment_urls: list[str] = None) -> FtsFile:
    try:
        file = FtsFile.objects.get(id=file_id)
    except FtsFile.DoesNotExist:
        raise ValueError("File not found.")
    
    current_status = file.status
    edit_state = edit_draft(current_status, new_comment, new_attachment_urls)
    
    with transaction.atomic():
        file.status = edit_state["status"]
        file.initial_comment = new_comment
        file.attachment_urls = new_attachment_urls
        file.save()
        
        FtsFileComment.objects.filter(file=file, is_initial=True).update(text=new_comment)
        
        FtsFileAttachment.objects.filter(file=file).delete()
        if new_attachment_urls:
            for url in new_attachment_urls:
                FtsFileAttachment.objects.create(
                    file=file,
                    actor_id=actor_id,
                    file_url=url,
                    created_at=timezone.now(),
                )
        
        FtsAuditLog.objects.create(
            file=file,
            actor_id=actor_id,
            action='EDIT_DRAFT',
            details={
                'new_comment': new_comment,
                'attachment_count': len(new_attachment_urls),
            },
        )
    
    return file


def discard_draft_service(actor_id: str, file_id: str) -> None:
    try:
        file = FtsFile.objects.get(id=file_id)
    except FtsFile.DoesNotExist:
        raise ValueError("File not found.")
    
    current_status = file.status
    discard_draft(current_status)
    
    with transaction.atomic():
        FtsFileComment.objects.filter(file=file).delete()
        FtsFileAttachment.objects.filter(file=file).delete()
        file.status = FileStatus.DISCARDED.value
        file.save()
        
        FtsAuditLog.objects.create(
            file=file,
            actor_id=actor_id,
            action='DISCARD_DRAFT',
            details={
                'file_id': file_id,
            },
        )
