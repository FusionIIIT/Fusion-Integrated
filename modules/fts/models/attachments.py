from django.db import models

from core.db.mixins import TimeStampedModel


class FileAttachment(TimeStampedModel):
    file = models.ForeignKey("fts.File", on_delete=models.CASCADE, related_name="attachments")
    movement = models.ForeignKey(
        "fts.FileMovement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments",
    )

    uploader_user_id = models.IntegerField(db_index=True)
    uploader_username = models.CharField(max_length=150)
    file_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=1024)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "fts_attachment"
        indexes = [
            models.Index(fields=["file", "created_at"], name="fts_att_file_time_idx"),
        ]

    def __str__(self) -> str:
        return f"Attachment {self.file_name} on file {self.file_id}"
