from django.db import models

from core.db.mixins import TimeStampedModel


class BudgetStatus(models.TextChoices):
    PENDING = "pending", "Pending Institutional Sanction"
    APPROVED = "approved", "Sanctioned / Approved"
    REJECTED = "rejected", "Budget Sanction Declined"
    ESCALATED = "escalated", "Escalated for Special Financial Approval"


class PatentBudget(TimeStampedModel):
    """Estimated and approved institutional budget for patent filing and attorney fees."""

    application = models.OneToOneField(
        "pms.PatentApplication",
        on_delete=models.CASCADE,
        related_name="budget",
    )
    estimated_filing_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    estimated_attorney_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    estimated_search_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_estimated_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    budget_status = models.CharField(
        max_length=32,
        choices=BudgetStatus.choices,
        default=BudgetStatus.PENDING,
    )
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_date = models.DateTimeField(null=True, blank=True)
    escalation_notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "pms_patent_budget"

    def __str__(self) -> str:
        return f"Budget for App #{self.application_id}: Total {self.total_estimated_amount}"
