"""ELM tables. Institute people are plain `user_id` integers, never FKs."""
from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.elm.domain.categories import LeaveCategory
from modules.elm.domain.state_machine import LeaveStatus, SubstituteStatus

CATEGORY_CHOICES = [(c.value, c.label) for c in LeaveCategory]
STATUS_CHOICES = [(s.value, s.value) for s in LeaveStatus]
SUBSTITUTE_CHOICES = [(s.value, s.value) for s in SubstituteStatus]

_CATEGORY_VALUES = [c.value for c in LeaveCategory]
_STATUS_VALUES = [s.value for s in LeaveStatus]

HALF_CHOICES = [("full", "Full day"), ("first", "First half"),
                ("second", "Second half")]


class HolidayCalendar(models.Model):
    """A published holiday / restricted-holiday date.

    Date and RH validation uses the currently effective published calendar; a
    replacement only governs once it is published (PS §12).
    """

    HOLIDAY = "holiday"
    RESTRICTED = "restricted"
    KIND_CHOICES = [(HOLIDAY, "Closed holiday"), (RESTRICTED, "Restricted holiday")]

    date = models.DateField(db_index=True)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES,
                            default=HOLIDAY)
    label = models.CharField(max_length=120, blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_holiday"
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["date", "kind"],
                                    name="elm_holiday_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.kind}"


class LeaveApplication(TimeStampedModel):
    """One employee's leave request, from submission to a final decision."""

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=8, choices=HALF_CHOICES, default="full")
    purpose = models.TextField(max_length=2000, blank=True)

    # Station Leave details are coupled to the same application (PS §2).
    station_leave = models.JSONField(null=True, blank=True)

    # Responsibility coverage. `none` means no substitute was required.
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=12,
                                         choices=SUBSTITUTE_CHOICES,
                                         default=SubstituteStatus.NONE.value)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES,
                              default=LeaveStatus.SUBMITTED.value)
    chargeable_days = models.DecimalField(max_digits=6, decimal_places=1,
                                          default=Decimal("0"))

    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(max_length=2000, blank=True)

    class Meta:
        db_table = "elm_application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "-created_at"],
                         name="elm_app_user_recent_idx"),
            models.Index(fields=["status", "start_date"],
                         name="elm_app_status_date_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(category__in=_CATEGORY_VALUES),
                                   name="elm_app_category_valid"),
            models.CheckConstraint(condition=Q(status__in=_STATUS_VALUES),
                                   name="elm_app_status_valid"),
            models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")),
                                   name="elm_app_dates_ordered"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.category} {self.start_date}"


class LeaveBalance(models.Model):
    """An employee's current balance for one category in one year."""

    user_id = models.IntegerField(db_index=True)
    year = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    entitled = models.DecimalField(max_digits=7, decimal_places=1, default=Decimal("0"))
    used = models.DecimalField(max_digits=7, decimal_places=1, default=Decimal("0"))

    class Meta:
        db_table = "elm_balance"
        ordering = ["year", "category"]
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year", "category"],
                                    name="elm_balance_unique"),
            models.CheckConstraint(condition=Q(category__in=_CATEGORY_VALUES),
                                   name="elm_balance_category_valid"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.year} {self.category} {self.available}"

    @property
    def available(self) -> Decimal:
        return self.entitled - self.used


class LeaveTransaction(models.Model):
    """Append-only ledger of balance movements (approved, cancelled, opened)."""

    OPENING = "opening"
    APPROVED = "approved"
    CANCELLED = "cancelled"
    CONVERSION = "conversion"
    REASON_CHOICES = [
        (OPENING, "Opening entitlement"),
        (APPROVED, "Approved leave"),
        (CANCELLED, "Cancelled leave restored"),
        (CONVERSION, "Year-end conversion"),
    ]

    user_id = models.IntegerField(db_index=True)
    year = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=7, decimal_places=1)
    reason = models.CharField(max_length=12, choices=REASON_CHOICES)
    application_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "elm_transaction"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "year", "category", "-created_at"],
                         name="elm_txn_user_year_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.category} {self.amount:+}"
