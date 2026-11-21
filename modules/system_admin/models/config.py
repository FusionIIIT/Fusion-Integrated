"""System parameter configuration models within strict boundaries (BR-SA-035)."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.system_admin.constants import PermittedConfigKey
from modules.system_admin.exceptions import ConfigurationBoundaryViolationError


class SystemParameter(TimeStampedModel):
    """Stores permitted system-wide parameters within strict boundaries (BR-SA-035)."""

    key = models.CharField(max_length=64, unique=True, primary_key=True)
    value = models.CharField(max_length=255)
    value_type = models.CharField(max_length=16, default="string")  # 'string', 'int', 'bool', 'json'
    category = models.CharField(max_length=32)
    description = models.TextField(blank=True)
    updated_by = models.IntegerField(help_text="Super Admin user_id")

    class Meta:
        db_table = "system_admin_parameter"

    def save(self, *args, **kwargs):
        if self.key not in PermittedConfigKey.ALL_KEYS:
            raise ConfigurationBoundaryViolationError(
                f"Parameter key '{self.key}' is not in permitted config keys whitelist (BR-SA-035)."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"SystemParameter: {self.key} = {self.value}"
