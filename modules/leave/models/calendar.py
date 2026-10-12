"""Holiday / restricted-holiday calendar (blueprint Step 3.2).

The publish lifecycle is specified (PS §12 ¶47, CFR-EL-025, BR-EL-031): a
calendar is maintained, then published, and only the effective published
calendar validates dates. What "governing a date range" means — inclusive
endpoints, overlap behaviour, whether a successor may be published before its
predecessor ends — is not stated, so the governing range is a PROVISIONAL
placeholder (blueprint §3.8 #5/#11) and **no** uniqueness or overlap constraint
is applied.

The calendar's relationship to the external Academic Calendar used for VL
vacation periods (BR-EL-006) is also unresolved (#11); that calendar is not
modelled here.
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class HolidayCalendar(TimeStampedModel):
    """A published holiday/RH calendar — PROVISIONAL range (#5/#11)."""

    label = models.CharField(max_length=120)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    #: PROVISIONAL placeholders for the governing range and provenance the
    #: constraint would need. Their meaning is unresolved; none is required.
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        indexes = [
            models.Index(fields=["is_published", "effective_from"],
                         name="leave_calendar_published_idx"),
        ]

    def __str__(self) -> str:
        return self.label


class HolidayCalendarDay(TimeStampedModel):
    """One dated entry on a calendar — EXPLICIT (BR-EL-031, BR-EL-003)."""

    KIND = [
        ("closed_holiday", "Closed holiday"),
        ("restricted_holiday", "Restricted holiday"),
    ]

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="days")
    date = models.DateField()
    kind = models.CharField(max_length=20, choices=KIND)

    class Meta:
        db_table = "leave_holiday_calendar_day"
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date", "kind"],
                                    name="leave_holiday_day_unique"),
        ]
        indexes = [models.Index(fields=["date", "kind"],
                                name="leave_holiday_day_date_idx")]

    def __str__(self) -> str:
        return f"{self.date} {self.kind}"
