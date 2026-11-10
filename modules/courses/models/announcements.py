"""Course Announcements models (CFR-LMS-005, BR-LMS-007, BR-LMS-008)."""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.courses.models.workspace import CourseWorkspace


class CourseAnnouncement(TimeStampedModel):
    """Course-scoped announcement posted by faculty (CFR-LMS-005)."""

    workspace = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_published = models.BooleanField(default=True, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "courses_announcement"
        ordering = ["-published_at", "-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["workspace", "is_published", "published_at"],
                name="courses_ann_ws_pub_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.workspace.code} - {self.title}"

