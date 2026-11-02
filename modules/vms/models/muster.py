"""Emergency muster: the roster, the roll-call and the eviction clock."""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class Muster(TimeStampedModel):
    STATUS = [("IN_PROGRESS", "In progress"), ("COMPLETED", "Completed")]
    TYPES = [("EMERGENCY", "Emergency"), ("DRILL", "Drill")]

    status = models.CharField(max_length=16, choices=STATUS,
                              default="IN_PROGRESS", db_index=True)
    muster_type = models.CharField(max_length=12, choices=TYPES,
                                   default="EMERGENCY")
    reason = models.CharField(max_length=255, blank=True)
    triggered_by_user_id = models.IntegerField()
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    #: Offline-capable snapshot of who was on site (VMS-CFR-018).
    roster_snapshot = models.JSONField(default=list, blank=True)
    summary = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "vms_muster"
        indexes = [
            models.Index(fields=["status", "started_at"],
                         name="vms_muster_status_idx"),
        ]

    def __str__(self) -> str:
        return f"muster#{self.id}:{self.status}"


class MusterEntry(TimeStampedModel):
    STATUS = [("UNACCOUNTED", "Unaccounted"), ("ACCOUNTED", "Accounted"),
              ("EVICTED", "Evicted")]

    muster = models.ForeignKey(Muster, on_delete=models.CASCADE,
                               related_name="entries")
    visit_id = models.IntegerField(db_index=True)
    visitor_id = models.IntegerField(db_index=True)
    host_user_id = models.IntegerField(null=True, blank=True)
    last_seen_zone = models.CharField(max_length=32, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS,
                              default="UNACCOUNTED")
    marked_present = models.BooleanField(default=False)
    marked_at = models.DateTimeField(null=True, blank=True)
    marked_by_user_id = models.IntegerField(null=True, blank=True)
    #: Minutes past the roster deadline observed at mark time (VMS-BR-045).
    extra_minutes = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "vms_muster_entry"
        constraints = [
            models.UniqueConstraint(fields=["muster", "visit_id"],
                                    name="vms_muster_entry_unique"),
        ]
        indexes = [
            models.Index(fields=["muster", "status"],
                         name="vms_muster_entry_status_idx"),
        ]

    def __str__(self) -> str:
        return f"entry:{self.visit_id}:{self.status}"
