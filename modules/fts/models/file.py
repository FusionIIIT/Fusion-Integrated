"""FTS File domain model (CFR-FTS-001, CFR-FTS-003, BR-FTS-003, BR-FTS-005)."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.fts.domain import state_machine


class FTSFile(TimeStampedModel):
    STATUS_CHOICES = [
        (state_machine.DRAFT, "Draft"),
        (state_machine.CIRCULATING, "Circulating"),
        (state_machine.ARCHIVED, "Archived"),
        (state_machine.DISCARDED, "Discarded"),
    ]

    file_id = models.CharField(max_length=64, unique=True, db_index=True)
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=state_machine.DRAFT,
        db_index=True,
    )
    creator_id = models.IntegerField(db_index=True)
    creator_designation = models.CharField(max_length=128, blank=True, default="")
    owner_id = models.IntegerField(db_index=True)
    current_holder_id = models.IntegerField(null=True, blank=True, db_index=True)
    current_holder_designation = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "fts_file"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["current_holder_id", "status"], name="idx_fts_holder_status"),
            models.Index(fields=["creator_id", "status"], name="idx_fts_creator_status"),
            models.Index(fields=["created_at"], name="idx_fts_created_at"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=[
                    state_machine.DRAFT,
                    state_machine.CIRCULATING,
                    state_machine.ARCHIVED,
                    state_machine.DISCARDED,
                ]),
                name="fts_file_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.file_id}: {self.subject} ({self.status})"
