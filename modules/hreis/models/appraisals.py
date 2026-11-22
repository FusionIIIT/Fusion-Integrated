"""Annual appraisal, reviewer route and immutable final archive reference."""

from django.db import models


class AppraisalDetail(models.Model):
    request = models.OneToOneField("HRRequest", on_delete=models.PROTECT, related_name="appraisal")
    employee_record = models.ForeignKey(
        "EmployeeServiceRecord",
        on_delete=models.PROTECT,
        related_name="appraisals",
    )
    period_key = models.CharField(max_length=80)
    reviewer_user_ids = models.JSONField(default=list)
    submitted_form = models.JSONField(default=dict)
    archive_reference = models.CharField(max_length=300, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "hreis_appraisal"
        constraints = [
            models.UniqueConstraint(
                fields=["employee_record", "period_key"],
                name="hr_appraisal_record_period_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["period_key"], name="hr_appraisal_period_idx"),
        ]

    def __str__(self) -> str:
        return f"Appraisal {self.request_id} ({self.period_key})"
