"""Access policy and zone elevation models."""

from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.vms.models.visitor import Pass


class AccessPolicy(TimeStampedModel):
    """Versioned campus visiting policies."""

    version = models.PositiveIntegerField(unique=True)
    visiting_hours_start = models.TimeField(default="08:00")
    visiting_hours_end = models.TimeField(default="20:00")
    max_duration_hours = models.PositiveIntegerField(default=12)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    policy_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self) -> str:
        status = "Published" if self.is_published else "Draft"
        return f"AccessPolicy v{self.version} ({status})"


class ZoneElevation(TimeStampedModel):
    """Temporary time-boxed zone elevation granted to a visitor pass."""

    pass_record = models.ForeignKey(Pass, on_delete=models.PROTECT, related_name="zone_elevations")
    zone_name = models.CharField(max_length=100)
    valid_from = models.DateTimeField(db_index=True)
    valid_to = models.DateTimeField(db_index=True)
    elevated_by_id = models.PositiveIntegerField()
    reason = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ZoneElevation for Pass {self.pass_record_id} to {self.zone_name}"
