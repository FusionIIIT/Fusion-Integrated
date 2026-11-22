"""Audit trail for special food state transitions (BR-MMS-031;
UC-019/020/021/029)."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class SpecialFoodTransition(TimeStampedModel):
    request = models.IntegerField(db_index=True)
    from_status = models.CharField(max_length=16)
    to_status = models.CharField(max_length=16)
    actor_user_id = models.IntegerField(null=True, blank=True)
    occurred_at = models.DateTimeField()
    note = models.TextField(blank=True)

    class Meta:
        db_table = "mms_special_food_transition"
        indexes = [
            models.Index(fields=["request", "occurred_at"], name="sf_trans_request_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["request"],
                condition=Q(to_status__in=("rejected", "served", "cancelled")),
                name="one_terminal_decision_per_request",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.request}:{self.from_status}→{self.to_status}"
