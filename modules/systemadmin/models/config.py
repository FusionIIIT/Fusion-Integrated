"""System Admin Configuration Models for Permitted Parameters (BR-SA-035)."""
from django.db import models
from core.db.mixins import TimeStampedModel


class SystemAdminConfig(TimeStampedModel):
    """Permitted system-wide configuration store (BR-SA-035).
    
    Prohibits modifying operational workflows, academic calendars, financial policies.
    """
    key = models.CharField(max_length=80, unique=True, db_index=True)
    value = models.JSONField()
    category = models.CharField(max_length=40, default="system")
    description = models.TextField(blank=True)
    is_critical = models.BooleanField(default=False)
    updated_by = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "systemadmin_config"
        ordering = ["category", "key"]

    def __str__(self) -> str:
        return f"{self.key} = {self.value}"
