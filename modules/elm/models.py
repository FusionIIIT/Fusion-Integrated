from django.db import models

from core.db.mixins import TimeStampedModel
from modules.elm.domain.rules import CATEGORIES


class Policy(TimeStampedModel):
    non_working_weekdays = models.JSONField(default=list)
    require_col_evidence = models.BooleanField(default=False)
    reminder_hours = models.PositiveIntegerField(default=24)
    escalation_hours = models.PositiveIntegerField(default=48)


class EmployeeConfiguration(TimeStampedModel):
    user_id = models.PositiveIntegerField(unique=True)
    unit = models.CharField(max_length=120)
    designation = models.CharField(max_length=120)
    coverage_required = models.BooleanField(default=False)
    eligible_categories = models.JSONField(default=list)
    routes = models.JSONField(default=dict)


class HolidayCalendar(TimeStampedModel):
    year = models.PositiveIntegerField()
    holidays = models.JSONField(default=list)
    restricted_holidays = models.JSONField(default=list)
    published = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["year"], condition=models.Q(published=True),
                                                name="elm_one_published_calendar")]


class Account(TimeStampedModel):
    user_id = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    employee_kind = models.CharField(max_length=12)
    cl = models.DecimalField(max_digits=9, decimal_places=2)
    rh = models.DecimalField(max_digits=9, decimal_places=2)
    scl = models.DecimalField(max_digits=9, decimal_places=2)
    el = models.DecimalField(max_digits=9, decimal_places=2)
    col = models.DecimalField(max_digits=9, decimal_places=2)
    vl = models.DecimalField(max_digits=9, decimal_places=2)
    year_end_processed = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user_id", "year"], name="elm_account_user_year")]
        constraints += [models.CheckConstraint(condition=models.Q(**{f"{c.lower()}__gte": 0}),
                                               name=f"elm_balance_{c.lower()}_nonnegative")
                        for c in CATEGORIES]


class Application(TimeStampedModel):
    user_id = models.PositiveIntegerField()
    kind = models.CharField(max_length=16, default="leave")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                               related_name="changes")
    category = models.CharField(max_length=3, choices=[(c, c) for c in CATEGORIES])
    start_date = models.DateField()
    end_date = models.DateField()
    effective_end_date = models.DateField()
    half = models.CharField(max_length=6, default="full")
    reason = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_details = models.TextField(blank=True)
    medical_reference = models.CharField(max_length=300, blank=True)
    substitute_id = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=24, default="unit_head")
    days_by_year = models.JSONField(default=dict)
    route = models.JSONField(default=list)
    route_index = models.PositiveIntegerField(default=0)
    revision = models.PositiveIntegerField(default=1)
    final_authority_id = models.PositiveIntegerField(null=True, blank=True)
    final_authority_role = models.CharField(max_length=120, blank=True)
    offline_reference = models.CharField(max_length=300, blank=True)
    resumption_reviewed = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["user_id", "-id"], name="elm_application_owner_idx"),
                   models.Index(fields=["user_id", "status", "start_date", "effective_end_date"],
                                name="elm_application_overlap_idx")]
        constraints = [models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                               name="elm_application_valid_dates")]


class WorkflowTask(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name="tasks")
    user_id = models.PositiveIntegerField()
    role = models.CharField(max_length=120)
    stage = models.CharField(max_length=16)
    pending = models.BooleanField(default=True)
    reminded_at = models.DateTimeField(null=True)
    escalated_at = models.DateTimeField(null=True)
    escalation_user_id = models.PositiveIntegerField(null=True)
    escalation_role = models.CharField(max_length=120, blank=True)
    reassign_on_escalation = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["user_id", "role", "pending", "-id"],
                                name="elm_task_assignee_idx")]
        constraints = [models.UniqueConstraint(fields=["application"], condition=models.Q(pending=True),
                                                name="elm_one_pending_task")]


class LedgerEntry(TimeStampedModel):
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="entries")
    application = models.ForeignKey(Application, null=True, on_delete=models.PROTECT)
    category = models.CharField(max_length=3)
    delta = models.DecimalField(max_digits=9, decimal_places=2)
    operation = models.CharField(max_length=32)
    event_key = models.CharField(max_length=150, unique=True)


class AuditEntry(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name="history")
    actor_id = models.PositiveIntegerField(null=True)
    action = models.CharField(max_length=40)
    reason = models.TextField(blank=True)
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)


class Notification(TimeStampedModel):
    user_id = models.PositiveIntegerField()
    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    message = models.CharField(max_length=300)
    read = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["user_id", "-id"], name="elm_notification_user_idx")]


class AttendanceOutbox(TimeStampedModel):
    application = models.OneToOneField(Application, on_delete=models.PROTECT)
    payload = models.JSONField()
    delivered_at = models.DateTimeField(null=True)
