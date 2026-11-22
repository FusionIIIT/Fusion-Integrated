from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.oap.domain import state_machines as sm


class SeminarRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        (sm.SEMINAR_AWAITING, "Awaiting scheduling"),
        (sm.SEMINAR_SCHEDULED, "Scheduled"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=sm.SEMINAR_AWAITING)

    class Meta:
        db_table = "oap_seminar_request"
        ordering = ["-created_at"]


class SeminarSchedule(TimeStampedModel):
    request = models.OneToOneField(
        SeminarRequest, on_delete=models.PROTECT, related_name="schedule"
    )
    scheduled_for = models.DateTimeField()
    venue = models.CharField(max_length=200)
    scheduled_by_user_id = models.IntegerField()
    scheduled_at = models.DateTimeField()

    class Meta:
        db_table = "oap_seminar_schedule"
        ordering = ["scheduled_for"]
