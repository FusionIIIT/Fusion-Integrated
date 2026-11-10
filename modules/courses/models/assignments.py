"""Course Assignments models (CFR-LMS-006, BR-LMS-009, BR-LMS-010)."""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel
from modules.courses.models.workspace import CourseWorkspace


class CourseAssignment(TimeStampedModel):
    """Course-scoped assignment item (CFR-LMS-006, BR-LMS-010)."""

    workspace = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "courses_assignment"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["workspace", "is_published", "created_at"],
                name="courses_asgn_ws_pub_idx",
            ),
            models.Index(
                fields=["workspace", "is_published", "due_at"],
                name="courses_asgn_ws_due_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.workspace.code} - {self.title}"

    @property
    def has_passed(self) -> bool:
        """True if a deadline is configured and has passed (CFR-LMS-006)."""
        if self.due_at is None:
            return False
        return self.due_at < timezone.now()
