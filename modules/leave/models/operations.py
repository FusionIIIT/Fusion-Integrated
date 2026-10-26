"""What the module does on its own: notifications, SLA events and year-end runs."""
from django.db import models

from core.db.mixins import TimeStampedModel


class Outbox(TimeStampedModel):
    """Written in the same transaction as its cause and drained by a worker."""

    STATUS = [("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"),
              ("failed", "Failed"), ("undeliverable", "Undeliverable")]

    topic = models.CharField(max_length=40, db_index=True)
    dedupe_key = models.CharField(max_length=160, unique=True)
    recipient_user_id = models.IntegerField(null=True, blank=True)
    #: Expanded to its holders at send time, so whoever holds the post then is told.
    recipient_designation = models.CharField(max_length=155, blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=14, choices=STATUS, default="pending", db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_outbox"
        indexes = [models.Index(fields=["status", "created_at"], name="leave_outbox_queue_idx")]

    def __str__(self) -> str:
        return f"{self.topic} {self.status}"


class SlaEvent(models.Model):
    """BR-EL-032/033: the log of every reminder and escalation actually issued."""

    task = models.ForeignKey("leave.Task", on_delete=models.CASCADE, related_name="sla_events")
    kind = models.CharField(max_length=10)
    action = models.CharField(max_length=10, blank=True)
    from_designation = models.CharField(max_length=155, blank=True)
    to_designation = models.CharField(max_length=155, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_sla_event"
        constraints = [models.UniqueConstraint(fields=["task", "kind"],
                                               name="leave_sla_event_once")]

    def __str__(self) -> str:
        return f"task#{self.task_id} {self.kind}"


class YearEndRun(TimeStampedModel):
    STATUS = [("running", "Running"), ("completed", "Completed"),
              ("completed_with_exceptions", "Completed with exceptions")]

    year = models.PositiveSmallIntegerField(unique=True)
    status = models.CharField(max_length=28, choices=STATUS, default="running")
    accounts_processed = models.PositiveIntegerField(default=0)
    entries_written = models.PositiveIntegerField(default=0)
    exceptions = models.JSONField(default=list)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_year_end_run"
        ordering = ["-year"]

    def __str__(self) -> str:
        return f"year-end {self.year} {self.status}"
