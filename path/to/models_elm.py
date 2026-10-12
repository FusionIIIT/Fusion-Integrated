from django.db import models
from django.contrib.auth.models import User

class LeaveApplication(models.Model):
    applicant = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    chargeable_days = models.IntegerField()
    status = models.CharField(max_length=20)
    purpose = models.TextField()
    is_station_leave = models.BooleanField()

class SubstituteAssignment(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
