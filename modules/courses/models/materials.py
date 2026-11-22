"""Course Materials and Sections models (CFR-LMS-003, CFR-LMS-004)."""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel
from modules.courses.models.workspace import CourseWorkspace


class CourseMaterialSection(TimeStampedModel):
    """Section or module grouping for course materials (AFR-LMS-003.2)."""

    workspace = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "courses_material_section"
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["workspace", "sort_order"], name="courses_sec_ws_sort_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.workspace.code} - {self.title}"


class CourseMaterial(TimeStampedModel):
    """Course learning material item (file, external link, or note)."""

    MATERIAL_TYPE_CHOICES = [
        ("file", "File"),
        ("link", "External Link"),
        ("note", "Note"),
    ]

    workspace = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="materials",
    )
    section = models.ForeignKey(
        CourseMaterialSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(
        max_length=16,
        choices=MATERIAL_TYPE_CHOICES,
        default="note",
        db_index=True,
    )
    file = models.FileField(
        upload_to="courses/materials/%Y/%m/",
        blank=True,
        null=True,
        max_length=255,
    )
    filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=120, blank=True)
    link_url = models.URLField(max_length=500, blank=True)
    content = models.TextField(blank=True)
    is_published = models.BooleanField(default=True, db_index=True)
    release_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by_id = models.IntegerField(db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "courses_material"
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(
                fields=["workspace", "is_published", "release_at"],
                name="courses_mat_pub_rel_idx",
            ),
            models.Index(
                fields=["workspace", "section", "sort_order"],
                name="courses_mat_ws_sec_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.workspace.code} - {self.title} ({self.material_type})"

    @property
    def is_available(self) -> bool:
        """True if material is published and release date has passed (BR-LMS-005, BR-LMS-006)."""
        if not self.is_published:
            return False
        if self.release_at is None:
            return True
        return self.release_at <= timezone.now()

    @property
    def is_scheduled(self) -> bool:
        """True if configured for a future release date (AFR-LMS-003.3)."""
        return self.release_at is not None and self.release_at > timezone.now()

