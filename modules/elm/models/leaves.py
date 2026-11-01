"""Leave Request and Workflow Lifecycle Models."""
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
        ("awaiting_director_self_sanction", "Awaiting Director Self-Sanction"),
        ("awaiting_establishment", "Awaiting Establishment Verification"),
        ("awaiting_final_sanction", "Awaiting Final Sanction Decision"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancellation_pending_unit_head", "Cancellation Pending - Unit Head Review"),
        ("cancellation_pending_establishment", "Cancellation Pending - Establishment"),
        ("cancellation_pending_final", "Cancellation Pending - Final Decision"),
        ("cancelled", "Cancelled"),
        ("extension_pending_substitute", "Extension Pending - Substitute"),
        ("extension_applicant_action_required", "Extension Applicant Action Required"),
        ("extension_pending_unit_head", "Extension Pending - Unit Head"),
        ("extension_pending_establishment", "Extension Pending - Establishment"),
        ("extension_pending_final", "Extension Pending - Final Decision"),
        ("extended", "Extended"),
        ("resumption_pending", "Resumption Review Pending"),
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

    # Station Leave fields (BR-EL-013: coupled in same application)
    leaving_station = models.BooleanField(default=False)
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)
    station_address = models.CharField(max_length=255, blank=True)
    emergency_phone = models.CharField(max_length=32, blank=True)

    # Substitute fields (BR-EL-014, BR-EL-015)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(max_length=24, default="none")  # none, pending, accepted, declined
    substitute_remarks = models.CharField(max_length=255, blank=True)

    # Review & Sanction hierarchy fields (BR-EL-016 - BR-EL-020)
    unit_head_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    unit_head_recommendation = models.CharField(max_length=24, default="pending")  # pending, recommended, not_recommended, approved, rejected
    unit_head_remarks = models.TextField(blank=True)
    establishment_user_id = models.IntegerField(null=True, blank=True)
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    final_decision_remarks = models.TextField(blank=True)
    sanctioned_at = models.DateTimeField(null=True, blank=True)

    # Extension support (CW-EL-03, BR-EL-025)
    is_extension = models.BooleanField(default=False)
    original_leave_id = models.IntegerField(null=True, blank=True, db_index=True)

    # Resumption support (CW-EL-04, BR-EL-027, BR-EL-028)
    actual_resumption_date = models.DateField(null=True, blank=True)
    resumption_remarks = models.TextField(blank=True)

    # Offline-sanctioned leave support (BR-EL-029, EL-UC-016)
    is_offline_sanctioned = models.BooleanField(default=False)
    offline_sanction_reference = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_req_user_status_idx"),
            models.Index(fields=["status", "category"], name="elm_req_status_cat_idx"),
            models.Index(fields=["start_date", "end_date"], name="elm_req_dates_idx"),
        ]

    def __str__(self) -> str:
        return f"Leave #{self.pk} (User {self.user_id}) - {self.category} [{self.status}]"


class LeaveTransitionHistory(TimeStampedModel):
    """Append-only audit trail of every status transition."""

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_status = models.CharField(max_length=40)
    to_status = models.CharField(max_length=40)
    actor_user_id = models.IntegerField(db_index=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "elm_transition_history"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Req #{self.leave_request_id}: {self.from_status} -> {self.to_status} by User {self.actor_user_id}"
