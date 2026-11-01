"""Employee Leave Management domain tables.

Institute identities are integer IDs from the shared IAM; this module never
creates a second user table. Policy parameters are current configuration (the
specification explicitly excludes policy draft/publish versions); calendars
retain published history so date validation can use the effective calendar.
"""
from django.db import models
from django.db.models import Q
from core.db.mixins import TimeStampedModel


class LeaveAccountLock(TimeStampedModel):
    """Per-employee serialization row for concurrent overlap/balance writes."""
    user_id = models.IntegerField(unique=True)

    class Meta:
        db_table = "elm_leave_account_lock"


class LeavePolicy(TimeStampedModel):
    """Current leave parameters and routing hierarchy; edited in place by admins."""
    key = models.CharField(max_length=32, unique=True, default="current")
    params = models.JSONField(default=dict, blank=True)
    hierarchy = models.JSONField(default=dict, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_policy"


class CalendarVersion(TimeStampedModel):
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=16, choices=[("draft", "Draft"), ("published", "Published")], default="draft")
    effective_from = models.DateField()
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_calendar_version"
        ordering = ["-effective_from", "-id"]
        indexes = [models.Index(fields=["status", "effective_from"], name="elm_calendar_effective_idx")]


class CalendarEntry(TimeStampedModel):
    KIND = [("closed_holiday", "Closed holiday"), ("restricted_holiday", "Restricted holiday"), ("vacation", "Vacation")]
    calendar = models.ForeignKey(CalendarVersion, on_delete=models.CASCADE, related_name="entries")
    kind = models.CharField(max_length=24, choices=KIND)
    start_date = models.DateField()
    end_date = models.DateField()
    label = models.CharField(max_length=160, blank=True)

    class Meta:
        db_table = "elm_calendar_entry"
        constraints = [models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")), name="elm_calendar_entry_dates_valid")]
        indexes = [models.Index(fields=["calendar", "kind", "start_date"], name="elm_calendar_entry_lookup_idx")]


class LeaveRequest(TimeStampedModel):
    CATEGORY = [(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    STATUS = [(x, x.replace("_", " ").title()) for x in (
        "awaiting_substitute", "substitute_declined", "awaiting_unit_head",
        "awaiting_establishment", "awaiting_sanction", "awaiting_director",
        "approved", "rejected", "withdrawn", "cancellation_pending",
        "cancelled", "resumption_pending", "resumption_reviewed_no_adjustment",
        "resumption_reviewed_early", "resumption_reviewed_late")]
    KIND = [("leave", "Leave"), ("extension", "Extension")]

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=CATEGORY)
    kind = models.CharField(max_length=12, choices=KIND, default="leave")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="extensions")
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=8, blank=True, choices=[("first", "First half"), ("second", "Second half")])
    days = models.DecimalField(max_digits=7, decimal_places=2)
    purpose = models.TextField(blank=True)
    station_leave = models.BooleanField(default=False)
    station_leave_from = models.DateField(null=True, blank=True)
    station_leave_to = models.DateField(null=True, blank=True)
    station_leave_address = models.CharField(max_length=300, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=16, choices=[("not_required", "Not required"), ("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")], default="not_required")
    status = models.CharField(max_length=40, choices=STATUS, default="awaiting_unit_head", db_index=True)
    route = models.JSONField(default=list, blank=True)
    stage = models.PositiveSmallIntegerField(default=0)
    current_role = models.CharField(max_length=80, blank=True)
    recommendation = models.CharField(max_length=16, blank=True, choices=[("recommended", "Recommended"), ("not_recommended", "Not recommended")])
    decision_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    cancellation_stage = models.PositiveSmallIntegerField(default=0)
    cancellation_reason = models.TextField(blank=True)
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    actual_return_date = models.DateField(null=True, blank=True)
    resumption_kind = models.CharField(max_length=12, blank=True, choices=[("normal", "Normal"), ("early", "Early"), ("late", "Late")])
    resumption_note = models.TextField(blank=True)
    evidence = models.JSONField(default=list, blank=True)
    policy_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")), name="elm_request_dates_valid"),
            models.CheckConstraint(condition=Q(days__gt=0), name="elm_request_days_positive"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_request_user_status_idx"),
            models.Index(fields=["status", "current_role"], name="elm_request_queue_idx"),
            models.Index(fields=["start_date", "end_date"], name="elm_request_dates_idx"),
        ]


class LeaveTransition(TimeStampedModel):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="transitions")
    from_status = models.CharField(max_length=40, blank=True)
    to_status = models.CharField(max_length=40)
    event = models.CharField(max_length=48)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=80, blank=True)
    note = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "elm_leave_transition"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["request", "created_at"], name="elm_transition_req_time_idx")]


class LedgerEntry(TimeStampedModel):
    ENTRY_TYPE = [(x, x) for x in ("annual_credit", "debit", "reversal", "restore", "year_end_lapse", "vl_conversion", "adjustment")]
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeaveRequest.CATEGORY)
    delta = models.DecimalField(max_digits=9, decimal_places=2)
    entry_type = models.CharField(max_length=24, choices=ENTRY_TYPE)
    year = models.PositiveSmallIntegerField(db_index=True)
    request = models.ForeignKey(LeaveRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="ledger_entries")
    reference = models.CharField(max_length=120, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "elm_ledger_entry"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "category", "year"], condition=Q(entry_type="annual_credit"), name="elm_ledger_credit_once"),
            models.UniqueConstraint(fields=["request", "entry_type"], condition=Q(entry_type__in=["debit", "reversal", "restore"]), name="elm_ledger_req_event_once"),
            models.UniqueConstraint(fields=["user_id", "category", "year", "entry_type", "reference"], condition=Q(reference__gt=""), name="elm_ledger_ref_once"),
        ]
        indexes = [models.Index(fields=["user_id", "category", "year"], name="elm_ledger_balance_idx")]


class OfflineLeaveRecord(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeaveRequest.CATEGORY)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=7, decimal_places=2)
    sanction_reference = models.CharField(max_length=120, blank=True)
    evidence = models.JSONField(default=list, blank=True)
    recorded_by_user_id = models.IntegerField()
    note = models.TextField(blank=True)
    synced_request = models.OneToOneField(LeaveRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="offline_record")

    class Meta:
        db_table = "elm_offline_leave_record"
        constraints = [models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")), name="elm_offline_dates_valid")]


class YearEndRun(TimeStampedModel):
    year = models.PositiveSmallIntegerField(unique=True)
    status = models.CharField(max_length=16, choices=[("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], default="running")
    report = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_year_end_run"


class Notification(TimeStampedModel):
    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_role = models.CharField(max_length=80, blank=True, db_index=True)
    topic = models.CharField(max_length=48, db_index=True)
    title = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_notification"
        indexes = [models.Index(fields=["recipient_user_id", "created_at"], name="elm_notification_user_idx")]


class SlaAction(TimeStampedModel):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="sla_actions")
    stage = models.PositiveIntegerField()
    action = models.CharField(max_length=16, choices=[("reminder", "Reminder"), ("escalation", "Escalation")])
    fired_at = models.DateTimeField(auto_now_add=True)
    target_role = models.CharField(max_length=80, blank=True)

    class Meta:
        db_table = "elm_sla_action"
        constraints = [models.UniqueConstraint(fields=["request", "stage", "action"], name="elm_sla_action_once_unique")]
