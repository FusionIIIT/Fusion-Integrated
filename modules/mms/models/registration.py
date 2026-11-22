"""Registration lifecycle (BR-MMS-009/010/012; UC-003/004; BW-MMS-01/02)."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class Registration(TimeStampedModel, UserScopedModel):
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]

    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "mms_registration"
        indexes = [
            models.Index(fields=["user_id", "status"], name="reg_student_status_idx"),
            models.Index(fields=["status", "submitted_at"], name="registration_pending_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id"],
                condition=Q(status="pending"),
                name="one_pending_registration_per_student",
            ),
            models.CheckConstraint(
                condition=(
                    Q(decided_at__isnull=True, decided_by_user_id__isnull=True)
                    | Q(decided_at__isnull=False, decided_by_user_id__isnull=False)
                ),
                name="registration_decision_paired",
            ),
        ]

    def __str__(self) -> str:
        return f"registration:{self.pk}:{self.status}"
