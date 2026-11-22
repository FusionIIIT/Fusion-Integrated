from django.db import models

from core.db.mixins import TimeStampedModel
from modules.patents.models.application import PatentApplication


class OfficeActionRecord(TimeStampedModel):
    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="office_actions",
    )
    action_code = models.CharField(max_length=100)
    issuing_authority = models.CharField(max_length=100)
    issued_date = models.DateField()
    response_deadline = models.DateField()
    status = models.CharField(max_length=30, default="RECORDED")
    requires_applicant_review = models.BooleanField(default=False)
    response_summary = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "patents_office_action"
