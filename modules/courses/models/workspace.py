"""Course Workspace and Membership models."""
from django.db import models

from core.db.mixins import TimeStampedModel


class CourseWorkspace(TimeStampedModel):
    code = models.CharField(max_length=32, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    semester = models.CharField(max_length=32)
    academic_year = models.CharField(max_length=16)
    credits = models.PositiveSmallIntegerField(default=4)
    syllabus = models.TextField(blank=True)
    schedule = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    allow_ta_announcements = models.BooleanField(default=False)

    class Meta:
        db_table = "courses_workspace"
        unique_together = [("code", "semester", "academic_year")]
        indexes = [
            models.Index(fields=["code", "semester", "academic_year"], name="courses_ws_lookup_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.title} ({self.semester})"


class CourseMembership(TimeStampedModel):
    ROLE_CHOICES = [
        ("instructor", "Instructor"),
        ("ta", "Teaching Assistant"),
        ("student", "Student"),
        ("observer", "Observer"),
    ]

    workspace = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, db_index=True)

    class Meta:
        db_table = "courses_membership"
        unique_together = [("workspace", "user_id")]
        indexes = [
            models.Index(fields=["user_id", "role"], name="courses_mem_user_role_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} in {self.workspace.code} as {self.role}"
