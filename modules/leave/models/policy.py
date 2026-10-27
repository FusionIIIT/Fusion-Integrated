from django.db import models
from core.db.mixins import TimeStampedModel

class LeavePolicyConfig(TimeStampedModel):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "leave_policy_config"