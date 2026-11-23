"""Club budget request tracking model for Gymkhana."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, Q

from modules.gymkhana.domain.constants import BUDGET_STATUS_OPEN
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.files import PrivateStorage, budget_key


class ClubBudgetRequest(models.Model):
    """Budget request submitted by Club Head for tracking (open state only)."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="budget_requests")
    submitted_by_id = models.IntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    supporting_file = models.FileField(upload_to=budget_key, storage=PrivateStorage())
    status = models.CharField(max_length=20, default=BUDGET_STATUS_OPEN)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_budget_request"
        ordering = ["-submitted_at"]
        constraints = [
            CheckConstraint(
                condition=Q(amount__gte=0),
                name="check_positive_budget_amount",
            ),
        ]

    def __str__(self) -> str:
        return f"BudgetRequest(club={self.club.name}, amount={self.amount})"
