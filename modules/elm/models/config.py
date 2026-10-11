"""Administrator-maintained configuration (EL-UC-014, 015, 018).

BR-EL-030: policy and hierarchy are current values with no publish lifecycle.
BR-EL-031: the holiday/RH calendar is the one exception, published per year.
"""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.elm.models.requests import CATEGORY_CHOICES


class CategoryPolicy(TimeStampedModel):
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES,
                                primary_key=True)
    annual_days = models.DecimalField(max_digits=5, decimal_places=1)
    updated_by_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_category_policy"
        constraints = [models.CheckConstraint(condition=Q(annual_days__gte=0),
                                              name="elm_policy_days_nonneg")]


class UnitHead(TimeStampedModel):
    """The Unit Head of a Department, Section or Office (ACT-03)."""

    unit = models.CharField(max_length=80, unique=True)
    head_user_id = models.IntegerField()

    class Meta:
        db_table = "elm_unit_head"


class SanctionRoute(TimeStampedModel):
    """BR-EL-018/019: higher-sanction path per category and employee kind."""

    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    applicant_kind = models.CharField(max_length=8)
    #: Null means no Establishment step is configured (EL-UC-004 A1).
    establishment_user_id = models.IntegerField(null=True, blank=True)
    authority_user_id = models.IntegerField()

    class Meta:
        db_table = "elm_sanction_route"
        constraints = [models.UniqueConstraint(
            fields=["category", "applicant_kind"], name="elm_route_unique")]


class SlaPolicy(TimeStampedModel):
    """BR-EL-038. One row; the latest is the current one."""

    reminder_hours = models.PositiveIntegerField(default=48)
    escalation_hours = models.PositiveIntegerField(default=96)
    escalation_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_sla_policy"
        constraints = [models.CheckConstraint(
            condition=Q(escalation_hours__gt=models.F("reminder_hours")),
            name="elm_sla_escalation_after_reminder")]


class HolidayCalendar(TimeStampedModel):
    DRAFT, PUBLISHED = "draft", "published"
    STATUS = [(DRAFT, "Draft"), (PUBLISHED, "Published")]

    year = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=STATUS, default=DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["-year", "-published_at", "-id"]
        constraints = [models.UniqueConstraint(
            fields=["year"], condition=Q(status="draft"),
            name="elm_calendar_one_draft_per_year")]


class Holiday(models.Model):
    CLOSED, RESTRICTED = "closed", "restricted"
    KIND = [(CLOSED, "Closed holiday"), (RESTRICTED, "Restricted Holiday")]

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="holidays")
    date = models.DateField()
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=10, choices=KIND)

    class Meta:
        db_table = "elm_holiday"
        ordering = ["date"]
        constraints = [models.UniqueConstraint(fields=["calendar", "date", "kind"],
                                               name="elm_holiday_unique")]

    def __str__(self) -> str:
        return f"{self.date} {self.name}"


class VacationPeriod(TimeStampedModel):
    """Mirror of the Academic Calendar's vacation periods (EXT-01) for VL."""

    label = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = "elm_vacation_period"
        ordering = ["start_date"]
        constraints = [models.CheckConstraint(
            condition=Q(end_date__gte=models.F("start_date")),
            name="elm_vacation_ordered")]
