from django.db import models

from core.db.mixins import TimeStampedModel


class PatentPolicy(TimeStampedModel):
    director_review_days = models.PositiveIntegerField(default=15)
    revision_resubmission_days = models.PositiveIntegerField(default=60)
    cost_escalation_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    max_document_size_bytes = models.BigIntegerField(default=52428800)
    withdrawal_eligible_states = models.JSONField(default=list)
    effective_from = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "patents_policy"
