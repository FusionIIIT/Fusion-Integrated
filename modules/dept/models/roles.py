"""Department role tenure and governance model (CFR-DEPT-016, BR-DEPT-021..024)."""

import uuid

from django.db import models

from modules.dept.models.department import Department


class DepartmentRoleAssignment(models.Model):
    ROLE_CHOICES = [
        ("HOD", "Head of Department"),
        ("DEPT_ADMIN", "Department Administrator"),
    ]
    STATUS_CHOICES = [
        ("SCHEDULED", "Scheduled"),
        ("ACTIVE", "Active"),
        ("REVOKED", "Revoked"),
        ("EXPIRED", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role_name = models.CharField(max_length=32, choices=ROLE_CHOICES)
    user_id = models.CharField(max_length=64)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="SCHEDULED")
    assigned_by_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dept_role_assignment"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_date__lt=models.F("end_date")),
                name="valid_role_tenure_range",
            ),
            models.UniqueConstraint(
                fields=["department", "role_name"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_role_per_department",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role_name} - {self.user_id} ({self.status})"
