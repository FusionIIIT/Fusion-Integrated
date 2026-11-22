from django.db import models
from core.db.mixins import TimeStampedModel
from modules.lms.domain.constants import ContentStatus, MaterialKind


class ModuleSection(TimeStampedModel):
    class Meta:
        db_table = "lms_module_section"
        ordering = ["order", "id"]

    course = models.ForeignKey(
        "lms.Course",
        on_delete=models.CASCADE,
        related_name="sections",
    )
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.course.code} Section: {self.title}"


class CourseMaterial(TimeStampedModel):
    class Meta:
        db_table = "lms_course_material"

    section = models.ForeignKey(
        "lms.ModuleSection",
        on_delete=models.CASCADE,
        related_name="materials",
    )
    title = models.CharField(max_length=255)
    kind = models.CharField(
        max_length=32,
        choices=MaterialKind.CHOICES,
        default=MaterialKind.FILE,
    )
    content_text = models.TextField(blank=True, default="")
    file_storage_key = models.CharField(max_length=512, blank=True, default="")
    link_url = models.URLField(max_length=1024, blank=True, default="")
    release_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=ContentStatus.CHOICES,
        default=ContentStatus.DRAFT,
    )

    def __str__(self) -> str:
        return f"Material: {self.title} ({self.kind}, {self.status})"


class Announcement(TimeStampedModel):
    class Meta:
        db_table = "lms_announcement"
        ordering = ["-created_at"]

    course = models.ForeignKey(
        "lms.Course",
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    author_user_id = models.IntegerField(db_index=True)
    author_role = models.CharField(max_length=32)
    title = models.CharField(max_length=255)
    content = models.TextField()

    def __str__(self) -> str:
        return f"Announcement: {self.title} in {self.course.code}"
