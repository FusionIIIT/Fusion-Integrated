"""The holiday/RH calendar and the vacation periods behind Vacation Leave.

The calendar is the one effective-dated surface: validation uses the currently
effective published calendar until a replacement is published (BR-EL-031).
Vacation periods stand in for EXT-01, the institute Academic Calendar, which the
platform does not carry; an administrator maintains them here (BR-EL-006).
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel

DRAFT = "draft"
PUBLISHED = "published"


class HolidayCalendar(TimeStampedModel):
    year = models.PositiveSmallIntegerField(unique=True)
    status = models.CharField(max_length=12, choices=[(DRAFT, DRAFT),
                                                      (PUBLISHED, PUBLISHED)],
                              default=DRAFT)
    #: The single calendar validation reads, so a replacement only takes effect
    #: when it is published.
    is_effective = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-year",)

    def __str__(self) -> str:
        return f"{self.year} holiday calendar ({self.status})"

    def publish(self, *, now) -> None:
        HolidayCalendar.objects.filter(is_effective=True).exclude(
            pk=self.pk).update(is_effective=False)
        self.status = PUBLISHED
        self.is_effective = True
        self.published_at = now
        self.save(update_fields=["status", "is_effective", "published_at",
                                 "updated_at"])


class Holiday(TimeStampedModel):
    """One closed holiday, or one applicable Restricted Holiday."""

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="holidays")
    date = models.DateField(db_index=True)
    name = models.CharField(max_length=120)
    is_restricted_holiday = models.BooleanField(default=False)

    class Meta:
        ordering = ("date",)
        constraints = [
            models.UniqueConstraint(fields=("calendar", "date"),
                                    name="leave_holiday_unique_date"),
        ]

    def __str__(self) -> str:
        return f"{self.date:%Y-%m-%d} {self.name}"


class VacationPeriod(TimeStampedModel):
    """EXT-01 stand-in: a published vacation period from the Academic Calendar."""
    label = models.CharField(max_length=120)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField()
    year = models.PositiveSmallIntegerField(db_index=True)
    source_reference = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Where the institute Academic Calendar published this period.")

    class Meta:
        ordering = ("start_date",)
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="leave_vacation_period_ordered"),
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.start_date}..{self.end_date})"