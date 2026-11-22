"""TrackedFile model for File Tracking System."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.filetracking.domain.entities import FileStatus


class TrackedFile(TimeStampedModel):
    STATUS_CHOICES = [
        (FileStatus.DRAFT, "Draft"),
        (FileStatus.CIRCULATING, "Circulating"),
        (FileStatus.ARCHIVED, "Archived"),
    ]

    file_number = models.CharField(max_length=64, unique=True, db_index=True)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=FileStatus.DRAFT,
        db_index=True,
    )
    created_by_user_id = models.IntegerField(db_index=True)
    creator_designation = models.CharField(max_length=128)
    current_holder_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    current_holder_designation = models.CharField(max_length=128, blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "filetracking_file"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["status", "current_holder_user_id"],
                name="idx_fts_file_status_holder",
            ),
            models.Index(
                fields=["created_by_user_id", "status"],
                name="idx_fts_file_creator_status",
            ),
            models.Index(
                fields=["-updated_at"],
                name="idx_fts_file_updated_at",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        FileStatus.DRAFT,
                        FileStatus.CIRCULATING,
                        FileStatus.ARCHIVED,
                    ]
                ),
                name="check_fts_file_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.file_number} - {self.subject} ({self.status})"
