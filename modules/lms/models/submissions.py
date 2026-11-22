from django.db import models

from core.db.mixins import TimeStampedModel
from modules.lms.models.assignments import Assignment


class StudentSubmission(TimeStampedModel):
    """Student submission against an assignment (CFR-LMS-005, UC-LMS-010)."""

    SUBMISSION_TYPE = Assignment.SUBMISSION_TYPE
    STATUS = [
        ("submitted", "Submitted"),
        ("late", "Late Submission"),
        ("missing", "Missing"),
    ]

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student_user_id = models.IntegerField(db_index=True)
    submission_type = models.CharField(max_length=20, choices=SUBMISSION_TYPE)
    submission_content = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS, default="submitted", db_index=True)

    class Meta:
        db_table = "lms_student_submission"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student_user_id"],
                name="lms_unique_assignment_submission",
            ),
        ]
        indexes = [
            models.Index(fields=["student_user_id", "status"], name="lms_sub_student_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Submission by u{self.student_user_id} on {self.assignment.title}"
