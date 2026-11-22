from django.db import models
from django.db.models import Q

from modules.iaa.models._append_only import AppendOnlyModel


class TrailEntry(AppendOnlyModel):
    """Who did what, under which role, to which row (BR-503); immutable by construction."""

    RECORD = "record"
    ANOMALY = "anomaly"
    OBSERVATION = "observation"
    CONFIGURATION = "configuration"
    ENTITIES = [(e, e.title()) for e in (RECORD, ANOMALY, OBSERVATION, CONFIGURATION)]

    entity = models.CharField(max_length=16, choices=ENTITIES)
    entity_id = models.IntegerField()
    action = models.CharField(max_length=32)
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=64)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["entity", "entity_id", "created_at"],
                                name="iaa_trail_entity_idx")]


class Notification(AppendOnlyModel):
    """A dashboard notification for one person, or for everyone acting as one role (BR-504)."""

    recipient_user_id = models.IntegerField(null=True, blank=True)
    recipient_role = models.CharField(max_length=64, blank=True)
    kind = models.CharField(max_length=32)
    message = models.CharField(max_length=300)
    entity = models.CharField(max_length=16)
    entity_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(recipient_user_id__isnull=False) & Q(recipient_role=""))
                | (Q(recipient_user_id__isnull=True) & ~Q(recipient_role="")),
                name="iaa_notification_one_recipient"),
        ]
        indexes = [
            models.Index(fields=["recipient_user_id", "-created_at"], name="iaa_notify_user_idx"),
            models.Index(fields=["recipient_role", "-created_at"], name="iaa_notify_role_idx"),
        ]
