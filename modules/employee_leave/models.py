from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeavePolicy(TimeStampedModel):
    TYPES = [(x, x) for x in ("CL", "RH", "SCL", "EL", "VL", "COL")]
    YEAR_END_TREATMENTS = [
        ("lapse", "Lapse unused balance"),
        ("carry_forward", "Carry forward"),
        ("convert_to_el", "Convert to Earned Leave"),
    ]
    leave_type = models.CharField(max_length=3, choices=TYPES)
    leave_year = models.PositiveSmallIntegerField()
    enabled = models.BooleanField(default=True)
    annual_entitlement = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))
    carry_forward_limit = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))
    year_end_treatment = models.CharField(
        max_length=16, choices=YEAR_END_TREATMENTS, default="lapse"
    )
    conversion_ratio = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("1"))
    max_continuous_days = models.PositiveSmallIntegerField(null=True, blank=True)
    requires_substitute = models.BooleanField(default=False)
    requires_higher_sanction = models.BooleanField(default=False)
    faculty_only = models.BooleanField(default=False)
    hierarchy = models.JSONField(default=dict, blank=True)
    unit_head_sla_hours = models.PositiveSmallIntegerField(default=72)
    final_sanction_sla_hours = models.PositiveSmallIntegerField(default=120)
    escalation_role = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "elm_leave_policy"
        constraints = [
            models.UniqueConstraint(
                fields=("leave_type", "leave_year"), name="elm_policy_type_year_uniq"
            )
        ]
        ordering = ("leave_year", "leave_type")


class LeaveBalance(TimeStampedModel):
    user_id = models.PositiveBigIntegerField(db_index=True)
    policy = models.ForeignKey(LeavePolicy, on_delete=models.PROTECT, related_name="balances")
    opening_balance = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    credited = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    used = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=("user_id", "policy"), name="elm_balance_user_policy_uniq"
            )
        ]

    @property
    def available(self):
        return self.opening_balance + self.credited - self.used


class LeaveRequest(TimeStampedModel):
    TYPES = LeavePolicy.TYPES
    KINDS = [
        (x, x.replace("_", " ").title()) for x in ("new", "cancellation", "extension", "offline")
    ]
    STATES = [
        (x, x.replace("_", " ").title())
        for x in (
            "substitute_pending",
            "substitute_declined",
            "unit_head_pending",
            "establishment_pending",
            "final_pending",
            "approved",
            "rejected",
            "withdrawn",
            "cancellation_unit_head_pending",
            "cancellation_establishment_pending",
            "cancellation_final_pending",
            "cancelled",
            "resumption_pending",
            "resumption_reviewed",
        )
    ]

    employee_id = models.PositiveBigIntegerField(db_index=True)
    department = models.CharField(max_length=80, blank=True, db_index=True)
    policy = models.ForeignKey(LeavePolicy, on_delete=models.PROTECT, related_name="requests")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="related_requests"
    )
    request_kind = models.CharField(max_length=16, choices=KINDS, default="new")
    leave_type = models.CharField(max_length=3, choices=TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    charged_days = models.DecimalField(max_digits=6, decimal_places=2)
    reason = models.TextField()
    station_leave_details = models.CharField(max_length=300, blank=True)
    substitute_id = models.PositiveBigIntegerField(null=True, blank=True)
    half_day = models.BooleanField(default=False)
    status = models.CharField(max_length=40, choices=STATES, db_index=True)
    assigned_role = models.CharField(max_length=64, blank=True)
    assigned_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    sla_reminded_at = models.DateTimeField(null=True, blank=True)
    sla_escalated_at = models.DateTimeField(null=True, blank=True)
    actual_resume_date = models.DateField(null=True, blank=True)
    actual_resume_details = models.CharField(max_length=500, blank=True)
    final_decision = models.CharField(max_length=12, blank=True)
    final_decision_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=("employee_id", "-created_at"), name="elm_request_employee_idx"),
            models.Index(fields=("status", "assigned_role"), name="elm_request_task_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")), name="elm_request_dates_ordered"
            )
        ]


class LeaveDecision(TimeStampedModel):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="decisions")
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=64)
    action = models.CharField(max_length=32)
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    comment = models.CharField(max_length=1000, blank=True)

    class Meta:
        db_table = "elm_leave_decision"
        ordering = ("created_at", "id")


class LeaveLedgerEntry(TimeStampedModel):
    balance = models.ForeignKey(LeaveBalance, on_delete=models.PROTECT, related_name="entries")
    request = models.ForeignKey(
        LeaveRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    entry_type = models.CharField(max_length=24)
    days = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.CharField(max_length=300)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_ledger"
        ordering = ("-created_at", "-id")


class LeaveHoliday(TimeStampedModel):
    leave_year = models.PositiveSmallIntegerField(db_index=True)
    day = models.DateField()
    name = models.CharField(max_length=120)
    restricted = models.BooleanField(default=False)
    published = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_leave_holiday"
        constraints = [
            models.UniqueConstraint(fields=("leave_year", "day"), name="elm_holiday_year_day_uniq")
        ]
        ordering = ("day",)


class LeaveYearEndRun(TimeStampedModel):
    from_year = models.PositiveSmallIntegerField()
    to_year = models.PositiveSmallIntegerField()
    actor_user_id = models.PositiveBigIntegerField()
    balances_processed = models.PositiveIntegerField(default=0)
    annual_credits = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    carried_forward = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    converted_to_el = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    lapsed = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    class Meta:
        db_table = "elm_leave_year_end_run"
        constraints = [
            models.UniqueConstraint(
                fields=("from_year", "to_year"), name="elm_year_end_run_years_uniq"
            )
        ]


class LeaveTaskNotice(TimeStampedModel):
    EVENTS = [
        ("assigned", "Task assigned"),
        ("reminder", "Task reminder"),
        ("escalated", "Task escalated"),
        ("decision", "Request status changed"),
    ]
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="task_notices")
    event = models.CharField(max_length=12, choices=EVENTS)
    dedupe_key = models.CharField(max_length=220, unique=True)
    recipient_user_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    assigned_role = models.CharField(max_length=64, blank=True, db_index=True)
    message = models.CharField(max_length=300)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_task_notice"
        ordering = ("-created_at", "-id")
