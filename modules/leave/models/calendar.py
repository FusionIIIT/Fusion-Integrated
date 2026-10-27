from django.db import models
from core.db.mixins import TimeStampedModel

class HolidayCalendar(TimeStampedModel):
    year = models.PositiveSmallIntegerField(db_index=True)
    date = models.DateField(db_index=True)
    kind = models.CharField(max_length=20, choices=[("closed", "Closed Holiday"), ("restricted", "Restricted Holiday")])
    title = models.CharField(max_length=255)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        constraints = [
            models.UniqueConstraint(fields=["date"], name="leave_holiday_unique_date")
        ]
        ordering = ["date"]

class VacationPeriod(TimeStampedModel):
    year = models.PositiveSmallIntegerField(db_index=True)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_vacation_period"
        ordering = ["start_date"]