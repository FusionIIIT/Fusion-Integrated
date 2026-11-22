"""Configurable policy parameters and SLA thresholds."""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel


class LeavePolicyConfig(TimeStampedModel):
    """Leave policy and SLA thresholds (BR-EL-030, BR-EL-038)."""

    key = models.CharField(max_length=80, unique=True)
    value = models.JSONField(default=dict)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "leave_policy_config"

    def __str__(self) -> str:
        return self.key
