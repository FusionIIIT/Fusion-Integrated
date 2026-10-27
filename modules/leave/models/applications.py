"""Leave applications model."""
from __future__ import annotations

from decimal import Decimal
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """Leave request submitted by an employee (WF-EL-01..05)."""

    CATEGORIES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("VL", "Vacation Leave"),
        ("COL", "Commuted Leave"),
    ]

    HALF_DAY_CHOICES = [
        ("full", "Full Day"),
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("substitute_pending", "Pending Substitute Consent"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancel_requested", "Cancellation Requested"),
        ("cancelled", "Cancelled"),
        ("extension_requested", "Extension Requested"),
        ("resumption_submitted", "Resumption Submitted"),
        ("resumption_reviewed", "Resumption Reviewed"),
    ]

    category = models.CharField(max_length=10, choices=CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day_type = models.CharField(max_length=15, choices=HALF_DAY_CHOICES, default="full")
    days_count = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("1.0"))

    purpose = models.TextField()
    address_during_leave = models.TextField(blank=True)

    # Station Leave details (BR-EL-013)
    is_station_leave = models.BooleanField(default=False)
    station_departure_date = models.DateField(null=True, blank=True)
    station_arrival_date = models.DateField(null=True, blank=True)
    station_destination = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="substitute_pending")

    # Routing and reviews (BR-EL-016..020)
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    unit_head_recommended = models.BooleanField(null=True, blank=True)
    unit_head_remarks = models.TextField(blank=True)
    unit_head_reviewed_at = models.DateTimeField(null=True, blank=True)

    establishment_user_id = models.IntegerField(null=True, blank=True)
    establishment_remarks = models.TextField(blank=True)
    establishment_reviewed_at = models.DateTimeField(null=True, blank=True)

    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True)
    sanctioning_remarks = models.TextField(blank=True)
    sanctioned_at = models.DateTimeField(null=True, blank=True)

    # Extension tracking (BR-EL-025, WF-EL-04)
    parent_leave = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="extensions"
    )

    # Cancellation tracking (BR-EL-023, WF-EL-03)
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Resumption of duty (BR-EL-027, BR-EL-028, WF-EL-05)
    resumption_date = models.DateField(null=True, blank=True)
    actual_days_count = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    resumption_remarks = models.TextField(blank=True)
    resumption_reviewed_at = models.DateTimeField(null=True, blank=True)
    resumption_outcome = models.CharField(
        max_length=32,
        choices=[
            ("", "Not reviewed"),
            ("no_adjustment", "No adjustment"),
            ("early_return_synchronized", "Early return synchronized"),
            ("late_return_synchronized", "Late return synchronized"),
        ],
        blank=True,
        default="",
    )

    # Offline synchronization (BR-EL-029, WF-EL-06)
    is_offline_sanctioned = models.BooleanField(default=False)
    offline_reference_no = models.CharField(max_length=120, blank=True)
    offline_sanction_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "leave_application"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_app_user_status_idx"),
            models.Index(fields=["start_date", "end_date"], name="leave_app_dates_idx"),
            models.Index(fields=["status"], name="leave_app_status_idx"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"leave#{self.pk} u{self.user_id} {self.category} {self.status}"
