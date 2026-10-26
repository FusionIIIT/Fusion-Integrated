from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveType(TimeStampedModel):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=64)
    max_days_per_year = models.PositiveSmallIntegerField()
    requires_document = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type"


class LeaveBalance(TimeStampedModel):
    employee_id = models.IntegerField()
    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField()
    allotted = models.DecimalField(max_digits=10, decimal_places=2)
    used = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("employee_id", "leave_type", "year")


class LeaveApplication(TimeStampedModel):
    employee_id = models.IntegerField()
    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day_period = models.CharField(
        max_length=16,
        choices=[
            ("FIRST_HALF", "First Half"),
            ("SECOND_HALF", "Second Half"),
        ],
        blank=True,
        default="",
    )
    days = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], default="DRAFT")
    approver_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_application"
