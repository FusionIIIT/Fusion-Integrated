"""Patent prosecution budget and financial authorization models."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.models.applications import PatentApplication


class PatentBudget(TimeStampedModel):
    """Budget details and approval for filing and prosecution (BR-PMS-048..052)."""

    application = models.OneToOneField(
        PatentApplication, on_delete=models.CASCADE, related_name="budget"
    )
    filing_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    attorney_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    administrative_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=50, default="draft", db_index=True
    )  # draft, approved, rejected, escalated
    director_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    justification = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pms_patent_budget"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Budget for App {self.application_id}: Total {self.total_cost} ({self.status})"
