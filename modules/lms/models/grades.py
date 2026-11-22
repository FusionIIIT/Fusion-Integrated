from django.db import models

from core.db.mixins import TimeStampedModel
from modules.lms.models.submissions import StudentSubmission


class Grade(TimeStampedModel):
    """Grading record and feedback lifecycle (CFR-LMS-006, UC-LMS-012, BR-LMS-015 to BR-LMS-018)."""

    STATUS = [
        ("draft", "Draft (Hidden from Student)"),
        ("released", "Released (Visible to Student)"),
    ]

    submission = models.OneToOneField(
        StudentSubmission,
        on_delete=models.CASCADE,
        related_name="grade",
    )
    points = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="draft", db_index=True)

    graded_by_user_id = models.IntegerField()
    graded_at = models.DateTimeField(auto_now=True)
    released_at = models.DateTimeField(null=True, blank=True)
    released_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "lms_grade"
        indexes = [
            models.Index(
                fields=["status", "graded_by_user_id"], name="lms_grade_status_grader_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"Grade for sub #{self.submission_id}: {self.points} pts [{self.status}]"


class GradeChangeLog(TimeStampedModel):
    """Audit log for post-release grade modifications (BR-LMS-019, Section 3.6)."""

    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="change_logs",
    )
    old_points = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    new_points = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.CharField(max_length=500, blank=True)
    changed_by_user_id = models.IntegerField()
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lms_grade_change_log"
        indexes = [
            models.Index(fields=["grade", "-changed_at"], name="lms_gcl_grade_changed_idx"),
        ]

    def __str__(self) -> str:
        return f"GradeChange #{self.grade_id}: {self.old_points}->{self.new_points}"
