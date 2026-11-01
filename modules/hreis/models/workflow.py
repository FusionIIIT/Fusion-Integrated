"""Workflow configuration model (BR-HR-009, BR-HR-012, BR-HR-034)."""
from django.db import models

from core.db.mixins import TimeStampedModel


class WorkflowConfiguration(TimeStampedModel):
    """Configurable HR-EIS institutional policies, approval matrices, and windows."""

    setting_key = models.CharField(max_length=64, unique=True, db_index=True)
    setting_value = models.JSONField(default=dict)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "hreis_workflow_configuration"
        verbose_name = "Workflow Configuration"
        verbose_name_plural = "Workflow Configurations"

    def __str__(self) -> str:
        return f"WorkflowConfig({self.setting_key})"
