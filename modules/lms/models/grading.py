"""Submission grading and grade change audit models."""

from __future__ import annotations

from django.db import models
from django.db.models import Q

from modules.lms.domain.constants import GradeStatus


class SubmissionGrade(models.Model):
    STATUS_CHOICES = [(s, s) for s in GradeStatus.ALL]

    submission = models.OneToOneField(
        "lms.AssignmentSubmission",
        on_delete=models.CASCADE,
        related_name="grade",
    )
    points_awarded = models.DecimalField(max_digits=6, decimal_places=2)
    feedback_text = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=GradeStatus.DRAFT)
    graded_by = models.IntegerField()
    graded_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "lms_submission_grade"
        verbose_name = "Submission Grade"
        verbose_name_plural = "Submission Grades"
        indexes = [
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(points_awarded__gte=0),
                name="lms_grade_points_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"Grade for Submission {self.submission_id}: {self.points_awarded} ({self.status})"


class GradeChangeAudit(models.Model):
    grade = models.ForeignKey(
        SubmissionGrade,
        on_delete=models.CASCADE,
        related_name="change_audits",
    )
    submission_id = models.IntegerField(db_index=True)
    old_points = models.DecimalField(max_digits=6, decimal_places=2)
    new_points = models.DecimalField(max_digits=6, decimal_places=2)
    old_feedback = models.TextField(blank=True, default="")
    new_feedback = models.TextField(blank=True, default="")
    changed_by = models.IntegerField()
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "lms_grade_change_audit"
        verbose_name = "Grade Change Audit"
        verbose_name_plural = "Grade Change Audits"
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"Audit for Grade {self.grade_id} by User {self.changed_by}"
