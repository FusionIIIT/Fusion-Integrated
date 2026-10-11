# entire file content 
from django.db import models
from django.contrib.auth import get_user_model

class LeaveApplication(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    # ... rest of code
