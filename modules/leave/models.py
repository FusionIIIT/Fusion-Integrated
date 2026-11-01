"""Employee Leave Management tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database, and a cross-boundary FK would
make this module impossible to lift out later (ADR-0013). The applicant's
employee kind, department and name are read through `directory's` contracts.

No business logic and no `save()` override: `bulk_update` and `queryset.update()`
bypass both anyway, so the rules live in `domain/` and the writes in
`services/`.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain import categories as cat
from modules.leave.domain.state_machine import (
    DRAFT,
    KIND_CANCELLATION,
    KIND_EXTENSION,
    KIND_NEW,
    KIND_RESUMPTION,
    STATES,
)

#: Status and kind choices are read off the state machine, so a state added
#: there cannot be missing here.
STATUS_CHOICES = [(s, s.replace("_", " ")) for s in sorted(STATES)]
KIND_CHOICES = [
    (KIND_NEW, "New leave"),
    (KIND_EXTENSION, "Extension of ongoing leave"),
    (KIND_CANCELLATION, "Cancellation of approved leave"),
    (KIND_RESUMPTION, "Resumption of duty"),
]

#: Category choices as (value, label) pairs — the domain module keeps codes and
#: labels apart, and Django's `choices` needs them paired (fields.E005).
CATEGORY_CHOICES = [(code, cat.LABELS[code]) for code in cat.CATEGORIES]

#: Decisions recorded against a request, at whatever stage made them.
DECISIONS = [
    ("approve", "Approve"),
    ("reject", "Reject"),
    ("recommended", "Recommended"),
    ("not_recommended", "Not recommended"),
    ("accept", "Substitute accepted"),
    ("decline", "Substitute declined"),
]


class LeavePolicy(TimeStampedModel):
    """The current configured leave-policy parameters (BR-EL-030).

    One row is current at a time; there is no draft/publish/effective-version
    lifecycle in this baseline, so validation simply reads the latest row.
    """

    label = models.CharField(max_length=60, default="Leave policy")
    year_label = models.CharField(max_length=9)          # "2026-27"
    starts_on = models.DateField()
    ends_on = models.DateField()

    # Annual entitlements, per eligible employee (BR-EL-002..009).
    cl_days = models.PositiveSmallIntegerField(default=8)
    rh_days = models.PositiveSmallIntegerField(default=2)
    scl_days = models.PositiveSmallIntegerField(default=15)
    el_days = models.PositiveSmallIntegerField(default=30)
    vl_days = models.PositiveSmallIntegerField(default=60)
    col_days = models.PositiveSmallIntegerField(default=20)

    #: Unused VL converts to EL at 2 VL : 1 EL, fractions included.
    vl_per_el = models.PositiveSmallIntegerField(default=2)

    #: The higher-sanction path, as designations (BR-EL-018/019).
    authority_path = models.JSONField(default=list, blank=True)
    establishment_designation = models.CharField(max_length=60, blank=True)
    establishment_step_enabled = models.BooleanField(default=False)

    #: SLA thresholds for actionable tasks (BR-EL-038).
    reminder_hours = models.PositiveSmallIntegerField(default=48)
    escalation_hours = models.PositiveSmallIntegerField(default=120)

    #: The year-end boundary EVT-01 fires on.
    year_end_on = models.DateField()

    class Meta:
        db_table = "leave_policy"
        ordering = ["-id"]
        verbose_name_plural = "leave policies"

    def __str__(self) -> str:
        return f"{self.label} ({self.year_label})"

    @classmethod
    def current(cls) -> LeavePolicy:
        """The configured values in force right now."""
        return cls.objects.order_by("-id").first()

    @property
    def hierarchy(self):
        from modules.leave.domain.routing import Hierarchy

        return Hierarchy(
            authority_path=tuple(self.authority_path or ()),
            establishment_designation=self.establishment_designation,
            establishment_step_enabled=self.establishment_step_enabled)

    def entitlement(self, code: str) -> int:
        return {
            cat.CL: self.cl_days, cat.RH: self.rh_days, cat.SCL: self.scl_days,
            cat.EL: self.el_days, cat.VL: self.vl_days, cat.COL: self.col_days,
        }.get(code, 0)


class OrganizationalUnit(TimeStampedModel):
    """A department, section or office and its head (ACT-03).

    Leave-owned configuration, because the Unit Head is who this module routes
    to — the IAM directory knows a person's department but not who heads it.
    """

    name = models.CharField(max_length=120, unique=True)
    head_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "leave_org_unit"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class LeaveBalance(UserScopedModel):
    """One employee's account for one category in one leave year.

    `opening` is what carried forward, `credited` is what the year added
    (annual entitlement, or EL produced by VL conversion), `used` is what has
    been consumed. Every change writes a LeaveTransaction, so the account can
    always be explained rather than merely trusted.
    """

    year_label = models.CharField(max_length=9)
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    opening = models.DecimalField(max_digits=6, decimal_places=2,
                                  default=Decimal("0"))
    credited = models.DecimalField(max_digits=6, decimal_places=2,
                                   default=Decimal("0"))
    used = models.DecimalField(max_digits=6, decimal_places=2,
                               default=Decimal("0"))

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year_label", "category"],
                                    name="leave_balance_unique"),
        ]
        indexes = [
            models.Index(fields=["user_id", "year_label"],
                         name="leave_balance_owner_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.category} {self.year_label}"

    @property
    def available(self) -> Decimal:
        return self.opening + self.credited - self.used


class LeaveRequest(UserScopedModel, TimeStampedModel):
    """A submitted leave-related request.

    One table for four kinds of request — new leave, extension, cancellation,
    resumption — because they share one state machine and differ only in what a
    final decision does to the leave they point at. That is also what makes
    "the approved leave is not edited in place" structural: an extension is a
    separate row that carries the incremental period, and the original stays
    exactly as it was sanctioned.
    """

    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default=KIND_NEW)
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=DRAFT)

    from_date = models.DateField()
    to_date = models.DateField()
    #: Set for a half-day CL (BR-EL-010).
    half = models.CharField(max_length=6, blank=True,
                            choices=[(h, h) for h in cat.HALVES])
    days = models.DecimalField(max_digits=6, decimal_places=2)

    purpose = models.TextField(max_length=1000)

    #: Station Leave details, captured inside the same application (BR-EL-013).
    station_leave_required = models.BooleanField(default=False)
    station_leave_details = models.CharField(max_length=300, blank=True)

    #: The approved leave this request acts on.
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True,
                               blank=True, related_name="amendments")

    #: Routing, frozen at submission so a configuration change cannot move a
    #: request that is already halfway through the hierarchy.
    unit_head_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    final_authority = models.CharField(max_length=60, blank=True)
    establishment_first = models.BooleanField(default=False)
    self_sanction = models.BooleanField(default=False)
    #: The applicant's designations, as they were when the request was raised.
    #: Frozen because the Director-specific rule (BR-EL-020) is about who the
    #: applicant IS, and a later role change must not move a live request.
    applicant_roles = models.JSONField(default=list, blank=True)

    #: Responsibility coverage (BR-EL-014/015).
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_response = models.CharField(max_length=12, blank=True)
    substitute_responded_at = models.DateTimeField(null=True, blank=True)

    #: Offline-sanctioned leave recorded after the fact (EL-UC-016).
    is_offline = models.BooleanField(default=False)
    sanction_reference = models.CharField(max_length=120, blank=True)
    sanctioned_on = models.DateField(null=True, blank=True)
    offline_reason = models.CharField(max_length=300, blank=True)

    #: The final decision, once there is one.
    decision = models.CharField(max_length=20, blank=True, choices=DECISIONS)
    decision_remarks = models.CharField(max_length=300, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(to_date__gte=models.F("from_date")),
                                   name="leave_request_period_valid"),
            models.CheckConstraint(condition=Q(days__gte=0),
                                   name="leave_request_days_non_negative"),
            models.CheckConstraint(
                condition=Q(half="") | Q(half__in=list(cat.HALVES)),
                name="leave_request_half_valid"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status", "-created_at"],
                         name="leave_request_owner_idx"),
            models.Index(fields=["status", "category", "-created_at"],
                         name="leave_request_queue_idx"),
            models.Index(fields=["substitute_user_id", "status"],
                         name="leave_request_substitute_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.category} {self.from_date}..{self.to_date}"

    @property
    def is_pending(self) -> bool:
        from modules.leave.domain.state_machine import is_pending

        return is_pending(self.status)

    @property
    def interval(self) -> cat.Interval:
        return cat.Interval(self.from_date, self.to_date, self.half or None)


class LeaveApproval(TimeStampedModel):
    """Append-only record of every decision taken on a request.

    Never updated, never deleted: the audit trail is the only place the
    recommendation history survives, and "Not Recommended is not a final
    rejection" is only defensible if the recommendation is still on file.
    """

    STAGES = [
        ("employee", "Employee"),
        ("substitute", "Substitute consent"),
        ("unit_head", "Unit Head"),
        ("establishment", "Establishment"),
        ("final", "Final sanctioning authority"),
        ("self_sanction", "Director self-sanction"),
    ]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="approvals")
    stage = models.CharField(max_length=16, choices=STAGES)
    decision = models.CharField(max_length=20, choices=DECISIONS)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remarks = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_approval"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["request", "created_at"],
                         name="leave_approval_request_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.stage}: {self.decision}"


class LeaveTask(TimeStampedModel):
    """An actionable workflow task, and the SLA clock that runs against it.

    Created when a request reaches a stage that needs a person, and superseded
    the moment it moves on — so "no escalation if the task is no longer pending"
    is a query against this table rather than a promise (BR-EL-032/033).
    """

    STATUS = [("pending", "Pending"), ("completed", "Completed"),
              ("superseded", "Superseded"), ("cancelled", "Cancelled")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="tasks")
    stage = models.CharField(max_length=16, choices=LeaveApproval.STAGES)
    assignee_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")

    assigned_at = models.DateTimeField(auto_now_add=True)
    actioned_at = models.DateTimeField(null=True, blank=True)
    #: SLA deadlines, stamped from the policy at assignment time.
    reminder_due_at = models.DateTimeField(null=True, blank=True)
    escalation_due_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_task"
        ordering = ["-created_at"]
        indexes = [
            # The reminder sweep's query: pending tasks, oldest deadline first.
            models.Index(fields=["status", "reminder_due_at"],
                         name="leave_task_sla_idx"),
            models.Index(fields=["assignee_user_id", "status"],
                         name="leave_task_assignee_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.stage} -> {self.assignee_user_id} ({self.status})"


class LeaveTransaction(TimeStampedModel):
    """The account ledger. Every balance change is a row here.

    A balance that cannot explain itself is a balance nobody can audit, which
    matters most at year end, when lapse, conversion and carry-forward all land
    on the same evening.
    """

    KINDS = [
        ("annual_credit", "Annual entitlement credited"),
        ("carry_forward", "Carried forward from the previous year"),
        ("approval", "Deducted for approved leave"),
        ("cancellation_reversal", "Restored by an approved cancellation"),
        ("extension_post", "Incremental period posted by an extension"),
        ("resumption_adjustment", "Adjustment after resumption review"),
        ("year_end_lapse", "Lapsed at the year-end boundary"),
        ("year_end_conversion", "Converted to another category"),
        ("offline_entry", "Offline-sanctioned leave recorded"),
    ]

    user_id = models.IntegerField(db_index=True)
    year_label = models.CharField(max_length=9)
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    kind = models.CharField(max_length=24, choices=KINDS)
    #: Signed: positive credits the account, negative consumes it.
    days = models.DecimalField(max_digits=6, decimal_places=2)
    request = models.ForeignKey(LeaveRequest, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="transactions")
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "leave_transaction"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["user_id", "year_label", "category"],
                         name="leave_txn_account_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.days} {self.category}"


class LeaveCalendar(TimeStampedModel):
    """The holiday/RH calendar for a leave year (EL-UC-015).

    Until a replacement is PUBLISHED, the currently effective one governs date
    and RH validation (BR-EL-031) — so "effective" is a property of what is
    published, never of what is being drafted.
    """

    year_label = models.CharField(max_length=9, unique=True)
    label = models.CharField(max_length=120, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_calendar"
        ordering = ["-year_label"]

    def __str__(self) -> str:
        return f"{self.year_label}{' (published)' if self.published_at else ' (draft)'}"


class CalendarEntry(TimeStampedModel):
    """One day in a calendar: a closed holiday, a Restricted Holiday, or a
    vacation period from the Academic Calendar (EXT-01)."""

    KINDS = [
        ("closed_holiday", "Closed holiday"),
        ("restricted_holiday", "Restricted holiday"),
        ("vacation", "Vacation period"),
    ]

    calendar = models.ForeignKey(LeaveCalendar, on_delete=models.CASCADE,
                                 related_name="entries")
    date = models.DateField()
    #: Inclusive; only used by a vacation period, which spans many days.
    ends_on = models.DateField(null=True, blank=True)
    kind = models.CharField(max_length=20, choices=KINDS)
    label = models.CharField(max_length=160, blank=True)

    class Meta:
        db_table = "leave_calendar_entry"
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date", "kind"],
                                    name="leave_calendar_entry_unique"),
        ]
        indexes = [
            models.Index(fields=["calendar", "kind", "date"],
                         name="leave_calendar_lookup_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.kind}"


class LeaveNotification(TimeStampedModel):
    """A notification this module decided to send.

    Written inside the same transaction as the decision that caused it, so a
    notification can never claim something that was rolled back. The delivery
    worker is not part of this change — see the module doc's list of gaps.
    """

    STATUS = [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")]

    topic = models.CharField(max_length=60, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField(db_index=True)
    subject = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                null=True, blank=True, related_name="notifications")

    class Meta:
        db_table = "leave_notification"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.topic} -> {self.recipient_user_id}"
