"""Course Submissions models (CFR-LMS-006, BR-LMS-012, BR-LMS-013, BR-LMS-014)."""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.courses.models.assignments import CourseAssignment
from modules.courses.models.workspace import CourseWorkspace


class CourseSubmission(TimeStampedModel):
    """Student submission for a course assignment (UC-LMS-010, BR-LMS-012)."""

    SUBMISSION_TYPE_CHOICES = [
        ("file", "File"),
        ("text", "Text"),
        ("link", "External Link"),
    ]

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("late", "Submitted Late"),
    ]

    workspace = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    assignment = models.ForeignKey(
        CourseAssignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student_id = models.IntegerField(db_index=True)
    submission_type = models.CharField(
        max_length=16,
        choices=SUBMISSION_TYPE_CHOICES,
        default="file",
        db_index=True,
    )
    file = models.FileField(
        upload_to="courses/submissions/%Y/%m/",
        blank=True,
        null=True,
        max_length=255,
    )
    filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=120, blank=True)
    content = models.TextField(blank=True)
    link_url = models.URLField(max_length=500, blank=True)
    submitted_at = models.DateTimeField(db_index=True)
    is_late = models.BooleanField(default=False, db_index=True)
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        default="submitted",
        db_index=True,
    )

    class Meta:
        db_table = "courses_submission"
        ordering = ["-submitted_at", "-id"]
        indexes = [
            models.Index(
                fields=["assignment", "student_id"],
                name="courses_sub_asgn_stud_idx",
            ),
            models.Index(
                fields=["workspace", "student_id"],
                name="courses_sub_ws_stud_idx",
            ),
            models.Index(
                fields=["assignment", "submitted_at"],
                name="courses_sub_asgn_sub_idx",
            ),
            models.Index(
                fields=["assignment", "is_late"],
                name="courses_sub_asgn_late_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student_id"],
                name="courses_sub_asgn_stud_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.assignment.title} - Student {self.student_id} ({self.status})"
