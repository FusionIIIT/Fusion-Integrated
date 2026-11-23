from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.oap.domain import state_machines as sm


class LeaveApplication(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        (sm.LEAVE_SUBMITTED, "Submitted"),
        (sm.LEAVE_APPROVED, "Approved"),
        (sm.LEAVE_REJECTED, "Rejected"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=sm.LEAVE_SUBMITTED)
    reason = models.TextField()
    from_date = models.DateField()
    to_date = models.DateField()
    supporting_document_link = models.URLField(max_length=500, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "oap_leave_application"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(to_date__gte=models.F("from_date")), name="oap_leave_dates_ordered"
            ),
        ]
        indexes = [models.Index(fields=["status", "created_at"])]
