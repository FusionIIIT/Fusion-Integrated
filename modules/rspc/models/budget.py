"""Budget head model for RSPC projects."""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.rspc.models.project import Project


class ProjectBudgetHead(TimeStampedModel):
    """Allocated budget head under a project."""

    HEAD_TYPES = [
        ("equipment", "Equipment / Capital Assets"),
        ("consumables", "Consumables & Chemicals"),
        ("manpower", "Project Staff / Manpower"),
        ("travel", "Travel & Field Work"),
        ("contingency", "Contingency"),
        ("overheads", "Institutional Overheads"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="budget_heads")
    head_type = models.CharField(max_length=32, choices=HEAD_TYPES)
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    spent_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    committed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "rspc_project_budget_head"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "head_type"], name="rspc_unique_project_head"
            ),
            models.CheckConstraint(
                condition=Q(allocated_amount__gte=0), name="rspc_budget_allocated_gte_zero"
            ),
            models.CheckConstraint(
                condition=Q(spent_amount__gte=0), name="rspc_budget_spent_gte_zero"
            ),
            models.CheckConstraint(
                condition=Q(committed_amount__gte=0), name="rspc_budget_committed_gte_zero"
            ),
        ]

    @property
    def available_balance(self) -> Decimal:
        return self.allocated_amount - (self.spent_amount + self.committed_amount)

    def __str__(self) -> str:
        return (
            f"{self.project.project_code} - {self.head_type}: "
            f"{self.spent_amount}/{self.allocated_amount}"
        )
