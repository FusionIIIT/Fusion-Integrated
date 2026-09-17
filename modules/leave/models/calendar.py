"""Closed days, restricted holidays and vacation periods."""
from django.db import models

from core.db.mixins import TimeStampedModel


class HolidayCalendar(TimeStampedModel):
    """The published calendar for one year."""

    year = models.IntegerField(db_index=True)
    version = models.CharField(max_length=32)
    published = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_holiday_calendar"
        ordering = ["-year", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["year", "version"], name="leave_calendar_unique_version"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.year} calendar {self.version}"


class Holiday(TimeStampedModel):
    """A closed day, or a restricted holiday an employee may elect to take."""

    calendar = models.ForeignKey(
        HolidayCalendar, on_delete=models.CASCADE, related_name="holidays"
    )
    day = models.DateField()
    name = models.CharField(max_length=120)
    #: BR-EL-003. A restricted holiday is not closed; RH must match one of these.
    restricted = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_holiday"
        constraints = [
            models.UniqueConstraint(
                fields=["calendar", "day", "restricted"], name="leave_holiday_unique_day"
            ),
        ]
        indexes = [
            models.Index(fields=["calendar", "restricted"], name="leave_holiday_kind_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.day} {self.name}"


class VacationPeriod(TimeStampedModel):
    """A published vacation window."""

    calendar = models.ForeignKey(
        HolidayCalendar, on_delete=models.CASCADE, related_name="vacation_periods"
    )
    name = models.CharField(max_length=120)
    starts_on = models.DateField()
    ends_on = models.DateField()

    class Meta:
        db_table = "leave_vacation_period"
        ordering = ["starts_on"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_on__gte=models.F("starts_on")),
                name="leave_vacation_period_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["calendar", "starts_on"], name="leave_vacation_window_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} {self.starts_on} to {self.ends_on}"
