from __future__ import annotations

from django.db import models
from django.db.models import F, Index, Q
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class SystemPolicyParameter(TimeStampedModel):
    key = models.CharField(max_length=64, db_index=True)
    value = models.CharField(max_length=255)
    value_type = models.CharField(max_length=16, default="string")
    version = models.PositiveIntegerField(default=1)
    effective_from = models.DateTimeField(default=timezone.now, db_index=True)
    effective_to = models.DateTimeField(null=True, blank=True, db_index=True)
    description = models.TextField(blank=True)
    updated_by = models.PositiveIntegerField()

    class Meta:
        db_table = "superadmin_policy_parameter"
        constraints = [
            models.UniqueConstraint(fields=["key", "version"], name="policy_param_key_ver_uniq"),
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True) | Q(effective_to__gt=F("effective_from")),
                name="policy_param_dates_valid",
            ),
        ]
        indexes = [
            Index(fields=["key", "effective_to"], name="policy_key_active_idx"),
        ]
