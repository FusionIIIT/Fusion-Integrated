from django.db import models

from core.db.mixins import TimeStampedModel
from modules.lms.models.courses import CourseWorkspace


class Assignment(TimeStampedModel):
    """Course assignment definition and lifecycle (CFR-LMS-004, UC-LMS-007)."""

    SUBMISSION_TYPE = [
        ("file", "File Upload"),
        ("text", "Text Entry"),
        ("link", "URL Link"),
    ]
    STATUS = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled for Release"),
        ("available", "Available for Submission"),
    ]

    course = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    points_possible = models.DecimalField(max_digits=5, decimal_places=2)
    submission_type = models.CharField(max_length=20, choices=SUBMISSION_TYPE)
    due_date = models.DateTimeField()

    status = models.CharField(max_length=20, choices=STATUS, default="draft", db_index=True)
    scheduled_release_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "lms_assignment"
        indexes = [
            models.Index(fields=["course", "status"], name="lms_asgn_course_status_idx"),
            models.Index(fields=["due_date"], name="lms_asgn_due_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.course.course_code}) [{self.status}]"
