from django.db import models

from core.db.mixins import TimeStampedModel
from modules.directory.models import UserRef


class LeaveType(TimeStampedModel):
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type"

    def __str__(self) -> str:
        return self.name


class LeaveBalance(TimeStampedModel):
    employee = models.ForeignKey(UserRef, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField()
    entitled_days = models.DecimalField(max_digits=5, decimal_places=2)
    used_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("employee", "leave_type", "year")

    def __str__(self) -> str:
        return f"{self.employee} - {self.leave_type} - {self.year}"


class LeaveApplication(TimeStampedModel):
    applicant = models.ForeignKey(UserRef, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    is_half_day = models.BooleanField(default=False)
    reason = models.TextField()
    substitute = models.ForeignKey(UserRef, null=True, blank=True, related_name="substituted_for", on_delete=models.SET_NULL)
    status = models.CharField(max_length=10, choices=[
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
        ("CANCELLED", "Cancelled")
    ], default="PENDING")
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(UserRef, null=True, blank=True, related_name="decided_leave_applications", on_delete=models.SET_NULL)

    class Meta:
        db_table = "elm_leave_application"

    def __str__(self) -> str:
        return f"{self.applicant} - {self.leave_type} - {self.status}"
