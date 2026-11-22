"""Course materials model."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class CourseMaterial(TimeStampedModel, UserScopedModel):
    """A course material (file, link, or note)."""

    class MaterialType(models.TextChoices):
        FILE = "file", "File"
        LINK = "link", "Link"
        NOTE = "note", "Note"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        SCHEDULED = "scheduled", "Scheduled"

    course_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    material_type = models.CharField(max_length=10, choices=MaterialType.choices)
    content = models.TextField(blank=True)  # link URL or note text
    file = models.FileField(upload_to="lms/materials/", blank=True, null=True)
    section = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    release_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lms_course_material"
        indexes = [
            models.Index(
                fields=["course_id", "status", "release_at"],
                name="lms_mat_course_status_rel",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"
