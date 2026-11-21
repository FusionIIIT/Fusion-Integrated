from django.db import models

from core.db.mixins import TimeStampedModel
from modules.fts.domain.state_machine import (
    STATE_ARCHIVED,
    STATE_CIRCULATED,
    STATE_DISCARDED,
    STATE_DRAFT,
)


class File(TimeStampedModel):
    STATUS_CHOICES = [
        (STATE_DRAFT, "Draft"),
        (STATE_CIRCULATED, "Circulated"),
        (STATE_ARCHIVED, "Archived"),
        (STATE_DISCARDED, "Discarded"),
    ]

    reference_number = models.CharField(max_length=64, unique=True, db_index=True)
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=24, choices=STATUS_CHOICES, default=STATE_DRAFT, db_index=True
    )

    owner_user_id = models.IntegerField(db_index=True)
    owner_username = models.CharField(max_length=150)
    owner_role = models.CharField(max_length=100)

    current_holder_user_id = models.IntegerField(db_index=True)
    current_holder_username = models.CharField(max_length=150)
    current_holder_role = models.CharField(max_length=100)

    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "fts_file"
        indexes = [
            models.Index(fields=["current_holder_user_id", "status"], name="fts_file_holder_idx"),
            models.Index(fields=["owner_user_id", "status"], name="fts_file_owner_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.reference_number} - {self.subject} ({self.status})"
