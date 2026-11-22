from django.db import models


class OapEvent(models.Model):
    """Append-only history of every state change. Corrections are new rows."""

    AGGREGATE_CHOICES = [
        ("leave", "Leave application"),
        ("bonafide", "Bonafide request"),
        ("no_dues", "No-dues case"),
        ("claim", "Assistantship claim"),
        ("seminar", "Seminar request"),
    ]

    aggregate = models.CharField(max_length=20, choices=AGGREGATE_CHOICES)
    aggregate_id = models.IntegerField()
    from_state = models.CharField(max_length=40, blank=True)
    to_state = models.CharField(max_length=40)
    actor_user_id = models.IntegerField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "oap_event"
        ordering = ["occurred_at", "id"]
        indexes = [models.Index(fields=["aggregate", "aggregate_id"])]

    def __str__(self) -> str:
        return f"{self.aggregate}#{self.aggregate_id}: {self.from_state} -> {self.to_state}"
