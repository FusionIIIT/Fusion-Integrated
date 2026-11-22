from django.db import models

from core.db.mixins import TimeStampedModel
from modules.lms.models.courses import CourseWorkspace


class CourseMaterial(TimeStampedModel):
    """Course materials organized by weekly section (CFR-LMS-002, UC-LMS-003)."""

    MATERIAL_TYPE = [
        ("file", "File Document"),
        ("link", "External Link"),
        ("note", "Lecture Note"),
    ]
    STATUS = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
    ]

    course = models.ForeignKey(
        CourseWorkspace,
        on_delete=models.CASCADE,
        related_name="materials",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    section_or_week = models.CharField(max_length=100)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE, default="file")
    file_url = models.CharField(max_length=500, blank=True)
    content = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default="draft", db_index=True)
    scheduled_release_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    uploaded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "lms_course_material"
        indexes = [
            models.Index(fields=["course", "status"], name="lms_mat_course_status_idx"),
            models.Index(fields=["section_or_week"], name="lms_mat_section_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.status.upper()}] {self.title} ({self.course.course_code})"
