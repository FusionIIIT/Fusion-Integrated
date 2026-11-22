from django.db import models

from core.db.mixins import TimeStampedModel


class PatentAuditEvent(TimeStampedModel):
    """Immutable audit trail for patent workflow transitions and actions."""

    application = models.ForeignKey(
        "pms.PatentApplication",
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    event_name = models.CharField(max_length=128, db_index=True)
    from_status = models.CharField(max_length=32, blank=True, default="")
    to_status = models.CharField(max_length=32, blank=True, default="")
    actor_user_id = models.IntegerField(db_index=True)
    payload = models.JSONField(default=dict)

    class Meta:
        db_table = "pms_audit_event"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_name} on App #{self.application_id} by User #{self.actor_user_id}"
