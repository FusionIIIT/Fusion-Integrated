"""Application supporting documents and version management."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.models.applications import PatentApplication


class ApplicationDocument(TimeStampedModel):
    """Supporting document with PDF/50MB validation and security (BR-PMS-014..130)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(
        max_length=50, db_index=True
    )  # specification, claims, drawings, prior_art, office_action
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="pms/documents/%Y/%m/")
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100, default="application/pdf")
    sensitivity = models.CharField(
        max_length=50, default="confidential"
    )  # standard, confidential, restricted
    version = models.IntegerField(default=1)
    uploaded_by_user_id = models.IntegerField(db_index=True)
    is_malware_scanned = models.BooleanField(default=False)
    scan_details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "pms_application_document"
        ordering = ["-version", "-created_at"]
        indexes = [
            models.Index(fields=["application", "document_type", "version"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} (v{self.version})"
