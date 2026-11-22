from django.db import models

from core.db.mixins import TimeStampedModel


class Notification(TimeStampedModel):
    CHANNEL_CHOICES = [("alert", "System alert"), ("email", "Email")]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("read", "Read"),
    ]

    recipient_user_id = models.IntegerField(db_index=True)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "oap_notification"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["channel", "status"])]

    def __str__(self) -> str:
        return f"{self.channel} to {self.recipient_user_id}: {self.subject}"


class ReminderPolicy(models.Model):
    """Effective-dated and never edited: a new row supersedes the old one."""

    effective_from = models.DateTimeField()
    after_hours = models.PositiveIntegerField()
    created_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "oap_reminder_policy"
        ordering = ["-effective_from"]

    def __str__(self) -> str:
        return f"Reminder after {self.after_hours}h from {self.effective_from:%Y-%m-%d}"
