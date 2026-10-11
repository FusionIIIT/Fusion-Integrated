"""Effective-dated policy and holiday/RH calendars (BR-EL-030, BR-EL-031).

Published versions are never edited; a replacement is a new published row.
"""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeavePolicy(TimeStampedModel):
    version = models.PositiveIntegerField()
    label = models.CharField(max_length=80, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    is_effective = models.BooleanField(default=False)

    cl_annual = models.DecimalField(max_digits=6, decimal_places=2, default=8)
    rh_annual = models.DecimalField(max_digits=6, decimal_places=2, default=2)
    scl_annual = models.DecimalField(max_digits=6, decimal_places=2, default=15)
    el_staff_annual = models.DecimalField(max_digits=6, decimal_places=2, default=30)
    vl_faculty = models.DecimalField(max_digits=6, decimal_places=2, default=60)
    col_annual = models.DecimalField(max_digits=6, decimal_places=2, default=20)
    vl_to_el_numerator = models.PositiveSmallIntegerField(default=2)
    vl_to_el_denominator = models.PositiveSmallIntegerField(default=1)
    categories_requiring_substitute = models.JSONField(default=list, blank=True)
    establishment_step_enabled = models.BooleanField(default=True)
    col_requires_medical = models.BooleanField(default=True)
    sla_reminder_hours = models.PositiveIntegerField(default=48)
    sla_escalation_hours = models.PositiveIntegerField(default=96)

    class Meta:
        db_table = "leave_policy"
        constraints = [
            models.UniqueConstraint(fields=["version"], name="leave_policy_version_uniq"),
            models.UniqueConstraint(
                fields=["is_effective"],
                condition=Q(is_effective=True),
                name="leave_policy_one_effective",
            ),
        ]


class HolidayCalendar(TimeStampedModel):
    version = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    label = models.CharField(max_length=80, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    is_effective = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_holiday_calendar"
        constraints = [
            models.UniqueConstraint(fields=["version"], name="leave_calendar_version_uniq"),
            models.UniqueConstraint(
                fields=["is_effective"],
                condition=Q(is_effective=True),
                name="leave_calendar_one_effective",
            ),
        ]


class CalendarEntry(TimeStampedModel):
    KINDS = (("closed", "Closed holiday"), ("rh", "Restricted holiday"),
             ("vacation", "Vacation period"))

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="entries")
    kind = models.CharField(max_length=12, choices=KINDS)
    start_on = models.DateField()
    end_on = models.DateField()
    label = models.CharField(max_length=80, blank=True)

    class Meta:
        db_table = "leave_calendar_entry"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_on__gte=models.F("start_on")),
                name="leave_calendar_entry_order",
            ),
        ]
