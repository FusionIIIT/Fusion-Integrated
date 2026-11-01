"""Resumption review, offline-sanctioned records and record maintenance.

EL-UC-010 to EL-UC-011, EL-UC-016 and EL-UC-017. Record maintenance is
deliberately a separate table from the decisions: BR-EL-037 says an
administrative correction must not read as a sanction.
"""

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class ResumptionSubmission(TimeStampedModel):
    """Actual return-to-duty information awaiting review (BR-EL-027, BR-EL-028)."""

    STATES = [("pending", "Review pending"), ("reviewed", "Reviewed")]

    request = models.ForeignKey("LeaveRequest", on_delete=models.CASCADE,
                               related_name="resumptions")
    actual_date = models.DateField()
    state = models.CharField(max_length=12, choices=STATES, default="pending")
    submitted_by_user_id = models.IntegerField(null=True, blank=True)
    review_event = models.CharField(max_length=24, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_resumption_submission"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["request", "state"], name="leave_resumption_req_idx"),
        ]

    def __str__(self) -> str:
        return f"req#{self.request_id} resumption {self.actual_date}"


class OfflineLeaveRecord(TimeStampedModel, UserScopedModel):
    """Leave already sanctioned on paper, synchronized without a second approval.

    BR-EL-029 and BR-EL-037: this records a decision that has already been made,
    so nothing here routes anywhere.
    """

    category = models.CharField(max_length=4)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=6, decimal_places=2)
    sanction_reference = models.CharField(max_length=120)
    evidence_note = models.CharField(max_length=300, blank=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)
    balance_synced = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_offline_record"
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="leave_offline_period_ordered"),
        ]

    def __str__(self) -> str:
        return f"offline u{self.user_id} {self.category} {self.start_date}"


class LeaveRecordAdjustment(TimeStampedModel, UserScopedModel):
    """An administrative correction to a balance, never a sanctioning decision.

    BR-EL-037: this row exists so a correction can be told apart from an
    approval when somebody reads the history a year later.
    """

    TYPES = [("adjustment", "Adjustment"), ("reversal", "Reversal")]

    request = models.ForeignKey("LeaveRequest", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="adjustments")
    account = models.ForeignKey("LeaveAccount", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="adjustments")
    entry_type = models.CharField(max_length=12, choices=TYPES, default="adjustment")
    days = models.DecimalField(max_digits=6, decimal_places=2)
    reason = models.CharField(max_length=300)
    actor_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_record_adjustment"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.entry_type} {self.days} u{self.user_id}"
