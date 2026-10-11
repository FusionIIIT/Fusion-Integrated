from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveType(TimeStampedModel):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=128)
    max_days_per_year = models.PositiveSmallIntegerField()
    requires_document = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type"


class LeaveBalance(TimeStampedModel):
    employee_id = models.IntegerField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField()
    allotted = models.PositiveSmallIntegerField()
    used = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("employee_id", "leave_type", "year")


class LeaveApplication(TimeStampedModel):
    employee_id = models.IntegerField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveSmallIntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], default="DRAFT")
    approver_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_application"
