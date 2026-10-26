"""Leave application and transition history models for ELM."""
from decimal import Decimal
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """The central leave application record in ELM."""

    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("VL", "Vacation Leave"),
        ("COL", "Commuted Leave"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("awaiting_substitute", "Awaiting Substitute Response"),
        ("substitute_declined", "Substitute Declined"),
        ("awaiting_unit_head", "Awaiting Unit Head Review"),
        ("awaiting_sanction", "Awaiting Sanction Decision"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
        ("resumed", "Resumed"),
    ]

    HALF_DAY_CHOICES = [
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ]

    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=16, choices=HALF_DAY_CHOICES, null=True, blank=True)
    days_calculated = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.00"))
    reason = models.TextField()
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="draft", db_index=True)

    # Station Leave fields (BR-EL-013)
    leaving_station = models.BooleanField(default=False)
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)
    station_address = models.CharField(max_length=255, blank=True)
    emergency_phone = models.CharField(max_length=32, blank=True)

    # Substitute fields (BR-EL-014, BR-EL-015)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(max_length=24, default="none")  # none, pending, accepted, declined
    substitute_remarks = models.CharField(max_length=255, blank=True)

    # Unit Head & Sanctioning Authority fields
    unit_head_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    unit_head_recommendation = models.CharField(max_length=24, default="pending")  # pending, recommended, rejected
    unit_head_remarks = models.TextField(blank=True)
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    sanction_remarks = models.TextField(blank=True)
    sanctioned_at = models.DateTimeField(null=True, blank=True)

    # Resumption support
    actual_resumption_date = models.DateField(null=True, blank=True)
    resumption_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_req_user_status_idx"),
            models.Index(fields=["substitute_user_id", "status"], name="elm_req_substitute_idx"),
            models.Index(fields=["status", "-created_at"], name="elm_req_status_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Leave #{self.id} ({self.category}) - User {self.user_id} [{self.status}]"


class LeaveTransitionHistory(TimeStampedModel):
    """Append-only audit trail for leave request status transitions."""

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_status = models.CharField(max_length=40)
    to_status = models.CharField(max_length=40)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "elm_transition_history"
        indexes = [
            models.Index(fields=["leave_request", "-created_at"], name="elm_hist_req_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Leave #{self.leave_request_id}: {self.from_status} -> {self.to_status}"
