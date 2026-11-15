"""Current leave policy, holiday and workflow timing configuration."""

from django.db import models

from core.db.mixins import TimeStampedModel


class PolicyConfiguration(TimeStampedModel):
    """Current parameters; policy configuration has no publish lifecycle."""

    category = models.ForeignKey(
        "leave_elm.LeaveCategory",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="policy_configurations",
    )
    key = models.CharField(max_length=80)
    value = models.JSONField(default=dict, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_policy_configuration"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "key"],
                condition=models.Q(category__isnull=False),
                name="leave_policy_category_key_uniq",
            ),
            models.UniqueConstraint(
                fields=["key"],
                condition=models.Q(category__isnull=True),
                name="leave_policy_global_key_uniq",
            ),
        ]


class HolidayCalendar(TimeStampedModel):
    name = models.CharField(max_length=120)
    year = models.PositiveSmallIntegerField()
    holidays = models.JSONField(default=list, blank=True)
    restricted_holidays = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        constraints = [
            models.UniqueConstraint(fields=["year", "name"], name="leave_holiday_year_name_uniq"),
            models.UniqueConstraint(
                fields=["year"],
                condition=models.Q(is_published=True),
                name="leave_one_published_calendar_per_year",
            ),
        ]


class OfflineSanctionedLeaveRecord(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.ForeignKey("leave_elm.LeaveCategory", on_delete=models.PROTECT)
    starts_on = models.DateField()
    ends_on = models.DateField()
    leave_days = models.DecimalField(max_digits=7, decimal_places=2)
    purpose = models.TextField(blank=True)
    sanction_reference = models.CharField(max_length=200)
    evidence_reference = models.CharField(max_length=500, blank=True)
    recorded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "leave_offline_sanctioned_record"


class SLAConfiguration(TimeStampedModel):
    workflow_name = models.CharField(max_length=80, unique=True)
    reminder_hours = models.PositiveIntegerField()
    escalation_hours = models.PositiveIntegerField()
    escalation_role = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_sla_configuration"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(escalation_hours__gte=models.F("reminder_hours")),
                name="leave_sla_escalation_after_reminder",
            )
        ]


class YearEndProcessingRun(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    completed_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_year_end_processing_run"

    def __str__(self) -> str:
        return f"leave year-end {self.year}"
