import uuid

from django.db import models


class FtsFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id = models.UUIDField()
    current_holder_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('DRAFT', 'Draft'),
            ('CIRCULATED', 'Circulated'),
            ('ARCHIVED', 'Archived'),
            ('DISCARDED', 'Discarded'),
        ],
        default='DRAFT',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"FtsFile {self.id}"


class FtsFileComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_id = models.UUIDField()
    actor_id = models.UUIDField()
    text = models.TextField()
    is_initial = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FtsFileComment {self.id}"


class FtsFileAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_id = models.UUIDField()
    actor_id = models.UUIDField()
    file_url = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FtsFileAttachment {self.id}"


class FtsAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_id = models.UUIDField(null=True, blank=True)
    actor_id = models.UUIDField()
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FtsAuditLog {self.id}"


class FtsFileMovement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_id = models.UUIDField()
    sender_id = models.UUIDField()
    receiver_id = models.UUIDField()
    comment = models.TextField()
    movement_type = models.CharField(
        max_length=10,
        choices=[
            ('FORWARD', 'Forward'),
            ('RETURN', 'Return')
        ])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FtsFileMovement {self.id}"
