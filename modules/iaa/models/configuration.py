from django.db import models

from core.db.mixins import TimeStampedModel


class IAAConfiguration(TimeStampedModel):
    financial_year = models.CharField(max_length=16, default="2026-2027")
    high_value_ta_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
    approval_timeout_days = models.PositiveIntegerField(default=3)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]


class DepartmentBudget(TimeStampedModel):
    department = models.CharField(max_length=64, db_index=True)
    financial_year = models.CharField(max_length=16, default="2026-2027")
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=1000000.00)
    utilized_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ("department", "financial_year")
        ordering = ["department"]

    @property
    def available_amount(self):
        return self.allocated_amount - self.utilized_amount


class ApprovalHierarchyRule(TimeStampedModel):
    request_type = models.CharField(max_length=32, default="expense")
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    required_levels = models.PositiveIntegerField(default=1)
    approver_roles = models.JSONField(default=list)

    class Meta:
        ordering = ["min_amount"]
