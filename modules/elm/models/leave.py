"""ELM domain tables.

Institute people are referenced by plain ``user_id`` integers, never foreign
keys -- there is no user table in this database (ADR-0013, same as placement).

Tables:
  LeaveRequest      -- one row per application / extension / cancellation.
  LeaveTransition   -- append-only audit trail of every status change.
  LeaveBalance      -- per-employee, per-category running balance.
  HolidayCalendar   -- effective published holiday / RH calendar (BR-EL-031).
"""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel

from modules.elm.domain.leave_policy import (
    VALID_CATEGORIES,
    DayHalf,
)


# -- LeaveRequest -------------------------------------------------------------

class LeaveRequest(TimeStampedModel, UserScopedModel):
    """A single leave application, extension, or cancellation request."""

    CATEGORY_CHOICES = [(c, c) for c in sorted(VALID_CATEGORIES)]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("awaiting_substitute", "Awaiting Substitute"),
        ("awaiting_unit_head", "Awaiting Unit Head"),
        ("awaiting_establishment", "Awaiting Establishment"),
        ("awaiting_sanction", "Awaiting Sanction"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("ongoing", "Ongoing"),
        ("cancel_requested", "Cancel Requested"),
        ("cancelled", "Cancelled"),
        ("extension_requested", "Extension Requested"),
        ("extension_approved", "Extension Approved"),
        ("resumption_submitted", "Resumption Submitted"),
        ("resumption_reviewed", "Resumption Reviewed"),
    ]

    HALF_CHOICES = [
        ("full", "Full Day"),
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ]

    REQUEST_TYPE_CHOICES = [
        ("new", "New Leave"),
        ("cancellation", "Cancellation"),
        ("extension", "Extension"),
        ("offline", "Offline Sanctioned"),
    ]

    # Core fields
    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES,
                              default="draft")
    request_type = models.CharField(max_length=16, choices=REQUEST_TYPE_CHOICES,
                                    default="new")

    # Date range (inclusive)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=12, choices=HALF_CHOICES,
                            default="full")

    # Computed at submission, frozen
    days_counted = models.DecimalField(max_digits=5, decimal_places=1,
                                       default=0)

    # Purpose / reason (BR-EL-004: SCL purpose judged by authority)
    purpose = models.TextField(blank=True)

    # Station leave (BR-EL-013)
    station_leave_required = models.BooleanField(default=False)
    station_leave_address = models.TextField(blank=True)

    # Substitute (BR-EL-014, BR-EL-015)
    substitute_id = models.IntegerField(null=True, blank=True)
    substitute_accepted = models.BooleanField(null=True, blank=True)

    # Unit Head recommendation (BR-EL-017)
    unit_head_recommendation = models.CharField(
        max_length=20, blank=True,
        choices=[("recommended", "Recommended"),
                 ("not_recommended", "Not Recommended")])

    # Links to parent request (for extensions / cancellations)
    parent_request = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.PROTECT, related_name="child_requests")

    # Offline sanction evidence (BR-EL-029)
    offline_sanction_reference = models.CharField(max_length=200, blank=True)

    # Resumption (BR-EL-027, BR-EL-028)
    actual_resumption_date = models.DateField(null=True, blank=True)

    # SLA tracking
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"],
                         name="elm_request_user_status_idx"),
            models.Index(fields=["category", "status"],
                         name="elm_request_cat_status_idx"),
            models.Index(fields=["start_date", "end_date"],
                         name="elm_request_dates_idx"),
            models.Index(fields=["substitute_id"],
                         name="elm_request_substitute_idx"),
        ]

    def __str__(self) -> str:
        return f"leave#{self.pk} u{self.user_id} {self.category} {self.status}"


# -- LeaveTransition (audit trail) --------------------------------------------

class LeaveTransition(models.Model):
    """Append-only audit of every status change on a LeaveRequest."""

    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="transitions")
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=40, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    recommendation = models.CharField(max_length=20, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_transition"
        indexes = [
            models.Index(fields=["leave_request", "at"],
                         name="elm_transition_req_idx"),
        ]

    def __str__(self) -> str:
        return (f"leave#{self.leave_request_id} "
                f"{self.from_status}->{self.to_status}")


# -- LeaveBalance -------------------------------------------------------------

class LeaveBalance(models.Model):
    """Per-employee, per-category running balance.

    Updated transactionally when leave is approved, cancelled, or at year-end.
    """

    user_id = models.IntegerField()
    category = models.CharField(max_length=4)
    year = models.IntegerField()
    credited = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    used = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    carried_forward = models.DecimalField(max_digits=6, decimal_places=1,
                                           default=0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "category", "year"],
                name="elm_balance_unique"),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"],
                         name="elm_balance_user_year_idx"),
        ]

    @property
    def available(self) -> float:
        return float(self.credited + self.carried_forward - self.used)

    def __str__(self) -> str:
        return (f"u{self.user_id} {self.category} {self.year}: "
                f"avail={self.available}")


# -- HolidayCalendar (BR-EL-031) ----------------------------------------------

class HolidayCalendar(models.Model):
    """Effective published holiday / Restricted Holiday calendar."""

    HOLIDAY_TYPE_CHOICES = [
        ("closed", "Closed Holiday"),
        ("restricted", "Restricted Holiday"),
    ]

    date = models.DateField()
    name = models.CharField(max_length=200)
    holiday_type = models.CharField(max_length=12, choices=HOLIDAY_TYPE_CHOICES)
    year = models.IntegerField()
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_holiday_calendar"
        constraints = [
            models.UniqueConstraint(
                fields=["date", "holiday_type"],
                name="elm_holiday_unique"),
        ]
        indexes = [
            models.Index(fields=["year", "is_published"],
                         name="elm_holiday_year_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.name} ({self.holiday_type})"
