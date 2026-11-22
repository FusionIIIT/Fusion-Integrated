"""Course Grades and Evaluation models (CFR-LMS-010, CFR-LMS-011, CFR-LMS-012, CFR-LMS-013, BR-LMS-015, BR-LMS-016, BR-LMS-017, BR-LMS-018, BR-LMS-019)."""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.courses.models.assignments import CourseAssignment
from modules.courses.models.submissions import CourseSubmission
from modules.courses.models.workspace import CourseWorkspace


class CourseGrade(TimeStampedModel):
    """Evaluation, marks, and feedback for a student submission (UC-LMS-012, UC-LMS-013)."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("released", "Released"),
    ]

    workspace = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="grades",
    )
    assignment = models.ForeignKey(
        CourseAssignment,
        on_delete=models.CASCADE,
        related_name="grades",
    )
    submission = models.OneToOneField(
        CourseSubmission,
        on_delete=models.CASCADE,
        related_name="grade",
    )
    student_id = models.IntegerField(db_index=True)
    grader_id = models.IntegerField(db_index=True)
    score = models.DecimalField(max_digits=6, decimal_places=2)
    feedback = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="draft",
        db_index=True,
    )
    graded_at = models.DateTimeField(db_index=True)
    released_at = models.DateTimeField(null=True, blank=True, db_index=True)
    released_by_id = models.IntegerField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "courses_grade"
        ordering = ["-graded_at", "-id"]
        indexes = [
            models.Index(
                fields=["assignment", "status"],
                name="courses_grd_asgn_stat_idx",
            ),
            models.Index(
                fields=["workspace", "student_id", "status"],
                name="courses_grd_ws_stud_stat_idx",
            ),
            models.Index(
                fields=["assignment", "student_id"],
                name="courses_grd_asgn_stud_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["submission"],
                name="courses_grade_submission_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"Grade {self.score} for Submission {self.submission_id} ({self.status})"


class CourseGradeAudit(models.Model):
    """Audit log for grading actions and post-release grade modifications (BR-LMS-019)."""

    workspace = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="grade_audit_logs",
    )
    grade = models.ForeignKey(
        CourseGrade,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    actor_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=32, db_index=True)
    score_before = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    score_after = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feedback_before = models.TextField(blank=True)
    feedback_after = models.TextField(blank=True)
    status_before = models.CharField(max_length=16, blank=True)
    status_after = models.CharField(max_length=16, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "courses_grade_audit"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["grade", "created_at"],
                name="courses_ga_grd_crt_idx",
            ),
            models.Index(
                fields=["workspace", "actor_id"],
                name="courses_ga_ws_act_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Audit {self.action} on Grade {self.grade_id} by Actor {self.actor_id} at {self.created_at}"
