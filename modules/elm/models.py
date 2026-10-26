from django.db import models
from django.utils import timezone


def current_year():
    return timezone.localdate().year


class LeaveType(models.Model):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"
    STATION_LEAVE = "STATION_LEAVE"

    TYPE_CHOICES = [
        (CL, "Casual Leave"),
        (RH, "Restricted Holiday"),
        (SCL, "Special Casual Leave"),
        (EL, "Earned Leave"),
        (COL, "Commuted Leave"),
        (VL, "Vacation Leave"),
        (STATION_LEAVE, "Station Leave"),
    ]

    type = models.CharField(max_length=13, choices=TYPE_CHOICES)
    days_allowed = models.PositiveIntegerField(default=0)
    carry_forward = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)

    def __str__(self):
        return self.get_type_display()

    @classmethod
    def current_year(cls):
        return timezone.localdate().year


class LeaveBalance(models.Model):
    employee = models.BigIntegerField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    year = models.PositiveIntegerField(default=current_year)
    employee_kind = models.CharField(
        max_length=10, choices=[("faculty", "Faculty"), ("staff", "Staff")], default="staff"
    )
    last_updated = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.balance} days)"


class LeavePolicy(models.Model):
    type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    max_days = models.PositiveIntegerField(default=0)
    carry_forward = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)
    medical_evidence_required = models.BooleanField(default=False)
    applicable_kind = models.CharField(
        max_length=10, choices=[("faculty", "Faculty"), ("staff", "Staff")], blank=True
    )
    reminder_hours = models.PositiveIntegerField(default=24)
    escalation_hours = models.PositiveIntegerField(default=48)
    holiday_calendar = models.BigIntegerField(null=True)

    def __str__(self):
        return f"{self.type} Policy"


class LeaveRequest(models.Model):
    employee = models.BigIntegerField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    substitute = models.BigIntegerField(null=True, blank=True)
    employee_kind = models.CharField(
        max_length=10, choices=[("faculty", "Faculty"), ("staff", "Staff")], default="staff"
    )
    unit = models.CharField(max_length=255, blank=True)
    half_day = models.CharField(
        max_length=10,
        choices=[("FULL", "Full"), ("FIRST", "First Half"), ("SECOND", "Second Half")],
        default="FULL",
    )
    station_leave = models.BooleanField(default=False)
    station_details = models.TextField(blank=True)
    medical_evidence = models.TextField(blank=True)
    days = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    substitute_status = models.CharField(
        max_length=15,
        choices=[
            ("NONE", "None"),
            ("PENDING", "Pending"),
            ("ACCEPTED", "Accepted"),
            ("DECLINED", "Declined"),
        ],
        default="NONE",
    )
    route = models.JSONField(default=list, blank=True)
    step = models.PositiveIntegerField(default=0)
    operation = models.CharField(
        max_length=15,
        choices=[
            ("LEAVE", "Leave"),
            ("CANCELLATION", "Cancellation"),
            ("EXTENSION", "Extension"),
            ("RESUMPTION", "Resumption"),
        ],
        default="LEAVE",
    )
    base_request = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="amendments", null=True
    )
    actual_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=[
            ("PENDING", "Pending"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
            ("CANCELLED", "Cancelled"),
            ("WITHDRAWN", "Withdrawn"),
            ("RESUMED", "Resumed"),
        ],
        default="PENDING",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.start_date} - {self.end_date})"


class AuthorityRoute(models.Model):
    employee = models.BigIntegerField()
    unit = models.CharField(max_length=255, blank=True)
    leave_category = models.CharField(max_length=13, blank=True)
    unit_head = models.BigIntegerField(null=True, blank=True)
    higher_authorities = models.JSONField(default=list, blank=True)
    director_self = models.BooleanField(default=False)

    class Meta:
        unique_together = ["employee", "unit", "leave_category"]

    def __str__(self):
        return f"{type(self).__name__} {self.pk}"


class CalendarDay(models.Model):
    date = models.DateField()
    kind = models.CharField(
        max_length=10,
        choices=[("CLOSED", "Closed"), ("RH", "Restricted Holiday"), ("VACATION", "Vacation")],
    )
    published = models.BooleanField(default=False)
    source = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ["date", "kind"]

    def __str__(self):
        return f"{type(self).__name__} {self.pk}"


class LeaveEvent(models.Model):
    request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, related_name="events", null=True
    )
    employee = models.BigIntegerField()
    actor = models.BigIntegerField(null=True, blank=True)
    action = models.CharField(max_length=64)
    delta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{type(self).__name__} {self.pk}"


class YearEndRun(models.Model):
    year = models.PositiveIntegerField(unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{type(self).__name__} {self.pk}"
