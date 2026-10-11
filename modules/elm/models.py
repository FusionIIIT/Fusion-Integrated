from django.db import models

class LeaveApplication(models.Model):
    employee = models.ForeignKey('core.Employee', on_delete=models.CASCADE)
    leave_category = models.CharField(max_length=50)
    requested_period = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=20, default='Pending')

    def __str__(self):
        return f"{self.employee.name} - {self.leave_category} - {self.requested_period}"
