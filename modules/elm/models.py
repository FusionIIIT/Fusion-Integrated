from django.db import models

class LeaveType(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class LeaveStatus(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class LeaveRequest(models.Model):
    employee = models.ForeignKey('directory.UserRef', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.ForeignKey(LeaveStatus, on_delete=models.CASCADE)
    substitute = models.ForeignKey('directory.UserRef', on_delete=models.SET_NULL, null=True, blank=True, related_name='substitute_for')

    def __str__(self):
        return f"{self.employee}'s leave request"
