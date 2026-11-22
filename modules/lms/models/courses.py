from django.db import models

from core.db.mixins import TimeStampedModel


class CourseWorkspace(TimeStampedModel):
    """Dedicated course workspace and home page (CFR-LMS-001, UC-LMS-001, BR-LMS-001)."""

    course_code = models.CharField(max_length=20, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    syllabus = models.TextField(blank=True)
    schedule = models.TextField(blank=True)
    instructor_user_id = models.IntegerField(db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "lms_course_workspace"
        indexes = [
            models.Index(fields=["course_code", "is_active"], name="lms_course_code_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.course_code} - {self.title}"


class CourseMembership(TimeStampedModel):
    """User enrollment and role linkage in a course (BR-LMS-001 to BR-LMS-004)."""

    ROLE_CHOICES = [
        ("student", "Student"),
        ("faculty", "Faculty"),
        ("ta", "Teaching Assistant"),
        ("observer", "Observer"),
    ]

    course = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    can_post_announcements = models.BooleanField(default=False)

    class Meta:
        db_table = "lms_course_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "user_id"],
                name="lms_unique_course_user_membership",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "role"], name="lms_user_role_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} in {self.course.course_code} as {self.role}"
