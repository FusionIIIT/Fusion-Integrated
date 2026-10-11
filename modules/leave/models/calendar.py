"""Holiday calendar models.

BR-EL-031: Effective published holiday and Restricted Holiday calendar.
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class HolidayCalendar(TimeStampedModel):
    year = models.IntegerField(unique=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-year"]


class HolidayItem(TimeStampedModel):
    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE, related_name="items")
    date = models.DateField()
    name = models.CharField(max_length=150)
    is_restricted_holiday = models.BooleanField(default=False)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"], name="unique_holiday_per_calendar_date")
        ]
