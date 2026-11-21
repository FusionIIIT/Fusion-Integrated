"""File Movement model (CFR-FTS-005, CFR-FTS-007, BR-FTS-008)."""
from django.db import models

from core.db.mixins import TimeStampedModel


class FileMovement(TimeStampedModel):
    ACTION_CHOICES = [
        ("created", "Created"),
        ("forwarded", "Forwarded"),
        ("returned", "Returned"),
        ("archived", "Archived"),
    ]

    file = models.ForeignKey(
        "fts.FTSFile",
        on_delete=models.CASCADE,
        related_name="movements",
    )
    sequence_number = models.PositiveIntegerField()
    sender_id = models.IntegerField(db_index=True)
    sender_designation = models.CharField(max_length=128, blank=True, default="")
    receiver_id = models.IntegerField(db_index=True)
    receiver_designation = models.CharField(max_length=128, blank=True, default="")
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "fts_movement"
        ordering = ["sequence_number"]
        indexes = [
            models.Index(fields=["sender_id", "action"], name="idx_fts_mov_sender_act"),
            models.Index(fields=["receiver_id", "action"], name="idx_fts_mov_rcv_act"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["file", "sequence_number"],
                name="fts_movement_unique_seq",
            ),
            models.CheckConstraint(
                condition=models.Q(action__in=["created", "forwarded", "returned", "archived"]),
                name="fts_movement_action_valid",
            ),
        ]

    def __str__(self) -> str:
        s = f"{self.file.file_id} #{self.sequence_number}: {self.action}"
        return f"{s} ({self.sender_id}->{self.receiver_id})"
