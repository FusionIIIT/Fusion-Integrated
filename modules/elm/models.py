# ELM ORM Layer: Defines database schema. No business logic allowed.

from django.db import models

class LeaveType(models.Model):
    """Defines valid leave types: CL, RH, SCL, EL, COL, VL."""
    name = models.CharField(max_length=10, unique=True)
    description = models.TextField()
    # Other basic configuration fields...

class EmployeeLeaveBalance(models.Model):
    """Tracks current and entitled leave balances."""
    employee_id = models.CharField(max_length=100) # References IAM erp_user_id
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=6, decimal_places=2)
    entitlement = models.DecimalField(max_digits=6, decimal_places=2)

class LeaveApplication(models.Model):
    """The core record of a submitted or processed leave request."""
    employee_id = models.CharField(max_length=100)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=50) # PENDING, APPROVED, REJECTED, WITHDRAWN, CANCELLED
    sanctioning_authority = models.CharField(max_length=100, null=True, blank=True)
    is_station_leave = models.BooleanField(default=False)

    class Meta:
        unique_together = [['employee_id', 'start_date', 'leave_type']]
        ordering = ['start_date']
