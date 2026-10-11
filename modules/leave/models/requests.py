"""Leave requests and transition trail."""

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]
    HALF_CHOICES = [
        ("none", "None"),
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ]

    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    state = models.CharField(max_length=32, default="draft", db_index=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    half = models.CharField(max_length=16, choices=HALF_CHOICES, default="none")
    reason = models.TextField()
    evidence_reference = models.CharField(max_length=255, blank=True)

    requested_days = models.DecimalField(max_digits=5, decimal_places=2)
    actual_days = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=255, blank=True)

    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    extension_to = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="extensions"
    )

    unit_head_recommended = models.BooleanField(null=True, blank=True)
    sanctioning_designation = models.CharField(max_length=128, blank=True)
    resumed_on = models.DateField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        indexes = [
            models.Index(fields=["user_id", "state"], name="leave_req_user_state_idx"),
            models.Index(fields=["category", "starts_on"], name="leave_req_cat_date_idx"),
        ]

    def __str__(self) -> str:
        return f"LeaveRequest#{self.pk} u{self.user_id} {self.category} ({self.state})"


class LeaveTransition(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="transitions")
    from_state = models.CharField(max_length=32)
    to_state = models.CharField(max_length=32)
    event = models.CharField(max_length=32)
    actor_role = models.CharField(max_length=128, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remark = models.TextField(blank=True)
    workflow_ref = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_transition"
        indexes = [
            models.Index(fields=["request", "created_at"], name="leave_trans_req_idx"),
        ]

    def __str__(self) -> str:
        return f"Transition#{self.pk} req#{self.request_id} {self.from_state}->{self.to_state}"
