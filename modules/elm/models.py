
from django.db import models
from django.core.exceptions import ValidationError

from core.db.mixins import TimeStampedModel


class LeaveType(models.TextChoices):
    COMPENSATION = "CL", "Compensation Leave"
    RESIGNATION = "RH", "Resignation Leave"
    SICK = "SCL", "Sick Leave"
    EARNED = "EL", "Earned Leave"
    CASUAL = "COL", "Casual Leave"
    VACATION = "VL", "Vacation Leave"

class LeaveStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELED = "canceled", "Canceled"
    EXTENDED = "extended", "Extended"


class LeaveCategory(TimeStampedModel):
    name = models.CharField(
        max_length=3,
        choices=LeaveType.choices,
        unique=True,
    )
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.get_name_display()


class LeaveApplication(TimeStampedModel):
    employee_id = models.IntegerField()
    leave_category = models.CharField(
        max_length=3,
        choices=LeaveType.choices,
    )             
    start_date = models.DateField() 
    end_date = models.DateField() 
    reason = models.TextField()
    status = models.CharField(  
        max_length=10, 
        choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING,
    )
    station_leave_details = models.TextField(
        null=True,
        blank=True,
    ) 

    def clean(self):
        super().clean()

        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({
                    "end_date": "End date cannot be before start date."
                })

    def __str__(self): 
        return ( 
            f"{self.employee_id} - {self.leave_category} - "
            f"{self.start_date} to {self.end_date}"
        ) 
