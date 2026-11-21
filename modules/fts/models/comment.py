"""File Comment model (CFR-FTS-001, BR-FTS-003, BR-FTS-004, BR-FTS-006)."""
from django.db import models

from core.db.mixins import TimeStampedModel


class FileComment(TimeStampedModel):
    file = models.ForeignKey(
        "fts.FTSFile",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    movement = models.ForeignKey(
        "fts.FileMovement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="comments",
    )
    author_id = models.IntegerField(db_index=True)
    author_designation = models.CharField(max_length=128, blank=True, default="")
    comment_text = models.TextField()

    class Meta:
        db_table = "fts_comment"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["author_id"], name="idx_fts_comment_author"),
            models.Index(fields=["created_at"], name="idx_fts_comment_created"),
        ]

    def __str__(self) -> str:
        return f"Comment on {self.file_id} by {self.author_id} at {self.created_at}"
