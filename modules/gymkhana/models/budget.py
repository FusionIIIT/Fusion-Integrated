from django.db import models
from django.db.models import CheckConstraint, Index, Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.club import Club
from modules.gymkhana.storage import gymkhana_upload_storage


class ClubBudgetRequest(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="budget_requests")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.CharField(max_length=250)
    description = models.TextField()
    supporting_file = models.FileField(
        upload_to="budgets/",
        storage=gymkhana_upload_storage,
    )
    status = models.CharField(max_length=20, default="open")
    submitted_by_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "gymkhana_budget_request"
        indexes = [
            Index(fields=["club", "status"], name="gym_budget_club_status_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(amount__gte=0),
                name="gymkhana_budget_non_negative",
            ),
        ]
