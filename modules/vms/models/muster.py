"""VMS Emergency Muster and Roll-call Models."""

from django.db import models

from core.db.mixins import TimeStampedModel


class EmergencyMuster(TimeStampedModel):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("resolved", "Resolved"),
    ]

    muster_code = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default="active", db_index=True
    )
    triggered_by = models.IntegerField()
    headcount_total = models.IntegerField(default=0)
    headcount_accounted = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vms_emergency_muster"
        indexes = [
            models.Index(fields=["status", "started_at"], name="vms_em_stat_start_idx"),
        ]

    def __str__(self) -> str:
        return f"Muster {self.muster_code} ({self.status})"
