from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.iaa.domain import state_machine as sm
from modules.iaa.domain.policy import ANOMALY_CATEGORIES


class Anomaly(TimeStampedModel):
    MANUAL = "manual"
    AUTOMATIC = "automatic"

    record = models.ForeignKey("iaa.FinancialRecord", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="anomalies")
    category = models.CharField(max_length=16, choices=[(c, c.title()) for c in ANOMALY_CATEGORIES])
    source = models.CharField(max_length=10, choices=[(MANUAL, "Manual"), (AUTOMATIC, "Automatic")])
    description = models.TextField()
    status = models.CharField(max_length=10, choices=[(s, s.title()) for s in sm.ANOMALY_STATES],
                              default=sm.ANOMALY_OPEN)
    resolver_chain = models.JSONField(default=list)
    resolver_level = models.PositiveSmallIntegerField(default=0)
    assigned_role = models.CharField(max_length=64)
    raised_by = models.IntegerField(null=True, blank=True)
    raised_role = models.CharField(max_length=64)
    resolved_by = models.IntegerField(null=True, blank=True)
    resolved_role = models.CharField(max_length=64, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["record", "category"],
                condition=Q(source="automatic") & ~Q(status="resolved"),
                name="iaa_anomaly_one_live_automatic"),
            models.CheckConstraint(condition=Q(status__in=sm.ANOMALY_STATES),
                                   name="iaa_anomaly_status_known"),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="iaa_anomaly_status_idx"),
            models.Index(fields=["record", "status"], name="iaa_anomaly_record_idx"),
            models.Index(fields=["assigned_role", "status"], name="iaa_anomaly_assigned_idx"),
        ]
