from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("awaiting_substitute", "Awaiting Substitute"),
        ("pending_unit_head", "Pending Unit Head"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ]

    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Compensatory Leave"),
        ("VL", "Vacation Leave"),
    ]

    user_id = models.IntegerField()
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    station_leave_outside_jabalpur = models.BooleanField(default=False)
    station_leave_details = models.TextField(blank=True, null=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    days_counted = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = "leave_request"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "start_date", "end_date"],
                                    name="request_unique_per_user_and_dates"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="request_user_idx"),
        ]

    def __str__(self) -> str:
        return f"req#{self.pk} u{self.user_id} {self.category} {self.status}"


class LeaveRequestHistory(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="history")
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    actor_user_id = models.IntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_request_history"
        indexes = [models.Index(fields=["request", "at"],
                                name="history_request_idx")]

    def __str__(self) -> str:
        return f"req#{self.request_id} {self.from_status}->{self.to_status}"
