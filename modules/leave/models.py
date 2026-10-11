"""Leave domain models.

`user_id` references are plain integers — no FK across module boundaries.
Leave consumes `hr.contracts.get_employments(user_ids)` for employment checks;
it never reads `hr_*` tables directly.
"""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


# ---------------------------------------------------------------------------
# Leave types (CL, EL, ML, etc.)
# ---------------------------------------------------------------------------

class LeaveType(TimeStampedModel):
    """One category of leave the institute offers.

    Annual quota and carry-forward rules are kept here; the balance tables
    track the per-person running total.
    """

    code        = models.CharField(max_length=20, unique=True)   # e.g. "CL", "EL"
    name        = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    # Annual entitlement, applicable to *all* kinds by default.
    annual_quota     = models.PositiveSmallIntegerField(default=0)
    # Max that may roll over to the next year (0 = no carry-forward).
    max_carry_forward = models.PositiveSmallIntegerField(default=0)
    # Whether half-day leave is permitted for this type.
    allow_half_day   = models.BooleanField(default=False)
    # Requires medical document if duration ≥ this many days (null = never).
    requires_doc_after_days = models.PositiveSmallIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_type"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# Leave balance (per person, per leave type, per year)
# ---------------------------------------------------------------------------

class LeaveBalance(TimeStampedModel):
    """Running quota for one person in one calendar year for one leave type.

    Written by HR (credit/debit) and by the approval service (debit on approve).
    """

    user_id    = models.IntegerField(db_index=True)   # IAM erp_user_id — NO FK
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT,
                                   related_name="balances")
    year       = models.PositiveSmallIntegerField()    # calendar year, e.g. 2026

    credited = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    used     = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "leave_type", "year"],
                                    name="balance_unique_per_user_type_year"),
            models.CheckConstraint(
                condition=Q(used__lte=models.F("credited")),
                name="balance_used_le_credited",
            ),
            models.CheckConstraint(
                condition=Q(credited__gte=0) & Q(used__gte=0),
                name="balance_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="balance_user_year_idx"),
        ]

    @property
    def remaining(self):
        return self.credited - self.used

    def __str__(self) -> str:
        return f"balance u{self.user_id} {self.leave_type_id} {self.year}"


# ---------------------------------------------------------------------------
# Leave requests
# ---------------------------------------------------------------------------

class LeaveRequest(TimeStampedModel):
    """One leave application by an employee.

    Status flows through the state machine in `domain/state_machine.py`.
    An append-only `LeaveRequestTransition` row is written on every change.
    """

    STATUS = [
        ("pending",   "Pending approval"),
        ("approved",  "Approved"),
        ("rejected",  "Rejected"),
        ("cancelled", "Cancelled"),
        ("revoked",   "Revoked"),
    ]

    user_id    = models.IntegerField(db_index=True)   # applicant — NO FK
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT,
                                   related_name="requests")

    start_date  = models.DateField()
    end_date    = models.DateField()
    # Half-day: which half the *first* day is being taken (null = full day).
    HALF = [("morning", "Morning"), ("afternoon", "Afternoon")]
    half_day    = models.CharField(max_length=12, choices=HALF,
                                   blank=True, null=True)

    # Computed at create time; stored so an approval does not need to re-count.
    days_requested = models.DecimalField(max_digits=4, decimal_places=1)

    reason      = models.TextField(blank=True)
    status      = models.CharField(max_length=12, choices=STATUS, default="pending")
    applied_at  = models.DateTimeField(null=True, blank=True)

    # The approver's identity (no FK — cross-boundary).
    approved_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at          = models.DateTimeField(null=True, blank=True)
    decision_note       = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_request"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="leave_request_dates_valid",
            ),
            models.CheckConstraint(
                condition=Q(days_requested__gt=0),
                name="leave_request_positive_days",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["pending", "approved", "rejected",
                                        "cancelled", "revoked"]),
                name="leave_request_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_req_user_idx"),
            models.Index(fields=["leave_type", "status"], name="leave_req_type_idx"),
            models.Index(fields=["status", "start_date"], name="leave_req_queue_idx"),
        ]

    def __str__(self) -> str:
        return f"leave#{self.pk} u{self.user_id} {self.status}"


class LeaveRequestTransition(models.Model):
    """Append-only audit of every status change."""

    request     = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                    related_name="transitions")
    from_status = models.CharField(max_length=12)
    to_status   = models.CharField(max_length=12)
    actor_user_id = models.IntegerField(null=True, blank=True)
    reason      = models.CharField(max_length=300, blank=True)
    at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_request_transition"
        indexes = [
            models.Index(fields=["request", "at"], name="leave_trans_req_idx"),
        ]

    def __str__(self) -> str:
        return f"leave#{self.request_id} {self.from_status}→{self.to_status}"
