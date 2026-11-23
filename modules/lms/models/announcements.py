"""Course announcements model."""

from __future__ import annotations

from django.db import models


class CourseAnnouncement(models.Model):
    course_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    author_id = models.IntegerField()
    author_role = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lms_course_announcement"
        verbose_name = "Course Announcement"
        verbose_name_plural = "Course Announcements"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} (Course {self.course_id})"
