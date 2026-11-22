"""The three child workflows that hang off an approved leave (CW-EL-02..04)."""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.domain import state_machine as sm
from modules.leave.models.requests import LeaveRequest


class CancellationRequest(TimeStampedModel):
    """Pre-start reversal of an approved leave (BR-EL-023)."""
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                      related_name="cancellations")
    status = models.CharField(max_length=48,
                              choices=[(s, s) for s in sm.CANCELLATION_STATES],
                              default=sm.CANCEL_PENDING_UNIT_HEAD, db_index=True)
    reason = models.CharField(max_length=500)
    unit_head_recommendation = models.CharField(max_length=20, blank=True, default="")
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ("-id",)
        constraints = [
            models.UniqueConstraint(
                fields=("leave_request",),
                condition=models.Q(status__in=sm.CANCELLATION_PENDING),
                name="leave_one_pending_cancellation"),
        ]

    def __str__(self) -> str:
        return f"cancellation:{self.leave_request_id}:{self.status}"


class ExtensionRequest(TimeStampedModel):
    """Additional leave time on an ongoing period (BR-EL-025).

    The original approved leave stays the base; only `additional_days` is
    posted when this is approved.
    """
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                      related_name="extensions")
    status = models.CharField(max_length=48,
                              choices=[(s, s) for s in sm.EXTENSION_STATES],
                              default=sm.EXT_AWAITING_UNIT_HEAD, db_index=True)
    additional_start_date = models.DateField()
    additional_end_date = models.DateField()
    additional_days = models.DecimalField(max_digits=8, decimal_places=2,
                                         validators=[MinValueValidator(Decimal("0.01"))])
    reason = models.CharField(max_length=500)
    substitute_required = models.BooleanField(default=False)
    unit_head_recommendation = models.CharField(max_length=20, blank=True, default="")
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ("-id",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(additional_end_date__gte=models.F("additional_start_date")),
                name="leave_extension_period_ordered"),
            models.UniqueConstraint(
                fields=("leave_request",),
                condition=models.Q(status__in=sm.EXTENSION_PENDING),
                name="leave_one_pending_extension"),
        ]

    def __str__(self) -> str:
        return f"extension:{self.leave_request_id}:{self.status}"


class ResumptionRequest(TimeStampedModel):
    """Actual return to duty, reviewed by the Sanctioning Authority (BR-EL-027).

    There is no generic closure state; the three reviewed outcomes are the end
    of this workflow (BR-EL-028).
    """
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                      related_name="resumptions")
    status = models.CharField(max_length=56,
                              choices=[(s, s) for s in sm.RESUMPTION_STATES],
                              default=sm.RESUMPTION_PENDING, db_index=True)
    actual_resumption_date = models.DateField()
    details = models.CharField(max_length=500, blank=True, default="")
    #: Signed: negative for an early return that owes days back, positive for a
    #: late return that owes more.
    adjustment_days = models.DecimalField(max_digits=8, decimal_places=2,
                                          default=Decimal("0"))
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ("-id",)
        constraints = [
            models.UniqueConstraint(
                fields=("leave_request",),
                condition=models.Q(status=sm.RESUMPTION_PENDING),
                name="leave_one_pending_resumption"),
        ]

    def __str__(self) -> str:
        return f"resumption:{self.leave_request_id}:{self.status}"