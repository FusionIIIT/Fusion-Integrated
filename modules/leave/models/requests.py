from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """EL-UC-001, BR-EL-034"""

    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_half_day = models.BooleanField(default=False)
    half_session = models.CharField(max_length=10, blank=True)
    days = models.DecimalField(max_digits=5, decimal_places=1)
    purpose = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=200, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(
        max_length=20,
        choices=[
            ("not_required", "Not Required"),
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
        ],
        blank=True,
    )
    unit = models.ForeignKey(
        "OrgUnit", on_delete=models.PROTECT, null=True, blank=True, related_name="requests"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("substitute_pending", "Substitute Pending"),
            ("unit_review", "Unit Review"),
            ("routing", "Routing"),
            ("sanction", "Sanction"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("withdrawn", "Withdrawn"),
            ("cancelled", "Cancelled"),
        ],
        default="substitute_pending",
    )
    recommendation = models.CharField(max_length=20, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)
    is_offline = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_request"
        indexes = [
            models.Index(fields=["status"], name="leave_request_status_idx"),
            models.Index(fields=["user_id", "start_date"], name="leave_request_user_start_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} - {self.category} - {self.start_date} to {self.end_date}"


class RequestAction(TimeStampedModel):
    """EL-UC-002, BR-EL-034"""

    ACTION_CHOICES = [
        ("create", "Create"),
        ("withdraw", "Withdraw"),
        ("cancel", "Cancel"),
        ("resume", "Resume"),
        ("substitute_response", "Substitute Response"),
        ("review", "Review"),
        ("route", "Route"),
        ("sanction", "Sanction"),
    ]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="actions")
    actor_user_id = models.IntegerField()
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_request_action"

    def __str__(self) -> str:
        return f"{self.request_id} - {self.actor_user_id} - {self.action}"


class Resumption(TimeStampedModel):
    """EL-UC-011, BR-EL-034"""

    request = models.OneToOneField(
        LeaveRequest, on_delete=models.CASCADE, related_name="resumption"
    )
    resumed_on = models.DateField()
    outcome = models.CharField(
        max_length=10, choices=[("normal", "Normal"), ("early", "Early"), ("late", "Late")]
    )
    status = models.CharField(
        max_length=10,
        choices=[("submitted", "Submitted"), ("accepted", "Accepted"), ("rejected", "Rejected")],
    )
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_resumption"

    def __str__(self) -> str:
        return f"{self.request_id} - {self.resumed_on} - {self.outcome}"
