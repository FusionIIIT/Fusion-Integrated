"""Effective-dated configuration (BR-EL-030, BR-EL-031). Published rows are never edited."""
from django.db import models

from core.db.mixins import TimeStampedModel

DRAFT = "draft"
PUBLISHED = "published"
STATUS = [(DRAFT, "Draft"), (PUBLISHED, "Published")]


class PolicyVersion(TimeStampedModel):
    name = models.CharField(max_length=120)
    params = models.JSONField(default=dict)
    hierarchy = models.JSONField(default=dict)
    effective_from = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS, default=DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_policy_version"
        indexes = [models.Index(fields=["status", "effective_from"],
                                name="elm_policy_eff_idx")]

    def __str__(self) -> str:
        return f"policy#{self.pk} {self.status} {self.effective_from}"


class CalendarVersion(TimeStampedModel):
    name = models.CharField(max_length=120)
    effective_from = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS, default=DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_calendar_version"
        indexes = [models.Index(fields=["status", "effective_from"],
                                name="elm_calendar_eff_idx")]

    def __str__(self) -> str:
        return f"calendar#{self.pk} {self.status} {self.effective_from}"


class CalendarEntry(models.Model):
    CLOSED_HOLIDAY = "closed_holiday"
    RESTRICTED_HOLIDAY = "restricted_holiday"
    VACATION = "vacation"
    KINDS = [(CLOSED_HOLIDAY, "Closed holiday"),
             (RESTRICTED_HOLIDAY, "Restricted holiday"),
             (VACATION, "Vacation period")]

    version = models.ForeignKey(CalendarVersion, on_delete=models.CASCADE,
                                related_name="entries")
    kind = models.CharField(max_length=20, choices=KINDS)
    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = "elm_calendar_entry"
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="elm_calendar_entry_order"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.start_date}..{self.end_date}"
