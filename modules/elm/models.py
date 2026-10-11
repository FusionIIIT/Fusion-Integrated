"""ELM-owned tables. IAM identities are integer references, never cross-module FKs."""
from decimal import Decimal

from django.db import models
from django.db.models import Q
from core.db.mixins import TimeStampedModel
from modules.elm.domain.rules import SUPPORTED_CATEGORIES


class LeavePolicy(TimeStampedModel):
    CATEGORY_CHOICES = [(c, c) for c in SUPPORTED_CATEGORIES]
    EMPLOYEE_SCOPES = [("all", "Faculty and staff"), ("faculty", "Faculty"), ("staff", "Staff")]

    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES, unique=True)
    annual_entitlement = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))
    employee_scope = models.CharField(max_length=12, choices=EMPLOYEE_SCOPES, default="all")
    carry_forward = models.BooleanField(default=False)
    continuous_counting = models.BooleanField(default=False)
    medical_evidence_required = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_policy"
        ordering = ["category"]

    def __str__(self):
        return f"{self.category}: {self.annual_entitlement} days/year"


class LeaveBalance(TimeStampedModel):
    """Per-person annual account. The ledger records every applied change."""
    user_id = models.IntegerField(db_index=True)
    employee_kind = models.CharField(max_length=12, choices=[("faculty", "Faculty"), ("staff", "Staff")])
    year = models.PositiveSmallIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeavePolicy.CATEGORY_CHOICES)
    entitlement = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    carried_in = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    converted_in = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    consumed = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    lapsed = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    converted_out = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [models.UniqueConstraint(fields=["user_id", "year", "category"],
                                                name="elm_balance_user_year_cat_uniq")]
        indexes = [models.Index(fields=["user_id", "year"], name="elm_balance_user_year_idx")]

    @property
    def available(self):
        return (self.entitlement + self.carried_in + self.converted_in
                - self.consumed - self.lapsed - self.converted_out)


class LeaveCalendar(TimeStampedModel):
    STATUS = [("draft", "Draft"), ("published", "Published")]
    name = models.CharField(max_length=160)
    year = models.PositiveSmallIntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=STATUS, default="draft")
    created_by_user_id = models.IntegerField()
    published_by_user_id = models.IntegerField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_calendar"
        ordering = ["-year", "-published_at"]
        constraints = [models.UniqueConstraint(fields=["year", "name"], name="elm_calendar_year_name_uniq")]


class LeaveCalendarDate(models.Model):
    calendar = models.ForeignKey(LeaveCalendar, on_delete=models.CASCADE, related_name="dates")
    day = models.DateField()
    name = models.CharField(max_length=160)
    is_restricted_holiday = models.BooleanField(default=False)
    is_closed_day = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_calendar_date"
        constraints = [models.UniqueConstraint(fields=["calendar", "day"], name="elm_cal_date_uniq")]
        ordering = ["day"]


class VacationPeriod(TimeStampedModel):
    """Local projection of vacation dates supplied by the external Academic Calendar."""
    name = models.CharField(max_length=160)
    start_date = models.DateField()
    end_date = models.DateField()
    external_reference = models.CharField(max_length=200, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_vacation_period"
        constraints = [models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")),
                                               name="elm_vacation_period_dates_valid")]


class LeaveHierarchy(TimeStampedModel):
    """Current routing configuration keyed by the directory department/unit name."""
    unit_key = models.CharField(max_length=120, unique=True)
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    establishment_user_id = models.IntegerField(null=True, blank=True)
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True)
    director_user_id = models.IntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_hierarchy"
        ordering = ["unit_key"]


class LeaveApplication(TimeStampedModel):
    CATEGORIES = LeavePolicy.CATEGORY_CHOICES
    REQUEST_TYPES = [("leave", "Leave"), ("cancellation", "Cancellation"),
                     ("extension", "Extension"), ("resumption", "Resumption"),
                     ("offline", "Offline sanctioned leave")]
    STATUSES = [(s, s.replace("_", " ").title()) for s in (
        "awaiting_substitute", "awaiting_unit_head", "awaiting_cancellation_unit_head",
        "awaiting_establishment", "awaiting_sanction", "awaiting_cancellation_sanction",
        "awaiting_resumption_review", "approved", "rejected", "withdrawn",
        "cancelled", "action_required")]
    HALVES = [("none", "Full day"), ("first", "First half"), ("second", "Second half")]
    SUBSTITUTE_RESPONSES = [("not_required", "Not required"), ("pending", "Pending"),
                            ("accepted", "Accepted"), ("declined", "Declined")]

    applicant_user_id = models.IntegerField(db_index=True)
    employee_kind = models.CharField(max_length=12, choices=[("faculty", "Faculty"), ("staff", "Staff")])
    department = models.CharField(max_length=120, blank=True, db_index=True)
    request_type = models.CharField(max_length=16, choices=REQUEST_TYPES, default="leave", db_index=True)
    parent_application = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                                           related_name="related_requests")
    category = models.CharField(max_length=3, choices=CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    cl_half = models.CharField(max_length=8, choices=HALVES, default="none")
    requested_days = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))
    requested_days_by_year = models.JSONField(default=dict, blank=True)
    purpose = models.CharField(max_length=1000)
    station_leave = models.BooleanField(default=False)
    station_leave_details = models.CharField(max_length=1000, blank=True)
    requires_substitute = models.BooleanField(default=False)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_response = models.CharField(max_length=16, choices=SUBSTITUTE_RESPONSES, default="not_required")
    director_case = models.BooleanField(default=False)
    status = models.CharField(max_length=36, choices=STATUSES, default="awaiting_unit_head", db_index=True)
    current_assignee_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    establishment_user_id = models.IntegerField(null=True, blank=True)
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True)
    unit_head_recommendation = models.CharField(max_length=24, blank=True)
    final_decision = models.CharField(max_length=12, blank=True)
    final_decision_note = models.CharField(max_length=1000, blank=True)
    final_decided_at = models.DateTimeField(null=True, blank=True)
    action_reason = models.CharField(max_length=1000, blank=True)
    actual_resumption_date = models.DateField(null=True, blank=True)
    evidence_reference = models.CharField(max_length=240, blank=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["applicant_user_id", "status"], name="elm_app_user_status_idx"),
                   models.Index(fields=["current_assignee_user_id", "status"], name="elm_app_assign_status_idx"),
                   models.Index(fields=["start_date", "end_date"], name="elm_app_dates_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")),
                                   name="elm_app_dates_valid"),
            models.UniqueConstraint(
                fields=["evidence_reference"],
                condition=Q(request_type="offline"),
                name="elm_offline_evidence_uniq",
            ),
        ]


class LeaveLedgerEntry(TimeStampedModel):
    TYPES = [(s, s.replace("_", " ").title()) for s in (
        "credit", "debit", "restore", "lapse", "convert_in", "convert_out", "carry_forward")]
    user_id = models.IntegerField(db_index=True)
    employee_kind = models.CharField(max_length=12, choices=[("faculty", "Faculty"), ("staff", "Staff")])
    year = models.PositiveSmallIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeavePolicy.CATEGORY_CHOICES)
    entry_type = models.CharField(max_length=16, choices=TYPES)
    units = models.DecimalField(max_digits=8, decimal_places=2)
    application = models.ForeignKey(LeaveApplication, null=True, blank=True,
                                   on_delete=models.PROTECT, related_name="ledger_entries")
    reference_key = models.CharField(max_length=200, unique=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "elm_leave_ledger"
        ordering = ["created_at"]


class LeaveNotice(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    application = models.ForeignKey(LeaveApplication, null=True, blank=True,
                                    on_delete=models.CASCADE, related_name="notices")
    kind = models.CharField(max_length=32)
    message = models.CharField(max_length=500)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_notice"
        ordering = ["-created_at"]


class LeaveSLAConfig(TimeStampedModel):
    reminder_after_hours = models.PositiveSmallIntegerField(default=24)
    escalation_after_hours = models.PositiveSmallIntegerField(default=48)
    escalation_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_sla_config"


class LeaveSLAEvent(TimeStampedModel):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="sla_events")
    event_type = models.CharField(max_length=16, choices=[("reminder", "Reminder"), ("escalation", "Escalation")])
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "elm_leave_sla_event"
        constraints = [models.UniqueConstraint(fields=["application", "event_type"], name="elm_sla_app_event_uniq")]


class LeaveYearEndRun(TimeStampedModel):
    year = models.PositiveSmallIntegerField(unique=True)
    run_by_user_id = models.IntegerField(null=True, blank=True)
    processed_accounts = models.PositiveIntegerField(default=0)
    exceptions = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "elm_leave_year_end_run"


class LeaveTransition(TimeStampedModel):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="transitions")
    actor_user_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=48)
    from_status = models.CharField(max_length=36)
    to_status = models.CharField(max_length=36)
    note = models.CharField(max_length=1000, blank=True)

    class Meta:
        db_table = "elm_leave_transition"
        ordering = ["created_at", "id"]
