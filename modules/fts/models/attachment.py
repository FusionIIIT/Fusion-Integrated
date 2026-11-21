"""File Attachment model (CFR-FTS-001, BR-FTS-003)."""
from django.db import models

from core.db.mixins import TimeStampedModel


class FileAttachment(TimeStampedModel):
    file = models.ForeignKey(
        "fts.FTSFile",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    movement = models.ForeignKey(
        "fts.FileMovement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attachments",
    )
    uploader_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=512)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=128, blank=True, default="application/octet-stream")

    class Meta:
        db_table = "fts_attachment"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["uploader_id"], name="idx_fts_attach_uploader"),
        ]

    def __str__(self) -> str:
        return f"{self.file_name} on {self.file_id}"
