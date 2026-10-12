"""Holiday / RH calendar and academic vacation periods (BR-EL-003, BR-EL-006,
BR-EL-031).

The currently effective calendar is the most recently published one; a
replacement only takes effect once published.
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class HolidayCalendar(TimeStampedModel):
    name = models.CharField(max_length=120)
    year = models.PositiveSmallIntegerField(db_index=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["-year", "-published_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.year})"


class Holiday(TimeStampedModel):
    KINDS = [("closed", "Closed holiday"), ("restricted", "Restricted holiday")]

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="holidays")
    date = models.DateField(db_index=True)
    kind = models.CharField(max_length=12, choices=KINDS, default="closed")
    name = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "elm_holiday"
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date", "kind"],
                                    name="elm_holiday_unique_per_day"),
        ]
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.date} {self.kind}"


class VacationPeriod(TimeStampedModel):
    """Faculty vacation windows from the institute Academic Calendar
    (BR-EL-006). ELM caches them; the Calendar office owns them."""

    label = models.CharField(max_length=120)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField()
    academic_year = models.CharField(max_length=16, blank=True)

    class Meta:
        db_table = "elm_vacation_period"
        ordering = ["start_date"]

    def __str__(self) -> str:
        return f"{self.label} ({self.start_date}..{self.end_date})"
