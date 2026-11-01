"""Co-inventor and institutional agreements models."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.models.applications import PatentApplication


class Inventor(TimeStampedModel):
    """Lead inventor or co-inventor on a patent application."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="inventors"
    )
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    department = models.CharField(max_length=100)
    is_lead = models.BooleanField(default=False)
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    consent_status = models.CharField(max_length=50, default="pending")  # pending, granted, refused
    consent_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pms_inventor"
        ordering = ["-is_lead", "name"]
        indexes = [
            models.Index(fields=["application", "user_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.share_percentage}%)"


class InventorAgreement(TimeStampedModel):
    """Legal agreements and assignment forms (BR-PMS-020, 078)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="agreements"
    )
    agreement_type = models.CharField(max_length=100)  # patent_assignment, co_inventor_agreement
    status = models.CharField(max_length=50, default="draft")  # draft, circulated, completed
    completed_at = models.DateTimeField(null=True, blank=True)
    document_url = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "pms_inventor_agreement"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.agreement_type} - {self.status}"
