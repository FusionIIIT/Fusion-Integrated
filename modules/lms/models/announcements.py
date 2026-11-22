from django.db import models

from core.db.mixins import TimeStampedModel
from modules.lms.models.courses import CourseWorkspace


class CourseAnnouncement(TimeStampedModel):
    """Course-wide announcements with timestamps (CFR-LMS-003, UC-LMS-005)."""

    course = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    posted_by_user_id = models.IntegerField(db_index=True)
    is_ta_announcement = models.BooleanField(default=False)
    posted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lms_course_announcement"
        indexes = [
            models.Index(fields=["course", "-posted_at"], name="lms_ann_course_posted_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} - {self.course.course_code} ({self.posted_at:%Y-%m-%d})"
