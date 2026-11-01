"""Department announcement models."""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel


class DepartmentAnnouncement(TimeStampedModel):
    """Department announcement or notice."""
    title = models.CharField(max_length=255)
    content = models.TextField()
    department = models.CharField(max_length=80, blank=True)
    target_audience = models.CharField(max_length=50, default="ALL")
    posted_by_id = models.IntegerField()
    posted_by_name = models.CharField(max_length=150)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        db_table = "department_announcement"
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self) -> str:
        return f"Announcement: {self.title[:40]}"
