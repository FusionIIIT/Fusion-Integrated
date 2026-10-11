from django.db import models
from django.contrib.auth.models import User


class LeaveType(models.Model):
    LEAVE_TYPES = (
        ('CL', 'Casual Leave'),
        ('RH', 'Restricted Holiday'),
        ('SCL', 'Sick Leave'),
        ('EL', 'Earned Leave'),
        ('VL', 'Voluntary Leave'),
        ('COL', 'Compensatory Off Leave'),
    )
    name = models.CharField(max_length=3, choices=LEAVE_TYPES)


class LeaveStatus(models.Model):
    STATUS_TYPES = (
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('RECOMMENDED', 'Recommended'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('FORWARDED', 'Forwarded'),
    )
    name = models.CharField(max_length=10, choices=STATUS_TYPES)


class LeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    academic_year = models.CharField(max_length=9)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    allocated_days = models.IntegerField()
    consumed_days = models.IntegerField()
    remaining_days = models.IntegerField()


class EmployeeLeave(models.Model):
    applicant = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.IntegerField()
    purpose = models.TextField()
    status = models.ForeignKey(LeaveStatus, on_delete=models.CASCADE)
    unit_head = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unit_head')
    remarks = models.TextField()

    def clean(self):
        # validation logic here
        pass

    def deduct_balance(self):
        # deduct balance logic here
        pass


class StationLeaveDetail(models.Model):
    leave_application = models.OneToOneField(EmployeeLeave, on_delete=models.CASCADE)
    station_start = models.CharField(max_length=200)
    station_end = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    emergency_contact = models.CharField(max_length=200)