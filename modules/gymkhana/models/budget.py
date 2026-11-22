from django.db import models
from django.db.models import Q

from modules.gymkhana.models.club import Club


class ClubBudgetRequest(models.Model):
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="budget_requests",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.CharField(max_length=200)
    description = models.TextField()
    supporting_file_url = models.CharField(max_length=500)
    supporting_file_id = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default="open")
    submitted_by_user_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_budget_request"
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="gymkhana_budget_amount_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(status="open"),
                name="gymkhana_budget_status_open",
            ),
        ]

    def __str__(self) -> str:
        return f"Budget: {self.club.name} - {self.amount} ({self.purpose})"
