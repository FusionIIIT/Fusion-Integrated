"""Effective-dated HR rules. No default eligibility, quota or money policy."""

from django.db import models
from django.db.models import Q


class HRPolicyVersion(models.Model):
    family = models.CharField(max_length=40)
    version = models.PositiveIntegerField()
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)
    parameters = models.JSONField()
    approved_by_user_id = models.IntegerField()
    approved_designation = models.CharField(max_length=150)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hreis_policy_version"
        constraints = [
            models.UniqueConstraint(
                fields=["family", "version"], name="hr_policy_family_version_unique"
            ),
            models.CheckConstraint(
                condition=Q(effective_until__isnull=True)
                | Q(effective_until__gt=models.F("effective_from")),
                name="hr_policy_valid_interval",
            ),
        ]
        indexes = [
            models.Index(fields=["family", "-effective_from"], name="hr_policy_effective_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.family} policy v{self.version}"
