"""Confidential feedback model (CFR-DEPT-007, CFR-DEPT-008, CW-DEPT-02)."""

import uuid

from django.db import models

from modules.dept.models.department import Department


class Feedback(models.Model):
    STATUS_CHOICES = [
        ("NEW", "New"),
        ("UNDER_REVIEW", "Under Review"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
    ]
    CATEGORY_CHOICES = [
        ("ACADEMIC", "Academic"),
        ("INFRASTRUCTURE", "Infrastructure"),
        ("ADMINISTRATIVE", "Administrative"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="feedbacks")
    submitted_by_id = models.CharField(max_length=64)
    submitter_role = models.CharField(max_length=32)
    category = models.CharField(max_length=64, choices=CATEGORY_CHOICES, default="ACADEMIC")
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="NEW")
    admin_remarks = models.TextField(blank=True, default="")
    reviewed_by_admin_id = models.CharField(max_length=64, blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    terminal_by_id = models.CharField(max_length=64, blank=True, default="")
    terminal_by_role = models.CharField(max_length=32, blank=True, default="")
    terminal_remarks = models.TextField(blank=True, default="")
    terminal_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dept_feedback"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["department", "status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} [{self.status}]"
