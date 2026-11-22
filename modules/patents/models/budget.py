from django.db import models

from core.db.mixins import TimeStampedModel
from modules.patents.models.application import PatentApplication


class PatentBudgetLedger(TimeStampedModel):
    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="budget_entries",
    )
    entry_type = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    category = models.CharField(max_length=50)
    status = models.CharField(max_length=30, default="PENDING")
    authorized_by_user_id = models.IntegerField(db_index=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "patents_budget_ledger"
