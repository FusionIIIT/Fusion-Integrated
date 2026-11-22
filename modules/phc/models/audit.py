from django.db import models

from core.db.mixins import TimeStampedModel


class PHCAuditEvent(TimeStampedModel):
    actor_user_id = models.PositiveBigIntegerField()
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=60)
    object_id = models.PositiveBigIntegerField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "phc_audit_event"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["object_type", "object_id", "created_at"],
                         name="phc_audit_object_idx"),
            models.Index(fields=["actor_user_id", "-created_at"],
                         name="phc_audit_actor_idx"),
        ]
