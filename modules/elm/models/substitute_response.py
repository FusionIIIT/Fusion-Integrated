from django.db import models
from core.db.mixins import TimeStampedModel
from modules.elm.models.leave_request import LeaveRequest

class SubstituteResponse(TimeStampedModel):
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField()
    response = models.CharField(max_length=50, choices=[
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ])

    def __str__(self):
        return f"{self.leave_request.user_id} - {self.substitute_user_id} - {self.response}"
