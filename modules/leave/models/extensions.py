"""Leave extension models.

Implements ongoing leave extension aggregate (CW-EL-03 / BR-EL-025).
"""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.domain.constants import RequestStatus, SubstituteStatus, UnitHeadRecommendation
from modules.leave.models.requests import LeaveRequest


class LeaveExtension(TimeStampedModel):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="extensions")
    extend_from = models.DateField()
    extend_to = models.DateField()
    incremental_days = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()

    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in SubstituteStatus],
        default=SubstituteStatus.NOT_REQUIRED.value,
    )

    unit_head_recommendation = models.CharField(
        max_length=20,
        choices=[(r.value, r.value) for r in UnitHeadRecommendation],
        default=UnitHeadRecommendation.NONE.value,
    )

    status = models.CharField(
        max_length=50,
        choices=[(s.value, s.value) for s in RequestStatus],
        default=RequestStatus.EXT_AWAITING_UNIT_HEAD.value,
    )

    class Meta:
        ordering = ["-created_at"]
