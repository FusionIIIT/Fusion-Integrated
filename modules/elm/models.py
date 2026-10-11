import uuid
from datetime import date, timedelta
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from core.models import BaseModel


class LeaveCategory(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Encashable Leave"
    COL = "COL", "Compensatory Leave"
    VL = "VL", "Vacation Leave"


class LeaveCategoryManager(models.Manager):
    def get_available_choices(self):
        return dict(LeaveCategory.choices)
