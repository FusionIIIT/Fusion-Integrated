from django.db import models


LEAVE_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    max_days_per_year = models.PositiveIntegerField(default=12)
    carry_forward = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_type"

    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    user_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField()
    total_days = models.PositiveIntegerField(default=0)
    used_days = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user_id", "leave_type", "year")

    @property
    def remaining_days(self):
        return self.total_days - self.used_days

    def __str__(self):
        return f"User {self.user_id} - {self.leave_type} ({self.year})"


class LeaveRequest(models.Model):
    employee_user_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=LEAVE_STATUS_CHOICES, default="pending")
    remarks = models.TextField(blank=True, default="")
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Employee {self.employee_user_id} - {self.leave_type} ({self.start_date} to {self.end_date})"
