"""Grade model."""
from django.core.validators import MinValueValidator
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class Grade(TimeStampedModel, UserScopedModel):
    """A grade for a submission."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        RELEASED = "released", "Released"

    submission = models.OneToOneField(
        "lms.Submission", on_delete=models.CASCADE, related_name="grade",
    )
    points = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    graded_by = models.IntegerField(db_index=True)  # user_id
    graded_at = models.DateTimeField(auto_now_add=True)
    released_by = models.IntegerField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lms_grade"
        indexes = [
            models.Index(fields=["submission"], name="lms_grade_submission"),
            models.Index(fields=["status"], name="lms_grade_status"),
        ]

    def __str__(self):
        return f"Grade {self.id} ({self.status})"


class GradeAudit(models.Model):
    """Audit log for post-release grade changes."""

    grade = models.ForeignKey("lms.Grade", on_delete=models.CASCADE, related_name="audits")
    changed_by = models.IntegerField(db_index=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    old_points = models.PositiveIntegerField(null=True, blank=True)
    new_points = models.PositiveIntegerField(null=True, blank=True)
    old_feedback = models.TextField(blank=True)
    new_feedback = models.TextField(blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        db_table = "lms_grade_audit"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"Audit {self.id} (grade {self.grade_id})"
