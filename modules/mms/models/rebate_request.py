"""Rebate request (BR-MMS-021..025; UC-014/015; BW-MMS-05/06/07)."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class RebateRequest(TimeStampedModel, UserScopedModel):
    REASON_CHOICES = [
        ("medical", "Medical"),
        ("institute_leave", "Institute Leave"),
        ("family_function", "Family Function"),
        ("other", "Other"),
    ]
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]

    reason = models.CharField(max_length=24, choices=REASON_CHOICES)
    explanation = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    approved_start_date = models.DateField(null=True, blank=True)
    approved_end_date = models.DateField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "mms_rebate_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="rebate_student_status_idx"),
            models.Index(fields=["start_date", "end_date"], name="rebate_date_range_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="rebate_dates_ordered",
            ),
            models.CheckConstraint(
                condition=(
                    Q(decided_at__isnull=True, decided_by_user_id__isnull=True)
                    | Q(decided_at__isnull=False, decided_by_user_id__isnull=False)
                ),
                name="rebate_decision_paired",
            ),
        ]

    def __str__(self) -> str:
        return f"rebate:{self.pk}:{self.status}"
