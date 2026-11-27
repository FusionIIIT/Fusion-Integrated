"""Resumption of duty models (CW-EL-04, BR-EL-027..028)."""

from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.models.requests import LeaveRequest


class ResumptionRecord(TimeStampedModel):
    """Formal return to duty report and review outcome."""

    NATURE_CHOICES = [
        ("normal", "Normal"),
        ("early", "Early"),
        ("late", "Late"),
    ]

    DECISION_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    request = models.OneToOneField(
        LeaveRequest, on_delete=models.CASCADE, related_name="resumption"
    )
    expected_date = models.DateField()
    actual_resumption_date = models.DateField()
    nature = models.CharField(max_length=20, choices=NATURE_CHOICES)
    difference_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    remarks = models.TextField(blank=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision = models.CharField(max_length=20, default="pending", choices=DECISION_CHOICES)

    def __str__(self) -> str:
        return f"Resumption for {self.request.application_number}: {self.nature} ({self.decision})"
