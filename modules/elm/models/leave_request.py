from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.elm.models.leave_type import LeaveType

class LeaveRequest(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ])

    def __str__(self):
        return f"{self.user_id} - {self.leave_type.name} ({self.start_date} to {self.end_date})"
