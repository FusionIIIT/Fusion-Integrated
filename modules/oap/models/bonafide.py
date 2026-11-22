from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.oap.domain import state_machines as sm


class BonafideRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        (sm.BONAFIDE_SUBMITTED, "Submitted"),
        (sm.BONAFIDE_APPROVED, "Approved"),
        (sm.BONAFIDE_REJECTED, "Rejected"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=sm.BONAFIDE_SUBMITTED)
    purpose = models.TextField(blank=True)
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "oap_bonafide_request"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]
