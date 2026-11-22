"""Club budget requests, stored open for tracking only (AFR-GYM-031)."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.clubs import Club


class BudgetRequest(TimeStampedModel):
    OPEN = "open"

    club = models.ForeignKey(Club, on_delete=models.PROTECT,
                             related_name="budget_requests")
    purpose = models.CharField(max_length=200)
    description = models.TextField(max_length=4000)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    document_link = models.CharField(max_length=300)
    document_file_id = models.CharField(max_length=200)
    status = models.CharField(max_length=8, default=OPEN)
    submitted_by_user_id = models.IntegerField()

    class Meta:
        db_table = "gymkhana_budget_request"
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0),
                                   name="gym_budget_amount_non_negative"),
            models.CheckConstraint(condition=~Q(document_file_id=""),
                                   name="gym_budget_document_present"),
            models.CheckConstraint(condition=Q(status="open"),
                                   name="gym_budget_status_open"),
        ]
        indexes = [
            models.Index(fields=["club", "created_at"],
                         name="gym_budget_club_created_idx"),
        ]
