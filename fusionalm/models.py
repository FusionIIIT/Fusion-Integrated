from django.db import models
from fusionalm.base.models import BaseModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

class LeaveType(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

class Leave(models.Model):
    employee = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=['PENDING', 'APPROVED', 'REJECTED'])
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

class LeaveRequest(models.Model):
    employee = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=['PENDING', 'APPROVED', 'REJECTED'])
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
