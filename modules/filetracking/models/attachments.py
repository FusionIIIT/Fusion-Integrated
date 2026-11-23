"""FileAttachment model for File Tracking System."""

from django.db import models

from core.db.mixins import TimeStampedModel


class FileAttachment(TimeStampedModel):
    file = models.ForeignKey(
        "TrackedFile",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    movement = models.ForeignKey(
        "FileMovement",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )
    uploaded_by_user_id = models.IntegerField(db_index=True)
    uploader_designation = models.CharField(max_length=128)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=512)
    file_size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=128)

    class Meta:
        db_table = "filetracking_attachment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["file", "-created_at"],
                name="idx_fts_att_file_created",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(file_size__lte=10485760),
                name="check_fts_att_max_10mb",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.file_name} ({self.file_size} bytes)"
