"""Database models for File Tracking System (FTS).

Institute users are referenced by plain user_id integers, never ForeignKeys,
preserving module autonomy without cross-module database constraints.
"""
import uuid

from django.db import models

from core.db.mixins import TimeStampedModel


def generate_file_code() -> str:
    return f"FTS-{uuid.uuid4().hex[:8].upper()}"


class TrackedFile(TimeStampedModel):
    """An institutional file tracked by FTS (composite object, BR-FTS-003)."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("circulated", "Circulated"),
        ("archived", "Archived"),
    ]

    file_code = models.CharField(
        max_length=64,
        unique=True,
        default=generate_file_code,
        db_index=True,
        help_text="Unique tracking code for the file",
    )
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        default="draft",
        db_index=True,
    )

    creator_user_id = models.IntegerField(db_index=True)
    creator_role = models.CharField(max_length=64)

    owner_user_id = models.IntegerField(db_index=True)

    current_holder_user_id = models.IntegerField(db_index=True)
    current_holder_role = models.CharField(max_length=64, blank=True)

    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by_user_id = models.IntegerField(null=True, blank=True)

    # Inter-module integration support (FTS-UC-010, BR-FTS-014)
    source_module = models.CharField(max_length=64, default="filetracking", db_index=True)
    external_reference = models.CharField(max_length=128, blank=True, db_index=True)

    class Meta:
        db_table = "fts_file"
        indexes = [
            models.Index(fields=["status", "current_holder_user_id"], name="fts_holder_status_idx"),
            models.Index(fields=["owner_user_id", "status"], name="fts_owner_status_idx"),
            models.Index(fields=["creator_user_id", "status"], name="fts_creator_status_idx"),
            models.Index(fields=["source_module", "external_reference"], name="fts_ext_ref_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.file_code}: {self.subject} ({self.status})"


class FileMovement(models.Model):
    """Chronological movement record (BR-FTS-008, AFR-FTS-026, AFR-FTS-027)."""

    MOVEMENT_TYPES = [
        ("creation", "Creation"),
        ("forward", "Forward"),
        ("return", "Return"),
        ("archival", "Archival"),
    ]

    file = models.ForeignKey(
        TrackedFile,
        on_delete=models.CASCADE,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=24, choices=MOVEMENT_TYPES)

    sender_user_id = models.IntegerField(db_index=True)
    sender_role = models.CharField(max_length=64)

    receiver_user_id = models.IntegerField(db_index=True)
    receiver_role = models.CharField(max_length=64)

    comment = models.TextField(help_text="Mandatory movement comment (BR-FTS-006)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fts_file_movement"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["file", "created_at"], name="fts_movement_file_idx"),
            models.Index(
                fields=["receiver_user_id", "created_at"],
                name="fts_movement_receiver_idx",
            ),
            models.Index(fields=["sender_user_id", "created_at"], name="fts_movement_sender_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"File {self.file_id} {self.movement_type}: "
            f"{self.sender_user_id}->{self.receiver_user_id}"
        )


class FileComment(models.Model):
    """Chronological comments on a file (BR-FTS-004, BR-FTS-006, BR-FTS-011)."""

    file = models.ForeignKey(
        TrackedFile,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    movement = models.ForeignKey(
        FileMovement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
    )
    author_user_id = models.IntegerField(db_index=True)
    author_role = models.CharField(max_length=64)
    comment_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fts_file_comment"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["file", "created_at"], name="fts_comment_file_idx"),
            models.Index(fields=["author_user_id"], name="fts_comment_author_idx"),
        ]

    def __str__(self) -> str:
        return f"Comment on {self.file_id} by u{self.author_user_id} at {self.created_at}"


class FileAttachment(models.Model):
    """Optional attachments added at creation or movement (BR-FTS-003, AFR-FTS-013, AFR-FTS-023)."""

    file = models.ForeignKey(
        TrackedFile,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    movement = models.ForeignKey(
        FileMovement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments",
    )
    uploaded_by_user_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=512)
    file_size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fts_file_attachment"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["file", "created_at"], name="fts_attachment_file_idx"),
            models.Index(fields=["uploaded_by_user_id"], name="fts_attachment_user_idx"),
        ]

    def __str__(self) -> str:
        return f"Attachment {self.file_name} for file {self.file_id}"


class FileAuditLog(models.Model):
    """Audit records for all file, movement, archival and integration events (BR-FTS-011)."""

    file = models.ForeignKey(
        TrackedFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=64, db_index=True)
    actor_user_id = models.IntegerField(db_index=True)
    actor_role = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "fts_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"], name="fts_audit_time_idx"),
            models.Index(fields=["action", "created_at"], name="fts_audit_action_time_idx"),
            models.Index(fields=["actor_user_id", "created_at"], name="fts_audit_actor_time_idx"),
        ]

    def __str__(self) -> str:
        return f"Audit {self.action} by u{self.actor_user_id} on {self.created_at}"
