from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel

LEAVE_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]


class LeaveType(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    max_days_per_year = models.PositiveIntegerField(default=12)
    carry_forward = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_type"

    def __str__(self):
        return self.name


class LeaveBalance(UserScopedModel, TimeStampedModel):
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name="leave_balances"
    )
    year = models.PositiveSmallIntegerField()
    total_days = models.PositiveIntegerField(default=0)
    used_days = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user_id", "leave_type", "year")

    @property
    def remaining_days(self) -> int:
        return self.total_days - self.used_days

    def __str__(self):
        return f"User {self.user_id} - {self.leave_type} ({self.year})"


class LeaveRequest(TimeStampedModel):
    employee_user_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name="leave_requests"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20, choices=LEAVE_STATUS_CHOICES, default="pending"
    )
    reviewed_by_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_date__lte=models.F("end_date")),
                name="elm_request_start_lte_end",
            )
        ]

    @property
    def user_id(self):
        return self.employee_user_id

    def __str__(self):
        return (
            f"User {self.employee_user_id} - {self.leave_type} "
            f"({self.start_date} to {self.end_date})"
        )
