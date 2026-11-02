from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel
from modules.lms.domain.constants import (
    ContentStatus,
    GradeAction,
    GradeStatus,
    SubmissionStatus,
    SubmissionType,
)


class Assignment(TimeStampedModel):
    class Meta:
        db_table = "lms_assignment"
        ordering = ["-due_date", "-created_at"]

    course = models.ForeignKey(
        "lms.Course",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    author_user_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True, default="")
    submission_type = models.CharField(
        max_length=32,
        choices=SubmissionType.CHOICES,
        default=SubmissionType.FILE,
    )
    points_possible = models.PositiveIntegerField(default=100)
    due_date = models.DateTimeField(null=True, blank=True)
    release_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=ContentStatus.CHOICES,
        default=ContentStatus.DRAFT,
    )

    def __str__(self) -> str:
        return f"Assignment: {self.title} in {self.course.code}"


class Submission(TimeStampedModel):
    class Meta:
        db_table = "lms_submission"
        ordering = ["-submitted_at", "-version"]

    assignment = models.ForeignKey(
        "lms.Assignment",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student_user_id = models.IntegerField(db_index=True)
    version = models.PositiveIntegerField(default=1)
    submission_type = models.CharField(
        max_length=32,
        choices=SubmissionType.CHOICES,
    )
    content_text = models.TextField(blank=True, default="")
    file_storage_key = models.CharField(max_length=512, blank=True, default="")
    link_url = models.URLField(max_length=1024, blank=True, default="")
    submitted_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=32,
        choices=SubmissionStatus.CHOICES,
        default=SubmissionStatus.SUBMITTED,
    )

    def __str__(self) -> str:
        return f"Submission v{self.version} by User {self.student_user_id} for {self.assignment_id}"


class Grade(TimeStampedModel):
    class Meta:
        db_table = "lms_grade"

    submission = models.OneToOneField(
        "lms.Submission",
        on_delete=models.CASCADE,
        related_name="grade",
    )
    assessor_user_id = models.IntegerField(db_index=True)
    assessor_role = models.CharField(max_length=32)
    points_awarded = models.PositiveIntegerField(null=True, blank=True)
    feedback_text = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=32,
        choices=GradeStatus.CHOICES,
        default=GradeStatus.DRAFT,
    )
    released_at = models.DateTimeField(null=True, blank=True)
    released_by_user_id = models.IntegerField(null=True, blank=True, db_index=True)

    def __str__(self) -> str:
        return f"Grade for Submission {self.submission_id}: {self.points_awarded} ({self.status})"


class GradeAuditLog(models.Model):
    class Meta:
        db_table = "lms_grade_audit_log"
        ordering = ["-changed_at"]

    grade = models.ForeignKey(
        "lms.Grade",
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    assessor_user_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=32, choices=GradeAction.CHOICES)
    previous_points = models.PositiveIntegerField(null=True, blank=True)
    new_points = models.PositiveIntegerField(null=True, blank=True)
    previous_feedback = models.TextField(blank=True, default="")
    new_feedback = models.TextField(blank=True, default="")
    reason = models.TextField(blank=True, default="")
    changed_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"AuditLog on Grade {self.grade_id} by User {self.assessor_user_id}: {self.action} at {self.changed_at}"
