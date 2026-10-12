"""Publication-managed holiday/RH calendar and VL vacation periods."""

from django.db import models

from core.db.mixins import TimeStampedModel

from modules.elm.models.hierarchy import ELMPolicy
from modules.elm.models.requests import LeaveApplication


class HolidayCalendar(TimeStampedModel):
    """The currently effective published holiday/RH calendar.

    Until a replacement is published, the existing published calendar remains
    governing; the publish action swaps the effective calendar.
    """

    STATUS = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("superseded", "Superseded"),
    ]

    code = models.CharField(
        max_length=64,
        unique=True,
        help_text="Planner-facing identifier, e.g. holiday_calendar_2027.",
    )
    label = models.CharField(max_length=120, help_text="Human-readable name.")
    start_on = models.DateField(null=True, blank=True, help_text="First date covered.")
    end_on = models.DateField(null=True, blank=True, help_text="Last date covered.")
    status = models.CharField(max_length=16, choices=STATUS, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        indexes = [
            models.Index(fields=["status", "published_at"], name="holiday_status_published_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.status})"


class HolidayEntry(TimeStampedModel):
    """One date, a set of leave categories it applies to, and its type."""

    calendar = models.ForeignKey(
        HolidayCalendar,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    date = models.DateField(db_index=True, help_text="Closed holiday or restricted holiday.")
    category = models.CharField(
        max_length=32,
        choices=[
            ("RH", "Restricted Holiday"),
            ("CH", "Closed Holiday"),
        ],
        db_index=True,
    )
    note = models.CharField(
        max_length=300,
        blank=True,
        help_text="Optional evidence or note, e.g. governing order number.",
    )

    class Meta:
        db_table = "elm_holiday_entry"
        constraints = [
            models.UniqueConstraint(
                fields=["calendar", "date"],
                name="holiday_entry_unique_date_per_calendar",
            ),
        ]
        indexes = [
            models.Index(fields=["category", "date"], name="holiday_entry_category_date"),
        ]

    def __str__(self) -> str:
        return f"{self.get_category_display()} {self.date}"


class VacationPeriod(TimeStampedModel):
    """A published vacation period used for VL applicability only.

    This is an ELM-side projection of the institute Academic Calendar that lives
    outside ELM. The governing data comes from EXT-01; this table adapts it for
    ELM validation.
    """

    category = models.ForeignKey(
        ELMPolicy,
        on_delete=models.CASCADE,
        related_name="vacation_periods",
    )
    label = models.CharField(max_length=120, help_text="e.g. Summer vacation.")
    start_on = models.DateField(db_index=True, help_text="Vacation period begins.")
    end_on = models.DateField(
        db_index=True,
        help_text="Vacation period ends; a student may avail VL up to and including this date.",
    )

    class Meta:
        db_table = "elm_vacation_period"
        indexes = [
            models.Index(fields=["category", "start_on"], name="vacation_category_start_idx"),
            models.Index(
                fields=["category", "start_on", "end_on"],
                name="vacation_category_window_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.category} - {self.label}"
