"""LMS Course Workspace data models.

User ids deliberately remain plain integers: IAM owns identities and directory
facts, so course memberships must not introduce cross-module foreign keys
(ADR-0013).
"""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.lms.domain.entities import CourseRole, CourseStatus


class Course(TimeStampedModel):
    """A course offering workspace in the LMS."""

    STATUS_CHOICES = [
        (CourseStatus.DRAFT, "Draft"),
        (CourseStatus.PUBLISHED, "Published"),
    ]

    code = models.CharField(max_length=32, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    syllabus = models.TextField(blank=True)
    schedule = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=CourseStatus.PUBLISHED)

    class Meta:
        db_table = "lms_course"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.title}"


class CourseMembership(TimeStampedModel):
    """Membership of an authenticated user in a course workspace.

    Governs access and role-dependent capabilities (Faculty, TA, Student, Observer)
    in compliance with BR-LMS-001, BR-LMS-002, BR-LMS-003, and BR-LMS-004.
    """

    ROLE_CHOICES = [
        (CourseRole.FACULTY, "Faculty"),
        (CourseRole.STUDENT, "Student"),
        (CourseRole.TA, "Teaching Assistant"),
        (CourseRole.OBSERVER, "Observer"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="memberships")
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)

    class Meta:
        db_table = "lms_course_membership"
        ordering = ["course", "role", "user_id"]
        constraints = [
            models.UniqueConstraint(fields=["course", "user_id"], name="lms_membership_unique"),
        ]
        indexes = [
            models.Index(fields=["user_id", "role"], name="lms_mem_user_role_idx"),
            models.Index(fields=["course", "role"], name="lms_mem_course_role_idx"),
        ]

    def __str__(self) -> str:
        return f"User({self.user_id}) in {self.course.code} as {self.role}"
