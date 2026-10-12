from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class Holiday(TimeStampedModel):
    """EL-UC-015, BR-EL-031"""

    name = models.CharField(max_length=120)
    date = models.DateField()
    is_restricted = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_holiday"
        constraints = [
            models.UniqueConstraint(fields=["date", "name"], name="holiday_unique_date_name"),
        ]
        indexes = [
            models.Index(fields=["date"], name="holiday_date_idx"),
            models.Index(fields=["is_published"], name="holiday_published_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.date})"
