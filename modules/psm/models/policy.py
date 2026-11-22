# Effective-dated PSM policy versions (BR-PSM-004, 007, 008, 010, 014, 022, 028).
from decimal import Decimal

from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel


def _default_permissible_states() -> list[str]:
    return ["draft", "submitted", "changes_requested", "department_reviewed"]


class PsmPolicy(TimeStampedModel):
    """Append-only policy version; superseding inserts a new row rather than mutating."""

    version = models.PositiveIntegerField(unique=True)
    effective_from = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)
    direct_limit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("50000.00"))
    final_approval_threshold = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("100000.00")
    )
    high_priority_direct_allowed = models.BooleanField(default=True)
    modifiable_states = models.JSONField(default=_default_permissible_states)
    withdrawable_states = models.JSONField(default=_default_permissible_states)
    sla_reminder_hours = models.PositiveIntegerField(default=24)
    sla_escalation_hours = models.PositiveIntegerField(default=48)
    high_priority_sla_reminder_hours = models.PositiveIntegerField(default=12)
    high_priority_sla_escalation_hours = models.PositiveIntegerField(default=24)
    partial_payment_enabled = models.BooleanField(default=True)
    duplicate_window_days = models.PositiveIntegerField(default=14)

    class Meta:
        db_table = "psm_policy"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"], condition=Q(is_active=True), name="psm_policy_single_active"
            ),
            models.CheckConstraint(
                condition=Q(direct_limit__gt=0) & Q(final_approval_threshold__gt=0),
                name="psm_policy_thresholds_positive",
            ),
            models.CheckConstraint(
                condition=Q(sla_escalation_hours__gt=F("sla_reminder_hours"))
                & Q(high_priority_sla_escalation_hours__gt=F("high_priority_sla_reminder_hours")),
                name="psm_policy_sla_order",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active", "-effective_from"], name="psm_policy_active_eff_idx"),
        ]

    def __str__(self) -> str:
        return f"psm_policy v{self.version}"
