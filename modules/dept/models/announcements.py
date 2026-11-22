"""Department announcement model."""

import uuid

from django.db import models

from modules.dept.models.department import Department


class Announcement(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("HIDDEN", "Hidden"),
        ("DELETED", "Deleted"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    author_id = models.CharField(max_length=64)
    author_role = models.CharField(max_length=32)
    target_role = models.CharField(max_length=32, default="ALL")
    target_program = models.CharField(max_length=64, default="ALL")
    target_academic_year = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="ACTIVE")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dept_announcement"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["department", "status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.department_id})"
