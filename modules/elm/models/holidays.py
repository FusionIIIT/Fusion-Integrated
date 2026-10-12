"""Holiday Calendar and Vacation Period Models for ELM."""
from django.db import models

from core.db.mixins import TimeStampedModel


class HolidayCalendar(TimeStampedModel):
    """Institute Holiday Calendar supporting Closed Holidays and Restricted Holidays."""

    HOLIDAY_TYPES = [
        ("closed", "Closed Institute Holiday"),
        ("restricted", "Restricted Holiday (RH)"),
        ("vacation", "Faculty Vacation Period"),
    ]

    date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, help_text="Used for vacation ranges")
    name = models.CharField(max_length=120)
    holiday_type = models.CharField(max_length=16, choices=HOLIDAY_TYPES)
    year = models.IntegerField(db_index=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        constraints = [
            models.UniqueConstraint(
                fields=["date", "holiday_type"],
                name="elm_unique_date_holiday_type",
            )
        ]
        indexes = [
            models.Index(fields=["year", "holiday_type"], name="elm_holiday_year_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.date}: {self.name} ({self.holiday_type})"
