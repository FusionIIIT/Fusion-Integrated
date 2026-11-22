from django.db import models

from core.db.mixins import TimeStampedModel

#: The only fields that may change on an existing policy row: its lifecycle, never its content.
LIFECYCLE_FIELDS = frozenset({"effective_to", "is_active", "superseded_by", "updated_at"})


class PolicyImmutable(Exception):
    """Raised when code tries to edit an administrator policy row in place (R1-08)."""


class PatentPolicy(TimeStampedModel):
    """Effective-dated administrator policy. Changes supersede a row; they never edit it."""

    director_review_days = models.PositiveIntegerField(default=15)
    revision_resubmission_days = models.PositiveIntegerField(default=60)
    cost_escalation_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    max_attorney_workload = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    max_document_size_bytes = models.BigIntegerField(default=52428800)
    withdrawal_eligible_states = models.JSONField(default=list)
    effective_from = models.DateTimeField(auto_now_add=True)
    effective_to = models.DateTimeField(null=True, blank=True)
    superseded_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supersedes",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "patents_policy"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            update_fields = kwargs.get("update_fields")
            if update_fields is None or not set(update_fields) <= LIFECYCLE_FIELDS:
                raise PolicyImmutable("Policy content is effective-dated; supersede the row.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PolicyImmutable("Policy rows are kept for history; supersede them instead.")
