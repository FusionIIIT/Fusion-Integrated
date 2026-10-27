"""Holidays and Vacation Periods."""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel


class HolidayCalendar(TimeStampedModel):
    """Institute closed holidays and restricted holidays (BR-EL-003, BR-EL-031)."""

    KINDS = [
        ("closed", "Closed Holiday"),
        ("restricted", "Restricted Holiday"),
    ]

    name = models.CharField(max_length=150)
    date = models.DateField(db_index=True)
    kind = models.CharField(max_length=15, choices=KINDS, default="closed")
    year = models.PositiveSmallIntegerField(db_index=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.date} - {self.name} ({self.kind})"


class VacationPeriod(TimeStampedModel):
    """Academic Calendar vacation windows for Faculty VL (BR-EL-006, EXT-01)."""

    name = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField()
    year = models.PositiveSmallIntegerField(db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_vacation_period"
        ordering = ["start_date"]

    def __str__(self) -> str:
        return f"{self.name}: {self.start_date} to {self.end_date}"
