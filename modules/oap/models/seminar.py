from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.oap.domain import constants as c


class GraduateSeminar(TimeStampedModel, UserScopedModel):
    """Graduate seminar scheduling request and schedule model (OA-UC-51, OA-UC-53, BW-OAP-09)."""

    title = models.CharField(max_length=255)
    abstract = models.TextField()
    preferred_dates = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=40,
        choices=[(s, s) for s in c.SEMINAR_STATES],
        default=c.SEMINAR_AWAITING_SCHEDULING,
        db_index=True,
    )

    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.CharField(max_length=50, blank=True)
    venue = models.CharField(max_length=100, blank=True)
    coordinator_user_id = models.IntegerField(null=True, blank=True)
    scheduled_by_user_id = models.IntegerField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
