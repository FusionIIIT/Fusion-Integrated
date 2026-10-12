from django.db import models
from core.db.mixins import TimeStampedModel


class LeaveCategory(TimeStampedModel):
    name = models.CharField(
        max_length=20,
        choices=[
            ("CL", "Compensation Leave"),
            ("RH", "Resignation Leave"),
            ("SCL", "Sick Leave"),
            ("EL", "Earned Leave"),
            ("COL", "Casual Leave"),
            ("VL", "Vocation Leave"),
        ],
    )
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel):
    employee_id = models.IntegerField()

    leave_category = models.CharField(
        max_length=20,
        choices=[
            ("CL", "Compensation Leave"),
            ("RH", "Resignation Leave"),
            ("SCL", "Sick Leave"),
            ("EL", "Earned Leave"),
            ("COL", "Casual Leave"),
            ("VL", "Vocation Leave"),
        ],
    )

    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("canceled", "Canceled"),
            ("extended", "Extended"),
        ],
    )

    station_leave_details = models.TextField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.employee_id} - {self.leave_category} - "
            f"{self.start_date} to {self.end_date}"
        )