"""Patent Application core model."""

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.pms.domain.constants import STATUS_DRAFT


class PatentApplication(TimeStampedModel, UserScopedModel):
    """Core patent application aggregate."""

    application_no = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    description = models.TextField()
    claims = models.TextField()
    domain = models.CharField(max_length=100, db_index=True)
    filing_type = models.CharField(max_length=50, default="provisional")
    status = models.CharField(max_length=50, default=STATUS_DRAFT, db_index=True)
    is_confidential = models.BooleanField(default=True)
    preferred_attorney_id = models.IntegerField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    revision_deadline = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pms_patent_application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "domain"]),
            models.Index(fields=["user_id", "status"]),
        ]

    def save(self, *args, **kwargs) -> None:
        if not self.application_no:
            import uuid

            from django.utils import timezone

            self.application_no = f"PMS-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.application_no} - {self.title}"
