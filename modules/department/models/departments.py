"""Department domain tables.

Departments are the core organizational units in the system.
"""

from django.db import models

from core.db.mixins import TimeStampedModel


class Department(TimeStampedModel):
    """Represents a department within the organization."""

    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    core_policies = models.TextField(blank=True)
    about = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "department_department"
        indexes = [
            models.Index(fields=["code"], name="dept_code_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.name}"
