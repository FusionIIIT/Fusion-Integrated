"""Deregistration lifecycle (BR-MMS-012/013; UC-005/006/027; BW-MMS-03/04)."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class Deregistration(TimeStampedModel, UserScopedModel):
    STATUS = [
        ("pending", "Pending"),
        ("approved_awaiting_effective_date", "Approved — Awaiting Date"),
        ("rejected", "Rejected"),
    ]

    status = models.CharField(max_length=32, choices=STATUS, default="pending")
    #: Next calendar day after Caretaker approval, set by UC-027.
    effective_date = models.DateField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "mms_deregistration"
        indexes = [
            models.Index(fields=["user_id", "status"], name="dereg_student_status_idx"),
            models.Index(fields=["status", "effective_date"], name="deregistration_pending_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id"],
                condition=Q(status="pending"),
                name="one_pending_deregistration_per_student",
            ),
            models.CheckConstraint(
                condition=(
                    Q(decided_at__isnull=True, decided_by_user_id__isnull=True)
                    | Q(decided_at__isnull=False, decided_by_user_id__isnull=False)
                ),
                name="deregistration_decision_paired",
            ),
        ]

    def __str__(self) -> str:
        return f"deregistration:{self.pk}:{self.status}"
