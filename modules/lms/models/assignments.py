"""Assignment model."""
from django.core.validators import MinValueValidator
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class Assignment(TimeStampedModel, UserScopedModel):
    """A course assignment."""

    class SubmissionType(models.TextChoices):
        FILE = "file", "File"
        TEXT = "text", "Text"
        LINK = "link", "Link"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        SCHEDULED = "scheduled", "Scheduled"
        AVAILABLE = "available", "Available"

    course_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    due_at = models.DateTimeField()
    submission_type = models.CharField(max_length=10, choices=SubmissionType.choices)
    points_possible = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    release_at = models.DateTimeField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "lms_assignment"
        indexes = [
            models.Index(fields=["course_id", "status"], name="lms_asg_course_status"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"
