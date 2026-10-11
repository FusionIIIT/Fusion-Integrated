"""ELM tables.

Employees, substitutes and authorities are plain `user_id` integers — this
database has no user table, so a cross-boundary reference stays unconstrained.
"""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel

LEAVE_TYPES = [
    ("CL", "Casual Leave"),
    ("RH", "Restricted Holiday"),
    ("SCL", "Special Casual Leave"),
    ("EL", "Earned Leave"),
    ("COL", "Commuted Leave"),
    ("VL", "Vacation Leave"),
]

HALF_DAY = [("", "Full day"), ("first", "First half"), ("second", "Second half")]

REQUEST_KINDS = [
    ("leave", "Leave"),
    ("extension", "Extension"),
    ("cancellation", "Cancellation"),
]

STATUSES = [
    ("pending_substitute", "Awaiting substitute consent"),
    ("pending_unit_head", "Awaiting Unit Head"),
    ("pending_authority", "Awaiting Sanctioning Authority"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("withdrawn", "Withdrawn"),
    ("cancelled", "Cancelled"),
]


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """One employee's account for one leave category in one leave year."""

    year = models.CharField(max_length=9)            # "2026-27"
    leave_type = models.CharField(max_length=4, choices=LEAVE_TYPES)
    entitled = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    carried_forward = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    availed = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year", "leave_type"],
                                    name="leave_balance_unique_per_year"),
        ]

    def __str__(self) -> str:
        return f"u{self.user_id} {self.year} {self.leave_type}"

    @property
    def available(self):
        return (self.entitled + self.carried_forward) - self.availed


class RestrictedHoliday(TimeStampedModel):
    """The published holiday/RH calendar an RH request must match (BR-EL-003)."""

    year = models.CharField(max_length=9, db_index=True)
    on_date = models.DateField()
    name = models.CharField(max_length=120)
    is_closed_holiday = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_restricted_holiday"
        constraints = [
            models.UniqueConstraint(fields=["on_date", "name"],
                                    name="leave_holiday_unique_per_date"),
        ]

    def __str__(self) -> str:
        return f"{self.on_date} {self.name}"


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """One leave request. Never edited in place: a change means withdraw and
    re-apply (BR-EL-022), and an approved leave is reversed by a cancellation
    request (BR-EL-023)."""

    kind = models.CharField(max_length=14, choices=REQUEST_KINDS, default="leave")
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True,
                               blank=True, related_name="children")
    leave_type = models.CharField(max_length=4, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=6, choices=HALF_DAY, blank=True)
    days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    reason = models.TextField(blank=True)

    # Station Leave travels inside the same application (BR-EL-013).
    station_leave = models.BooleanField(default=False)
    station_place = models.CharField(max_length=120, blank=True)

    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=10, default="not_required")

    status = models.CharField(max_length=20, choices=STATUSES,
                              default="pending_unit_head")
    pending_role = models.CharField(max_length=40, blank=True)
    authority_chain = models.JSONField(default=list, blank=True)
    unit_head_recommendation = models.CharField(max_length=20, blank=True)

    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)

    # Resumption (BR-EL-027, BR-EL-028)
    actual_end_date = models.DateField(null=True, blank=True)
    resumption_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_application"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_app_user_idx"),
            models.Index(fields=["status", "pending_role"],
                         name="leave_app_queue_idx"),
        ]

    def __str__(self) -> str:
        return f"leave#{self.pk} u{self.user_id} {self.leave_type} {self.status}"

    @property
    def is_open(self) -> bool:
        return self.status.startswith("pending_")


class LeaveApproval(models.Model):
    """Append-only record of every routing step and decision."""

    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="approvals")
    step_role = models.CharField(max_length=40)
    action = models.CharField(max_length=20)
    actor_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_approval"
        indexes = [models.Index(fields=["application", "at"],
                                name="leave_approval_app_idx")]

    def __str__(self) -> str:
        return f"leave#{self.application_id} {self.step_role} {self.action}"


class LeaveLedger(TimeStampedModel, UserScopedModel):
    """Every balance movement: deduction on approval, restoration on
    cancellation, year-end lapse and VL→EL conversion."""

    application = models.ForeignKey(LeaveApplication, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name="ledger_entries")
    year = models.CharField(max_length=9)
    leave_type = models.CharField(max_length=4, choices=LEAVE_TYPES)
    delta = models.DecimalField(max_digits=6, decimal_places=1)
    reason = models.CharField(max_length=120)

    class Meta:
        db_table = "leave_ledger"
        indexes = [models.Index(fields=["user_id", "year"],
                                name="leave_ledger_user_idx")]

    def __str__(self) -> str:
        return f"u{self.user_id} {self.leave_type} {self.delta:+}"
