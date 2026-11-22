from django.db import models


class LeaveType(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL = "VL", "Vacation Leave"


class LeaveStatus(models.TextChoices):
    PENDING_SUBSTITUTE = "PENDING_SUBSTITUTE", "Pending Substitute Consent"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
    RECOMMENDED = "RECOMMENDED", "Recommended"
    NOT_RECOMMENDED = "NOT_RECOMMENDED", "Not Recommended"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    CANCELLED = "CANCELLED", "Cancelled"


class LeaveBalance(models.Model):
    employee_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=10, choices=LeaveType.choices)
    year = models.IntegerField()
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    balance = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("employee_id", "leave_type", "year")

    def __str__(self):
        return f"Emp {self.employee_id} - {self.leave_type} ({self.year}): {self.balance}"


class LeaveRequest(models.Model):
    applicant_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=10, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=20, blank=True, null=True)
    purpose = models.TextField()
    is_station_leave = models.BooleanField(default=False)
    station_details = models.TextField(blank=True, null=True)
    substitute_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=30, default="NOT_REQUIRED")
    status = models.CharField(max_length=30, choices=LeaveStatus.choices, default=LeaveStatus.PENDING_APPROVAL)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Request #{self.id} - Emp {self.applicant_id} - {self.leave_type} ({self.status})"


class LeaveActionHistory(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="actions")
    actor_id = models.IntegerField()
    action = models.CharField(max_length=50)
    comments = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_action_history"
        ordering = ["timestamp"]


class HolidayCalendar(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=100)
    is_restricted = models.BooleanField(default=False)
    year = models.IntegerField(db_index=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["date"]

    def __str__(self):
        label = "RH" if self.is_restricted else "Closed"
        return f"{self.date} - {self.name} ({label})"
