from django.db import models


class LeaveType(models.Model):
    name = models.CharField(max_length=100)


class LeaveStatus(models.Model):
    name = models.CharField(max_length=100)


class LeaveRequest(models.Model):
    employee = models.ForeignKey('directory.UserRef', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.ForeignKey(LeaveStatus, on_delete=models.CASCADE)
    substitute = models.ForeignKey('directory.UserRef', on_delete=models.CASCADE, null=True, blank=True, related_name='substitute_for')
