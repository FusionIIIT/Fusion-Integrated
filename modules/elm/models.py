from django.db import models


class LeaveType(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    annual_quota = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    requires_attachment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class LeaveBalance(models.Model):
    employee_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name="balances",
    )
    year = models.PositiveSmallIntegerField()
    total_allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = [("employee_id", "leave_type", "year")]
        ordering = ["-year", "leave_type__code"]

    def __str__(self) -> str:
        return f"{self.employee_id}:{self.leave_type_id}:{self.year}"

    @property
    def remaining_days(self):
        return self.total_allocated - self.used_days


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
        ("CANCELLED", "Cancelled"),
    ]

    employee_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="requests",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=5, decimal_places=1)
    is_half_day = models.BooleanField(default=False)
    reason = models.TextField()
    contact_address = models.CharField(max_length=255, blank=True, default="")
    substitute_employee_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    reviewer_id = models.IntegerField(null=True, blank=True)
    review_comment = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"LeaveRequest({self.id}, emp={self.employee_id}, status={self.status})"
