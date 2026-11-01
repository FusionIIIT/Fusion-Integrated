"""The published holiday and restricted-holiday calendar (BR-EL-003, BR-EL-031).

Publishing a replacement makes it effective; the previous one is kept, because
a request validated last month has to stay explainable this month.
"""

from django.db import models

from core.db.mixins import TimeStampedModel


class HolidayCalendar(TimeStampedModel):
    """One calendar edition. Unpublished rows validate nothing."""

    year = models.PositiveSmallIntegerField()
    version = models.PositiveSmallIntegerField(default=1)
    label = models.CharField(max_length=80, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        ordering = ["-year", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["year", "version"],
                                    name="holiday_calendar_year_version"),
        ]

    @property
    def is_published(self) -> bool:
        return self.published_at is not None

    def __str__(self) -> str:
        return f"{self.year} v{self.version}"


class HolidayCalendarDay(TimeStampedModel):
    """One dated entry. `kind` decides whether RH validation may use it."""

    KINDS = [("holiday", "Closed holiday"), ("restricted", "Restricted holiday")]

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="days")
    date = models.DateField()
    kind = models.CharField(max_length=12, choices=KINDS, default="holiday")
    name = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "leave_holiday_calendar_day"
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"],
                                    name="holiday_calendar_day_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.name}".strip()
