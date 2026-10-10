from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.elm.models.leave_type import LeaveType

class LeaveBalance(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user_id} - {self.leave_type.name} - {self.balance}"
