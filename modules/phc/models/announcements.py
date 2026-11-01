"""Health announcements / advisories (CFR-PHC-009, AFR-PHC-033; UC-PHC-12)."""
from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class HealthAnnouncement(TimeStampedModel):
    PRIORITY_CHOICES = [
        ("Normal", "Normal"),
        ("Urgent", "Urgent"),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Normal")
    published_date = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    published_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_announcements"
        ordering = ["-priority", "-published_date"]

    def __str__(self) -> str:
        return f"[{self.priority}] {self.title}"
