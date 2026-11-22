"""Course announcements model."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class Announcement(TimeStampedModel, UserScopedModel):
    """A course announcement."""

    course_id = models.IntegerField(db_index=True)
    content = models.TextField()
    is_pinned = models.BooleanField(default=False)

    class Meta:
        db_table = "lms_announcement"
        indexes = [
            models.Index(fields=["course_id", "-created_at"], name="lms_ann_course_created"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Announcement {self.id} (course {self.course_id})"
