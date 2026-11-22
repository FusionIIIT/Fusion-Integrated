from django.db import models

from core.db.mixins import TimeStampedModel
from modules.patents.models.application import PatentApplication


class TechnologyTransferRecord(TimeStampedModel):
    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="licensing_records",
    )
    applicant_user_id = models.IntegerField(db_index=True)
    request_type = models.CharField(max_length=50)
    partner_name = models.CharField(max_length=255)
    status = models.CharField(max_length=30, default="SUBMITTED")
    confidentiality_level = models.CharField(max_length=30, default="confidential")
    terms_summary = models.TextField(blank=True, default="")

    class Meta:
        db_table = "patents_tech_transfer"
