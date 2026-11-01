from django.db import models

from core.db.mixins import TimeStampedModel


class HolidayCalendar(TimeStampedModel):
    """BR-EL-031: the published calendar for a year is the effective one."""

    DRAFT, PUBLISHED, SUPERSEDED = "draft", "published", "superseded"

    year = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=120)
    status = models.CharField(max_length=12, default=DRAFT, choices=[
        (DRAFT, "Draft"), (PUBLISHED, "Published"), (SUPERSEDED, "Superseded")])
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "leave_holiday_calendar"
        constraints = [models.UniqueConstraint(
            fields=["year"], condition=models.Q(status="published"),
            name="leave_one_published_calendar_per_year")]


class Holiday(models.Model):
    CLOSED, RESTRICTED = "closed", "restricted"

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="holidays")
    date = models.DateField()
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=10, choices=[(CLOSED, "Closed"),
                                                    (RESTRICTED, "Restricted")])

    class Meta:
        db_table = "leave_holiday"
        constraints = [models.UniqueConstraint(fields=["calendar", "date", "kind"],
                                               name="leave_holiday_unique")]

    def __str__(self) -> str:
        return f"{self.date} {self.name}"


class VacationPeriod(TimeStampedModel):
    """Local mirror of the Academic Calendar's vacations (EXT-01), used for VL."""

    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = "leave_vacation_period"
        constraints = [models.CheckConstraint(
            condition=models.Q(end_date__gte=models.F("start_date")),
            name="leave_vacation_period_ordered")]
