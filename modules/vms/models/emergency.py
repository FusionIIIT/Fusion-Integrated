"""Emergency muster and roll-call models."""

from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.vms.models.visitor import Pass, Visitor


class EmergencyMusterRoster(TimeStampedModel):
    """Snapshot roster of all on-site visitors during an emergency muster."""

    ACCOUNTABILITY_STATUS = [
        ("UNACCOUNTED", "Unaccounted"),
        ("ACCOUNTED", "Accounted"),
    ]

    muster_id = models.CharField(max_length=64, db_index=True)
    assembly_point = models.CharField(max_length=100)
    initiated_by_id = models.PositiveIntegerField()
    initiated_at = models.DateTimeField(db_index=True)
    visitor = models.ForeignKey(Visitor, on_delete=models.PROTECT, related_name="emergency_rosters")
    pass_record = models.ForeignKey(
        Pass, on_delete=models.PROTECT, related_name="emergency_rosters"
    )
    check_in_time = models.DateTimeField()
    accountability_status = models.CharField(
        max_length=20, choices=ACCOUNTABILITY_STATUS, default="UNACCOUNTED", db_index=True
    )
    accounted_at = models.DateTimeField(null=True, blank=True)
    accounted_by_id = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-initiated_at", "accountability_status"]
        indexes = [
            models.Index(fields=["muster_id", "accountability_status"]),
        ]

    def __str__(self) -> str:
        return f"Muster {self.muster_id}: {self.visitor.name} - {self.accountability_status}"
