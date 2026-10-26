from django.db import models


class OutboxEvent(models.Model):
    topic = models.CharField(max_length=80)
    payload = models.JSONField()
    dedupe_key = models.CharField(max_length=160, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)

    class Meta:
        db_table = "outbox_event"
        indexes = [
            models.Index(
                fields=["id"],
                condition=models.Q(consumed_at__isnull=True),
                name="event_outbox_pending_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.topic} ({self.dedupe_key})"
