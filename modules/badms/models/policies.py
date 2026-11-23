from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class SecurityPolicy(TimeStampedModel):
    policy_key = models.CharField(max_length=100)
    policy_value = models.JSONField()
    configured_by_user_id = models.IntegerField()
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "badms_security_policy"
        constraints = [
            models.UniqueConstraint(
                fields=["policy_key", "is_active"],
                condition=Q(is_active=True),
                name="uniq_badms_active_security_policy",
            ),
        ]


class RetentionPolicy(TimeStampedModel):
    name = models.CharField(max_length=100)
    data_classification = models.CharField(max_length=50)
    retention_days = models.IntegerField(default=30)
    auto_purge_enabled = models.BooleanField(default=False)
    configured_by_user_id = models.IntegerField()
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "badms_retention_policy"
        constraints = [
            models.UniqueConstraint(
                fields=["data_classification", "is_active"],
                condition=Q(is_active=True),
                name="uniq_badms_active_retention_policy",
            ),
        ]
