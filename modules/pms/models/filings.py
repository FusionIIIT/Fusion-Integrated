"""External patent office filing records."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.models.applications import PatentApplication


class ExternalFilingRecord(TimeStampedModel):
    """External patent office filing details (BR-PMS-055, 056, 128, 142)."""

    application = models.OneToOneField(
        PatentApplication, on_delete=models.CASCADE, related_name="filing_record"
    )
    jurisdiction = models.CharField(max_length=50, default="IN")  # IN, PCT, US, EP
    filing_number = models.CharField(max_length=100, unique=True, db_index=True)
    filing_date = models.DateField(db_index=True)
    patent_office = models.CharField(max_length=200)
    confirmation_details = models.TextField()
    international_justification = models.TextField(blank=True)
    recorded_by_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "pms_external_filing_record"
        ordering = ["-filing_date"]

    def __str__(self) -> str:
        return f"{self.filing_number} ({self.jurisdiction}) - App {self.application_id}"
