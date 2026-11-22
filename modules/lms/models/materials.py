"""Course material model."""

from __future__ import annotations

from django.db import models

from modules.lms.domain.constants import MaterialStatus, MaterialType


class CourseMaterial(models.Model):
    TYPE_CHOICES = [(t, t) for t in MaterialType.ALL]
    STATUS_CHOICES = [(s, s) for s in MaterialStatus.ALL]

    course_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    material_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    content_text = models.TextField(blank=True, default="")
    external_url = models.URLField(blank=True, default="")
    file_attachment = models.FileField(upload_to="lms/materials/", blank=True, null=True)
    section_name = models.CharField(max_length=128, default="General")
    sort_order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=MaterialStatus.DRAFT)
    release_date = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lms_course_material"
        verbose_name = "Course Material"
        verbose_name_plural = "Course Materials"
        indexes = [
            models.Index(fields=["course_id", "status", "release_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.material_type})"
