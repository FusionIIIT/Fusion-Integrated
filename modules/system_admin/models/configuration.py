"""Permitted system parameters configuration model."""
from django.db import models

from core.db.mixins import TimeStampedModel


class SystemParameter(TimeStampedModel):
    key = models.CharField(max_length=64, unique=True, db_index=True)
    label = models.CharField(max_length=120)
    value = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    updated_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "system_admin_parameter"
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.key} = {self.value}"
