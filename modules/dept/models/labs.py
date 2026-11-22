"""Lab resource profiles and equipment catalog (CFR-DEPT-012, BR-DEPT-012)."""

import uuid

from django.db import models

from modules.dept.models.department import Department


class LabResource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="lab_resources",
    )
    lab_name = models.CharField(max_length=150)
    location = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    equipment_details = models.JSONField(default=list, blank=True)
    in_charge_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dept_lab_resource"
        ordering = ["lab_name"]
        constraints = [
            models.UniqueConstraint(fields=["department", "lab_name"], name="unique_dept_lab_name"),
        ]

    def __str__(self) -> str:
        return f"{self.lab_name} ({self.department_id})"
