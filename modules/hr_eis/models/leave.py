from django.db import models
from modules.hr_eis.models.employee import EmployeeProfile
from modules.hr_eis.contracts import LeaveTypes, LeaveStatus

class LeaveBalance(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.CharField(max_length=50, choices=LeaveTypes.CHOICES)
    year = models.IntegerField(default=2026)
    entitled_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        unique_together = ("employee", "leave_type", "year")

    @property
    def available_days(self):
        return max(0.0, float(self.entitled_days - self.used_days))

    def __str__(self):
        return f"{self.employee.employee_id} {self.leave_type} {self.year}: {self.available_days} left"

class LeaveRequest(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=50, choices=LeaveTypes.CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()
    status = models.CharField(max_length=30, choices=LeaveStatus.CHOICES, default=LeaveStatus.SUBMITTED, db_index=True)
    current_authority = models.CharField(max_length=50, default="HOD")
    remarks = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Leave #{self.id} ({self.employee.employee_id} - {self.leave_type} [{self.status}])"
