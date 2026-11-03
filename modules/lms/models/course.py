from django.db import models
from core.db.mixins import TimeStampedModel
from modules.lms.domain.constants import Role


class Course(TimeStampedModel):
    class Meta:
        db_table = "lms_course"
        ordering = ["-academic_year", "semester", "code"]

    code = models.CharField(max_length=32, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    syllabus = models.TextField(blank=True, default="")
    schedule = models.CharField(max_length=255, blank=True, default="")
    academic_year = models.IntegerField()
    semester = models.IntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.code} - {self.title} ({self.academic_year} Sem {self.semester})"


class CourseMembership(TimeStampedModel):
    class Meta:
        db_table = "lms_course_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "user_id", "role"],
                name="unique_course_membership_role",
            )
        ]

    course = models.ForeignKey(
        "lms.Course",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(
        max_length=32,
        choices=Role.CHOICES,
        default=Role.STUDENT,
    )
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"User {self.user_id} as {self.role} in Course {self.course_id}"
