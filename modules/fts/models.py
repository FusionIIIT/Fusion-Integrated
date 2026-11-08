from django.db import models
from core.db.mixins import TimeStampedModel
from modules.directory.models import UserRef

class FTSFile(TimeStampedModel):
    file_number = models.CharField(max_length=64, unique=True, db_index=True)
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(UserRef, on_delete=models.PROTECT, related_name='fts_owned_files')
    creator_role = models.CharField(max_length=64, blank=True)
    current_holder = models.ForeignKey(UserRef, on_delete=models.PROTECT, related_name='fts_held_files', null=True, blank=True)
    current_holder_role = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=[('draft', 'Draft'), ('circulated', 'Circulated / Active'), ('archived', 'Archived / Read-only'), ('discarded', 'Discarded')], default='draft', db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    def is_accessible_by(self, user):
        return (
            self.owner_id == user.user_id or
            self.current_holder_id == user.user_id or
            self.movements.filter(sender=user).exists() or
            self.movements.filter(receiver=user).exists()
        )

    def __str__(self):
        return f"{self.file_number}: {self.subject} ({self.status})"

class FileMovement(TimeStampedModel):
    file = models.ForeignKey(FTSFile, on_delete=models.CASCADE, related_name='movements')
    sender = models.ForeignKey(UserRef, on_delete=models.PROTECT, related_name='fts_sent_movements')
    sender_role = models.CharField(max_length=64, blank=True)
    receiver = models.ForeignKey(UserRef, on_delete=models.PROTECT, related_name='fts_received_movements')
    receiver_role = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=20, choices=[('created', 'Created'), ('forwarded', 'Forwarded'), ('returned', 'Returned'), ('archived', 'Archived')])
    comments = models.TextField()

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Move #{self.id} on {self.file.file_number} by {self.sender.username} ({self.action})"

class FileAttachment(TimeStampedModel):
    file = models.ForeignKey(FTSFile, on_delete=models.CASCADE, related_name='attachments')
    movement = models.ForeignKey(FileMovement, on_delete=models.SET_NULL, null=True, blank=True, related_name='attachments')
    uploader = models.ForeignKey(UserRef, on_delete=models.PROTECT, related_name='fts_uploaded_attachments')
    file_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=500, blank=True)
    file_size = models.IntegerField(default=0)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.file_name} ({self.file.file_number})"

class FileAuditLog(TimeStampedModel):
    file = models.ForeignKey(FTSFile, on_delete=models.CASCADE, related_name='audit_logs')
    actor = models.ForeignKey(UserRef, on_delete=models.PROTECT, related_name='fts_audit_actions')
    actor_role = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=64)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Audit #{self.id} on {self.file.file_number} - {self.action}"