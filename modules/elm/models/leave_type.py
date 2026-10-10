from django.db import models
from core.db.mixins import TimeStampedModel

class LeaveType(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
