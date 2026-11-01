from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel


class DepartmentRoleAssignment(TimeStampedModel):
    """Represents a role assignment for a department."""
    department = models.ForeignKey(
        "department.Department",
        on_delete=models.PROTECT,
        related_name="role_assignments"
    )
    ROLE_CHOICES = [
        ('hod', 'Head of Department'),
        ('dept_admin', 'Department Administrator'),
    ]
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    user_id = models.IntegerField()
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    assigned_by_user_id = models.IntegerField()
    transition_applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "department_role_assignment"
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_to__gt=F("valid_from")),
                name="dept_roleassign_interval"
            )
        ]
        indexes = [
            models.Index(fields=["department", "role", "valid_from"], name="dept_roleassign_lookup_idx"),
        ]
