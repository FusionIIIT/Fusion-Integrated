"""Submission model."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class Submission(TimeStampedModel, UserScopedModel):
    """A student's submission for an assignment."""

    class SubmissionType(models.TextChoices):
        FILE = "file", "File"
        TEXT = "text", "Text"
        LINK = "link", "Link"

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        LATE = "late", "Late"
        MISSING = "missing", "Missing"

    assignment = models.ForeignKey(
        "lms.Assignment", on_delete=models.CASCADE, related_name="submissions",
    )
    submission_type = models.CharField(max_length=10, choices=SubmissionType.choices)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="lms/submissions/", blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUBMITTED)
    is_late = models.BooleanField(default=False)
    attempt_number = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "lms_submission"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "user_id", "attempt_number"],
                name="lms_sub_unique_attempt",
            ),
        ]
        indexes = [
            models.Index(fields=["assignment", "user_id"], name="lms_sub_asg_student"),
        ]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Submission {self.id} (assignment {self.assignment_id})"
