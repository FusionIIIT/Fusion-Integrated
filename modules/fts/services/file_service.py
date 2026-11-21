from uuid import uuid4
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from modules.fts.models import FTSFile, FileMovement, FileAuditLog, FileAttachment
from modules.directory.models import UserRef

def create_file(owner: UserRef, subject: str, description: str = "", initial_comment: str = "", creator_role: str = "", attachments_data: list = None) -> FTSFile:
    if not initial_comment.strip():
        raise ValidationError("Initial comment is required per BR-FTS-004.")
    file_number = f"FTS-{timezone.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
    file = FTSFile.objects.create(
        file_number=file_number,
        owner=owner,
        subject=subject,
        description=description,
        status='draft',
        creator_role=creator_role,
        current_holder=owner,
        current_holder_role=creator_role
    )
    FileMovement.objects.create(
        file=file,
        sender=owner,
        sender_role=creator_role,
        receiver=owner,
        receiver_role=creator_role,
        action='created',
        comments=initial_comment
    )
    FileAuditLog.objects.create(
        file=file,
        actor=owner,
        actor_role=creator_role,
        action='created',
        details="File created in draft status."
    )
    if attachments_data:
        for data in attachments_data:
            FileAttachment.objects.create(file=file, **data)
    return file

def edit_draft(file: FTSFile, user: UserRef, subject: str = None, description: str = None, user_role: str = "") -> FTSFile:
    if file.status != 'draft' or file.owner_id != user.user_id:
        raise PermissionDenied("Only the owner can edit a draft file per BR-FTS-005.")
    if subject is not None:
        file.subject = subject
    if description is not None:
        file.description = description
    file.save()
    FileAuditLog.objects.create(
        file=file,
        actor=user,
        actor_role=user_role,
        action='draft_edited'
    )
    return file

def discard_draft(file: FTSFile, user: UserRef, user_role: str = "") -> FTSFile:
    if file.status != 'draft' or file.owner_id != user.user_id:
        raise PermissionDenied("Only the owner can discard a draft file per BR-FTS-005.")
    file.status = 'discarded'
    file.save()
    FileAuditLog.objects.create(
        file=file,
        actor=user,
        actor_role=user_role,
        action='draft_discarded'
    )
    return file

def send_file(file: FTSFile, sender: UserRef, receiver: UserRef, comment: str, sender_role: str = "", receiver_role: str = "", attachments_data: list = None) -> FileMovement:
    if not comment.strip():
        raise ValidationError("Movement comment is required per BR-FTS-006.")
    if file.is_archived or file.status in ['archived', 'discarded']:
        raise ValidationError("Cannot send an archived or discarded file per BR-FTS-005.")
    if file.current_holder_id != sender.user_id:
        raise PermissionDenied("Only the current holder can send the file per BR-FTS-005.")
    file.status = 'circulated'
    file.current_holder = receiver
    file.current_holder_role = receiver_role
    file.save()
    movement = FileMovement.objects.create(
        file=file,
        sender=sender,
        sender_role=sender_role,
        receiver=receiver,
        receiver_role=receiver_role,
        action='forwarded',
        comments=comment
    )
    FileAuditLog.objects.create(
        file=file,
        actor=sender,
        actor_role=sender_role,
        action='forwarded',
        details=f"Forwarded to {receiver.username}"
    )
    if attachments_data:
        for data in attachments_data:
            FileAttachment.objects.create(file=file, **data)
    return movement

def return_file(file: FTSFile, sender: UserRef, comment: str, sender_role: str = "") -> FileMovement:
    if not comment.strip():
        raise ValidationError("Movement comment is required per BR-FTS-006.")
    if file.is_archived or file.status in ['archived', 'discarded']:
        raise ValidationError("Cannot return an archived or discarded file per BR-FTS-005.")
    if file.current_holder_id != sender.user_id:
        raise PermissionDenied("Only the current holder can return the file per BR-FTS-005.")
    prior_movement = file.movements.exclude(action='created').order_by('-created_at').first()
    target_receiver = prior_movement.sender if prior_movement else file.owner
    file.current_holder = target_receiver
    file.current_holder_role = prior_movement.sender_role if prior_movement else ""
    file.save()
    movement = FileMovement.objects.create(
        file=file,
        sender=sender,
        sender_role=sender_role,
        receiver=target_receiver,
        receiver_role=file.current_holder_role,
        action='returned',
        comments=comment
    )
    FileAuditLog.objects.create(
        file=file,
        actor=sender,
        actor_role=sender_role,
        action='returned',
        details=f"Returned to {target_receiver.username}"
    )
    return movement

def archive_file(file: FTSFile, user: UserRef, comment: str = "", user_role: str = "") -> FTSFile:
    if file.owner_id != user.user_id:
        raise PermissionDenied("Only the file owner can archive this file per BR-FTS-012.")
    if file.status != 'circulated':
        raise ValidationError("Cannot archive a draft or already archived file per BR-FTS-012.")
    file.status = 'archived'
    file.is_archived = True
    file.archived_at = timezone.now()
    file.save()
    movement = FileMovement.objects.create(
        file=file,
        sender=user,
        sender_role=user_role,
        receiver=user,
        receiver_role=user_role,
        action='archived',
        comments=comment or "File archived by owner."
    )
    FileAuditLog.objects.create(
        file=file,
        actor=user,
        actor_role=user_role,
        action='archived',
        details="File permanently archived."
    )
    return file

def get_inbox(user: UserRef):
    return FTSFile.objects.filter(current_holder=user, status='circulated').order_by('-updated_at')

def get_outbox(user: UserRef):
    return FTSFile.objects.filter(movements__sender=user, status='circulated').exclude(current_holder=user).distinct().order_by('-updated_at')

def get_drafts(user: UserRef):
    return FTSFile.objects.filter(owner=user, status='draft').order_by('-updated_at')

def get_archived(user: UserRef):
    return FTSFile.objects.filter(Q(owner=user) | Q(movements__sender=user) | Q(movements__receiver=user), is_archived=True).distinct().order_by('-archived_at')

def get_file_history(file: FTSFile, user: UserRef) -> dict:
    return {
        'file': file,
        'movements': file.movements.all().order_by('created_at'),
        'attachments': file.attachments.all(),
        'audit_logs': file.audit_logs.all().order_by('created_at')
    }