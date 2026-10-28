"""ELM tables.

Institute people are plain `user_id` integers — there is no user table in this
database and a cross-module foreign key is forbidden (ADR-0013). Only rows ELM
itself owns are related by FK.
"""
from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain.categories import CATEGORY_RULES, LeaveCategory

CATEGORY_CHOICES = [(c.value, CATEGORY_RULES[c]["label"]) for c in LeaveCategory]

HALF_DAY_CHOICES = [("none", "Full day"), ("first_half", "First half"),
                    ("second_half", "Second half")]

STATUS_CHOICES = [
    ("pending", "Pending"),
    ("recommended", "Recommended"),
    ("not_recommended", "Not recommended"),
    ("sanctioned", "Sanctioned"),
    ("rejected", "Rejected"),
    ("withdrawn", "Withdrawn"),
    ("cancellation_pending", "Cancellation requested"),
    ("cancelled", "Cancelled"),
]


class LeavePolicy(TimeStampedModel):
    """Editable per-category policy parameters. Seeded from CATEGORY_RULES; no
    draft/publish lifecycle — validation uses the current values (§5, §12)."""

    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES,
                                unique=True)
    annual_entitlement = models.DecimalField(max_digits=5, decimal_places=2)
    carries_forward = models.BooleanField(default=False)
    continuous_counting = models.BooleanField(default=False)
    half_day_allowed = models.BooleanField(default=False)
    final_authority = models.CharField(max_length=24, default="unit_head")

    class Meta:
        db_table = "leave_policy"
        verbose_name_plural = "leave policies"
        constraints = [
            models.CheckConstraint(
                condition=Q(annual_entitlement__gte=0),
                name="leave_policy_entitlement_nonneg"),
        ]

    def __str__(self) -> str:
        return self.category


class Holiday(TimeStampedModel):
    """The published holiday / RH calendar. Date and RH validation read the
    currently effective published rows (§5, §12)."""

    KINDS = [("closed", "Closed holiday"), ("restricted", "Restricted holiday")]

    on_date = models.DateField(unique=True)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=12, choices=KINDS, default="closed")
    published = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_holiday"
        ordering = ["on_date"]

    def __str__(self) -> str:
        return f"{self.on_date} {self.name}"


class VacationPeriod(TimeStampedModel):
    """Vacation windows for VL, supplied by the external Academic Calendar
    (EXT-01). Mirrored here so VL applicability is checkable locally."""

    label = models.CharField(max_length=120)
    starts_on = models.DateField()
    ends_on = models.DateField()

    class Meta:
        db_table = "leave_vacation_period"
        ordering = ["starts_on"]
        constraints = [
            models.CheckConstraint(condition=Q(ends_on__gte=models.F("starts_on")),
                                   name="leave_vacation_period_valid"),
        ]

    def __str__(self) -> str:
        return self.label


class LeaveAccount(UserScopedModel, TimeStampedModel):
    """One employee's balance for one category in one year. `remaining` is
    derived, never stored — a stored balance is the classic drift bug."""

    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    year = models.PositiveSmallIntegerField()
    entitlement = models.DecimalField(max_digits=6, decimal_places=2,
                                      default=Decimal("0"))
    carried_forward = models.DecimalField(max_digits=6, decimal_places=2,
                                          default=Decimal("0"))
    availed = models.DecimalField(max_digits=6, decimal_places=2,
                                  default=Decimal("0"))

    class Meta:
        db_table = "leave_account"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "category", "year"],
                                    name="leave_account_unique"),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="leave_account_user_year_idx"),
        ]

    @property
    def remaining(self) -> Decimal:
        return (self.entitlement + self.carried_forward - self.availed)


class LeaveApplication(TimeStampedModel):
    """A leave request. Station Leave details are captured on the same row when
    the employee will be outside Jabalpur (§2) — not a separate request."""

    applicant_user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    starts_on = models.DateField()
    ends_on = models.DateField()
    half_day = models.CharField(max_length=12, choices=HALF_DAY_CHOICES,
                                default="none")
    purpose = models.TextField(max_length=2000, blank=True)
    leave_days = models.DecimalField(max_digits=6, decimal_places=2)

    status = models.CharField(max_length=24, choices=STATUS_CHOICES,
                              default="pending")
    unit_head_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    sanction_authority_user_id = models.IntegerField(null=True, blank=True)

    station_leave = models.BooleanField(default=False)
    station_leave_place = models.CharField(max_length=160, blank=True)
    station_leave_reason = models.CharField(max_length=300, blank=True)

    resumption_on = models.DateField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_application"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(ends_on__gte=models.F("starts_on")),
                                   name="leave_application_period_valid"),
            models.CheckConstraint(
                condition=Q(leave_days__gt=0),
                name="leave_application_days_positive"),
            models.CheckConstraint(
                condition=~Q(station_leave=True)
                | ~Q(station_leave_place=""),
                name="leave_application_station_has_place"),
        ]
        indexes = [
            models.Index(fields=["applicant_user_id", "-created_at"],
                         name="leave_applicant_recent_idx"),
            models.Index(fields=["status", "starts_on"],
                         name="leave_status_start_idx"),
        ]

    def __str__(self) -> str:
        return (f"[{self.category}] {self.applicant_user_id} "
                f"{self.starts_on}..{self.ends_on} ({self.status})")


class LeaveTransition(models.Model):
    """Audit of every status change, so a decision is defensible after the fact."""

    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="transitions")
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=24, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_transition"
        ordering = ["at"]

    def __str__(self) -> str:
        return f"{self.application} -> {self.to_status}"


class SubstituteNomination(TimeStampedModel):
    """When responsibility coverage is required the applicant nominates one
    eligible substitute, who must accept before approval routing continues (§6)."""

    STATUS = [("nominated", "Nominated"), ("accepted", "Accepted"),
              ("declined", "Declined")]

    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="substitutes")
    substitute_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=STATUS, default="nominated")
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_substitute_nomination"
        constraints = [
            models.UniqueConstraint(fields=["application", "substitute_user_id"],
                                    name="leave_substitute_unique"),
        ]


class LeaveTask(TimeStampedModel):
    """An actionable workflow task with SLA thresholds. Reminders and
    escalations fire only while the task is still pending (§14, EL-UC-021)."""

    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="tasks")
    assigned_user_id = models.IntegerField(db_index=True)
    due_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_task"
        indexes = [
            models.Index(fields=["is_open", "due_at"], name="leave_task_open_due_idx"),
        ]


class YearEndRun(TimeStampedModel):
    """One row per year-end processing event (§13, EL-UC-020): lapses CL/RH/SCL,
    converts unused faculty VL to EL, carries EL/COL forward, and reports
    exceptions rather than committing an uncertain adjustment."""

    year = models.PositiveSmallIntegerField(unique=True)
    processed_accounts = models.PositiveIntegerField(default=0)
    exceptions = models.JSONField(default=list, blank=True)
    ran_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_year_end_run"
        ordering = ["-year"]
