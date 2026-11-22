"""Assignment submission model."""

from __future__ import annotations

from django.db import models

from modules.lms.domain.constants import SubmissionStatus, SubmissionType


class AssignmentSubmission(models.Model):
    TYPE_CHOICES = [(t, t) for t in SubmissionType.ALL]
    STATUS_CHOICES = [(s, s) for s in SubmissionStatus.ALL]

    assignment = models.ForeignKey(
        "lms.Assignment",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student_id = models.IntegerField(db_index=True)
    submission_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    content_text = models.TextField(blank=True, default="")
    content_link = models.URLField(blank=True, default="")
    file_attachment = models.FileField(upload_to="lms/submissions/", blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=SubmissionStatus.SUBMITTED
    )

    class Meta:
        db_table = "lms_assignment_submission"
        verbose_name = "Assignment Submission"
        verbose_name_plural = "Assignment Submissions"
        indexes = [
            models.Index(fields=["assignment", "student_id", "submitted_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"Submission {self.id} for Assignment {self.assignment_id} by Student {self.student_id}"
        )
