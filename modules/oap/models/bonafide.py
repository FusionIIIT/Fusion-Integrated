from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.oap.domain import constants as c


class BonafideRequest(TimeStampedModel, UserScopedModel):
    """Bonafide certificate request model (OA-UC-11, OA-UC-12, BW-OAP-03, BW-OAP-04)."""

    purpose = models.CharField(max_length=255)
    details = models.TextField(blank=True)

    status = models.CharField(
        max_length=60,
        choices=[(s, s) for s in c.BONAFIDE_STATES],
        default=c.BONAFIDE_SUBMITTED,
        db_index=True,
    )
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    certificate_number = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]
