"""Holiday and academic vacation calendars."""

from django.db import models


class Calendar(models.Model):
    year = models.IntegerField(db_index=True)
    version = models.CharField(max_length=32)
    published = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_calendar"
        constraints = [
            models.UniqueConstraint(fields=["year", "version"], name="leave_cal_year_ver_unique"),
        ]

    def __str__(self) -> str:
        return (
            f"Calendar {self.year} v{self.version} ({'published' if self.published else 'draft'})"
        )


class Holiday(models.Model):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name="holidays")
    day = models.DateField(db_index=True)
    name = models.CharField(max_length=128)
    restricted = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_holiday"
        constraints = [
            models.UniqueConstraint(
                fields=["calendar", "day"], name="leave_holiday_cal_day_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"Holiday {self.day} - {self.name} ({'RH' if self.restricted else 'Closed'})"


class VacationPeriod(models.Model):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name="vacations")
    name = models.CharField(max_length=128)
    starts_on = models.DateField()
    ends_on = models.DateField()

    class Meta:
        db_table = "leave_vacation_period"

    def __str__(self) -> str:
        return f"Vacation {self.name} ({self.starts_on} to {self.ends_on})"
