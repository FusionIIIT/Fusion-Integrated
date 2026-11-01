"""Yearly appraisal models (BR-HR-012 to BR-HR-015)."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.hreis.domain.appraisal import AppraisalStatus


class AppraisalSubmission(TimeStampedModel, UserScopedModel):
    """Annual performance appraisal submitted by faculty or staff."""

    user_id = models.IntegerField(db_index=True)
    academic_year = models.CharField(max_length=16, db_index=True)
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name.title()) for s in AppraisalStatus],
        default=AppraisalStatus.DRAFT.value,
        db_index=True,
    )
    content = models.JSONField(default=dict)
    assigned_reviewers = models.JSONField(default=list, blank=True)
    reviews = models.JSONField(default=list, blank=True)
    final_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    final_remarks = models.TextField(blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    is_immutable = models.BooleanField(default=False)

    class Meta:
        db_table = "hreis_appraisal_submission"
        verbose_name = "Appraisal Submission"
        verbose_name_plural = "Appraisal Submissions"
        unique_together = ("user_id", "academic_year")
        ordering = ["-academic_year", "-created_at"]

    def __str__(self) -> str:
        return f"Appraisal(user={self.user_id}, year={self.academic_year}, status={self.status})"
