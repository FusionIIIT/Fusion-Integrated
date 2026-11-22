"""Course workspace and membership models."""

from __future__ import annotations

from django.db import models

from modules.lms.domain.constants import CourseRole, MembershipStatus


class CourseWorkspace(models.Model):
    course_id = models.IntegerField(unique=True, db_index=True)
    course_code = models.CharField(max_length=32)
    title = models.CharField(max_length=255)
    syllabus = models.TextField(blank=True, default="")
    schedule_info = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_course_workspace"
        verbose_name = "Course Workspace"
        verbose_name_plural = "Course Workspaces"

    def __str__(self) -> str:
        return f"{self.course_code}: {self.title}"


class CourseMembership(models.Model):
    ROLE_CHOICES = [(r, r) for r in CourseRole.ALL]
    STATUS_CHOICES = [(s, s) for s in MembershipStatus.ALL]

    course_id = models.IntegerField(db_index=True)
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=MembershipStatus.ACTIVE
    )
    can_post_announcement = models.BooleanField(default=False)
    can_grade = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lms_course_membership"
        verbose_name = "Course Membership"
        verbose_name_plural = "Course Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["course_id", "user_id", "role"],
                name="lms_unique_course_user_role",
            )
        ]

    def __str__(self) -> str:
        return f"Course {self.course_id} - User {self.user_id} ({self.role})"
