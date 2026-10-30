from django.db import models
from core.db.mixins import TimeStampedModel


class HolidayCalendar(TimeStampedModel):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=128)
    is_restricted_holiday = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    year = models.IntegerField(db_index=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["date"]

    def __str__(self) -> str:
        kind = "RH" if self.is_restricted_holiday else "Closed"
        return f"{self.date} ({kind}): {self.name}"


class AcademicVacationPeriod(TimeStampedModel):
    name = models.CharField(max_length=128)
    start_date = models.DateField()
    end_date = models.DateField()
    academic_year = models.CharField(max_length=32)

    class Meta:
        db_table = "elm_academic_vacation_period"
        ordering = ["start_date"]

    def __str__(self) -> str:
        return f"{self.name} [{self.start_date} to {self.end_date}]"
