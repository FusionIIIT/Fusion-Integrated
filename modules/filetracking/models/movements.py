"""FileMovement model for File Tracking System."""

from django.db import models

from core.db.mixins import TimeStampedModel


class FileMovement(TimeStampedModel):
    file = models.ForeignKey(
        "TrackedFile",
        on_delete=models.CASCADE,
        related_name="movements",
    )
    sequence_number = models.PositiveIntegerField()
    action = models.CharField(max_length=32)
    sender_user_id = models.IntegerField(db_index=True)
    sender_designation = models.CharField(max_length=128)
    receiver_user_id = models.IntegerField(db_index=True)
    receiver_designation = models.CharField(max_length=128)
    comment = models.TextField()

    class Meta:
        db_table = "filetracking_movement"
        ordering = ["file", "sequence_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["file", "sequence_number"],
                name="uniq_fts_movement_seq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["file", "sequence_number"],
                name="idx_fts_mov_file_seq",
            ),
            models.Index(
                fields=["receiver_user_id", "-created_at"],
                name="idx_fts_mov_rcv_created",
            ),
            models.Index(
                fields=["sender_user_id", "-created_at"],
                name="idx_fts_mov_snd_created",
            ),
        ]

    def __str__(self) -> str:
        return f"Movement #{self.sequence_number} ({self.action}) on {self.file_id}"
