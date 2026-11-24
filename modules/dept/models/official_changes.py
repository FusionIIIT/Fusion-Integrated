"""Official department detail change request (CFR-DEPT-015, CW-DEPT-03)."""

import uuid

from django.db import models

from modules.dept.models.department import Department


class OfficialDetailChangeRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="official_changes",
    )
    proposed_by_id = models.CharField(max_length=64)
    field_name = models.CharField(max_length=64)
    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField()
    justification = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    reviewed_by_id = models.CharField(max_length=64, blank=True, default="")
    review_reason = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dept_official_change_request"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Change {self.field_name} for {self.department_id} [{self.status}]"
