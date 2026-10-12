"""Holiday / Restricted-Holiday calendars and Academic Calendar vacations.

BR-EL-031: a calendar is versioned draft → published; only the currently
effective *published* calendar validates RH dates (CFR-EL-005.2). Vacation
periods come from the Academic Calendar (EXT-01) and gate VL (BR-EL-006).
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class HolidayCalendar(TimeStampedModel):
    DRAFT = "draft"
    PUBLISHED = "published"
    STATUS = [(DRAFT, "Draft"), (PUBLISHED, "Published")]

    title = models.CharField(max_length=120)
    academic_year = models.CharField(max_length=20, blank=True)  # "2026-27"
    status = models.CharField(max_length=12, choices=STATUS, default=DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        ordering = ["-published_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"


class Holiday(TimeStampedModel):
    CLOSED = "closed"          # institute closed: CL/SCL/RH do not count it
    RESTRICTED = "restricted"  # Restricted Holiday: the only RH-valid dates

    KIND = [(CLOSED, "Closed day"), (RESTRICTED, "Restricted Holiday")]

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="holidays")
    date = models.DateField()
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=12, choices=KIND, default=CLOSED)

    class Meta:
        db_table = "leave_holiday"
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"],
                                    name="leave_holiday_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.date.isoformat()} {self.name}"


class VacationPeriod(TimeStampedModel):
    """EXT-01 input: an Academic Calendar window inside which VL may be taken."""

    name = models.CharField(max_length=120)
    academic_year = models.CharField(max_length=20, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    source_ref = models.CharField(max_length=200, blank=True)  # calendar doc

    class Meta:
        db_table = "leave_vacation_period"
        ordering = ["start_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="leave_vacation_interval_valid"),
        ]

    def __str__(self) -> str:
        return f"{self.name} {self.start_date}…{self.end_date}"
