"""Leave resumption models.

Implements duty resumption review (CW-EL-04 / BR-EL-027, BR-EL-028).
"""
from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.domain.constants import RequestStatus, ResumptionType
from modules.leave.models.requests import LeaveRequest


class LeaveResumption(TimeStampedModel):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="resumptions")
    actual_resumption_date = models.DateField()
    resumption_type = models.CharField(
        max_length=20,
        choices=[(t.value, t.value) for t in ResumptionType],
        default=ResumptionType.NORMAL.value,
    )
    days_adjustment = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    status = models.CharField(
        max_length=50,
        choices=[(s.value, s.value) for s in RequestStatus],
        default=RequestStatus.RESUMPTION_REVIEW_PENDING.value,
    )
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
