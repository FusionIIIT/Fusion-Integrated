from django.db import models

from core.db.mixins import TimeStampedModel


class FileComment(TimeStampedModel):
    file = models.ForeignKey("fts.File", on_delete=models.CASCADE, related_name="comments")
    movement = models.ForeignKey(
        "fts.FileMovement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
    )

    author_user_id = models.IntegerField(db_index=True)
    author_username = models.CharField(max_length=150)
    author_role = models.CharField(max_length=100)
    comment_text = models.TextField()

    class Meta:
        db_table = "fts_comment"
        indexes = [
            models.Index(fields=["file", "created_at"], name="fts_comm_file_time_idx"),
        ]

    def __str__(self) -> str:
        return f"Comment by {self.author_username} on file {self.file_id}"
