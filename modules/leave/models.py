"""Leave domain tables (ELM).

Institute people are referenced by plain `user_id` integers, never foreign keys
— this database holds no user table (ADR-0013). Every table is prefixed
`leave_` and belongs to this module alone.

Two rules from the ELM baseline shape the schema:

  BR-EL-030  no draft/publish/effective-version lifecycle for leave-policy
             parameters: the current configured row is the one in force.
  BR-EL-031  the *published* holiday/RH calendar governs until a replacement is
             published, so publication is a state, not a version number.

Amounts are Decimal, not float: an approved half CL is 0.5 days and VL converts
to EL at 2:1 including fractions, so the arithmetic must be exact.
"""
from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel

#: Status vocabulary, mirrored from modules/leave/domain/state_machine.py.
REQUEST_STATUSES = [
    ("draft", "Draft / not submitted"),
    ("awaiting_substitute_response", "Awaiting substitute response"),
    ("applicant_action_required", "Applicant action required"),
    ("awaiting_unit_head_review", "Awaiting Unit Head review"),
    ("awaiting_establishment_routing", "Awaiting Establishment routing"),
    ("awaiting_final_sanction_decision", "Awaiting final sanction decision"),
    ("awaiting_director_self_sanction", "Awaiting Director self-sanction"),
    ("awaiting_extension_substitute_response",
     "Awaiting extension substitute response"),
    ("extension_applicant_action_required", "Extension applicant action required"),
    ("awaiting_extension_unit_head_review", "Awaiting extension Unit Head review"),
    ("extension_pending_establishment", "Extension pending — Establishment"),
    ("extension_pending_final_decision", "Extension pending — final decision"),
    ("cancellation_pending_unit_head_review",
     "Cancellation pending — Unit Head review"),
    ("cancellation_pending_establishment", "Cancellation pending — Establishment"),
    ("cancellation_pending_final_decision", "Cancellation pending — final decision"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("withdrawn", "Withdrawn"),
    ("cancelled", "Cancelled"),
    ("cancellation_rejected", "Cancellation rejected"),
    ("extension_withdrawn", "Extension request withdrawn"),
    ("extended", "Extended — incremental period posted"),
    ("extension_rejected", "Extension rejected — original leave unchanged"),
]


# -- Configuration (BR-EL-030, BR-EL-031, BR-EL-038) ---------------------------
class LeavePolicy(TimeStampedModel):
    """The current configured leave-policy parameters.

    One row per year with `is_current` naming the one in force. There is no
    draft/publish lifecycle here on purpose (BR-EL-030): an administrator edits
    the current row and the next validation uses it.
    """

    leave_year = models.PositiveSmallIntegerField(unique=True)
    label = models.CharField(max_length=60, blank=True)
    is_current = models.BooleanField(default=True, db_index=True)

    #: Entitlement per leave category, keyed by category code.
    entitlements = models.JSONField(default=dict, blank=True)

    #: BR-EL-011: categories counted continuously across the approved interval.
    continuous_counting = models.JSONField(default=list, blank=True)
    #: BR-EL-010: categories supporting a half day.
    half_day_categories = models.JSONField(default=list, blank=True)
    #: Which employee kinds may use which category (BR-EL-001).
    category_kinds = models.JSONField(default=dict, blank=True)

    #: BR-EL-013: does this category require responsibility coverage?
    substitute_required_categories = models.JSONField(default=list, blank=True)
    #: BR-EL-007: VL to EL at 2:1, including fractions.
    vl_to_el_ratio = models.DecimalField(max_digits=4, decimal_places=2,
                                         default=Decimal("2"))

    #: EVT-01: the year-end boundary that triggers EL-UC-020.
    year_end_month = models.PositiveSmallIntegerField(default=12)
    year_end_day = models.PositiveSmallIntegerField(default=31)

    #: BR-EL-004: admissibility of an SCL purpose is authority judgement, so
    #: this is a note the authority reads, not an encoded criterion.
    scl_admissibility_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_policy"
        ordering = ["-leave_year"]
        indexes = [models.Index(fields=["is_current"], name="leave_policy_current_idx")]

    def __str__(self) -> str:
        return f"leave policy {self.leave_year}{' (current)' if self.is_current else ''}"


class HierarchyStep(TimeStampedModel):
    """One configured step of the processing/sanctioning path (BR-EL-019).

    The route is resolved from applicant, unit, designation, category and this
    table. A step is one of:

        unit_head      the applicant's own Unit Head (review / recommend / decide)
        establishment  Deputy Registrar (Estt.) verification and routing
        sanction       final competent authority

    `authority` names the office whose queue a `sanction` step is, so the same
    configured path can end at the Dean for one unit and the Registrar for
    another without a code change.
    """

    STEP_KINDS = [("unit_head", "Unit Head"), ("establishment", "Establishment"),
                  ("sanction", "Final sanctioning authority")]
    AUTHORITIES = [
        ("deputy_registrar_estt", "Deputy Registrar (Estt.)"),
        ("dean", "Dean"),
        ("registrar", "Registrar"),
        ("director", "Director"),
    ]

    category = models.CharField(max_length=8, blank=True)     # blank = any
    unit = models.CharField(max_length=60, blank=True)         # blank = any
    designation = models.CharField(max_length=80, blank=True)  # blank = any

    step_order = models.PositiveSmallIntegerField()
    step_kind = models.CharField(max_length=16, choices=STEP_KINDS)
    authority = models.CharField(max_length=32, choices=AUTHORITIES, blank=True)
    label = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_hierarchy_step"
        ordering = ["category", "step_order"]
        indexes = [models.Index(fields=["category", "is_active"],
                                name="leave_step_category_idx")]
        constraints = [
            models.UniqueConstraint(fields=["category", "unit", "designation",
                                            "step_order"],
                                    name="leave_step_unique_position"),
        ]

    def __str__(self) -> str:
        return f"{self.category or 'any'} step {self.step_order} ({self.step_kind})"


class HolidayCalendar(TimeStampedModel):
    """A leave year's holidays and Restricted Holidays (BR-EL-031).

    Only a published calendar governs. Publishing a replacement flips
    `is_effective` in the same transaction, so the previously published one
    remains in force until that moment.
    """

    leave_year = models.PositiveSmallIntegerField(db_index=True)
    label = models.CharField(max_length=80, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    is_effective = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        ordering = ["-leave_year", "-published_at"]
        constraints = [
            # An effective calendar must have been published.
            models.CheckConstraint(
                condition=~Q(is_effective=True) | Q(published_at__isnull=False),
                name="leave_calendar_effective_is_published",
            ),
        ]

    def __str__(self) -> str:
        return f"calendar {self.leave_year}{' (effective)' if self.is_effective else ''}"


class HolidayEntry(TimeStampedModel):
    """One dated entry. `restricted_holiday` is what an RH request must match."""

    KINDS = [("closed_holiday", "Closed holiday"),
             ("restricted_holiday", "Restricted holiday")]

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="entries")
    date = models.DateField()
    kind = models.CharField(max_length=20, choices=KINDS)
    label = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "leave_holiday_entry"
        ordering = ["date"]
        indexes = [models.Index(fields=["calendar", "kind", "date"],
                                name="leave_holiday_lookup_idx")]
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"],
                                    name="leave_holiday_unique_per_day"),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.kind}"


class SlaThreshold(TimeStampedModel):
    """Configurable reminder and escalation thresholds (BR-EL-038).

    `escalation_action` distinguishes notification-only escalation from one
    that changes routing/responsibility — XTP-EL-01 applies to the second.
    """

    ACTION_KINDS = [("notify", "Notify only"), ("reassign", "Reassign routing")]

    task_class = models.CharField(max_length=40, unique=True)
    reminder_hours = models.PositiveIntegerField()
    escalation_hours = models.PositiveIntegerField()
    escalation_action = models.CharField(max_length=12, choices=ACTION_KINDS,
                                         default="notify")
    escalate_to_role = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_sla_threshold"
        constraints = [
            models.CheckConstraint(
                condition=Q(escalation_hours__gte=models.F("reminder_hours")),
                name="leave_sla_escalation_after_reminder",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.task_class} {self.reminder_hours}h/{self.escalation_hours}h"


# -- Accounts (BR-EL-002..009) -------------------------------------------------
class LeaveBalance(TimeStampedModel, UserScopedModel):
    """A materialised leave account for one employee, category and leave year.

    `used_days` is what has been deducted; `lapsed_days` and `carried_days`
    record the year-end outcome. The authority for every movement is the ledger
    below, which is append-only.
    """

    leave_year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=8)

    entitled_days = models.DecimalField(max_digits=6, decimal_places=2,
                                        default=Decimal("0"))
    carried_days = models.DecimalField(max_digits=6, decimal_places=2,
                                       default=Decimal("0"))
    used_days = models.DecimalField(max_digits=6, decimal_places=2,
                                    default=Decimal("0"))
    lapsed_days = models.DecimalField(max_digits=6, decimal_places=2,
                                      default=Decimal("0"))

    class Meta:
        db_table = "leave_balance"
        indexes = [models.Index(fields=["user_id", "leave_year"],
                                name="leave_balance_user_year_idx")]
        constraints = [
            models.UniqueConstraint(fields=["user_id", "category", "leave_year"],
                                    name="leave_balance_unique_account"),
            models.CheckConstraint(condition=Q(used_days__gte=0),
                                   name="leave_balance_used_not_negative"),
        ]

    @property
    def available_days(self) -> Decimal:
        return self.entitled_days + self.carried_days - self.used_days

    def __str__(self) -> str:
        return f"u{self.user_id} {self.category} {self.leave_year} ({self.available_days} left)"


class LeaveLedgerEntry(models.Model):
    """Append-only leave-account transaction (EL-UC-020 records these).

    Entry types: credit · debit · restore · lapse · carry_forward · convert ·
    adjust · year_end. Nothing updates a row here; a correction is a new entry.
    """

    TYPES = [("credit", "Credit"), ("debit", "Debit"), ("restore", "Restore"),
             ("lapse", "Year-end lapse"), ("carry_forward", "Carry forward"),
             ("convert", "VL to EL conversion"), ("adjust", "Administrative adjustment")]

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8)
    leave_year = models.PositiveSmallIntegerField()
    entry_type = models.CharField(max_length=16, choices=TYPES)
    days = models.DecimalField(max_digits=6, decimal_places=2)
    request_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "leave_ledger_entry"
        ordering = ["-at", "-id"]
        indexes = [models.Index(fields=["user_id", "leave_year", "-at"],
                                name="leave_ledger_user_idx")]

    def __str__(self) -> str:
        return f"{self.entry_type} {self.days} {self.category} u{self.user_id}"


# -- Requests ------------------------------------------------------------------
class LeaveRequest(TimeStampedModel, UserScopedModel):
    """One leave request: a new application, an extension or a cancellation.

    A cancellation and an extension are their own requests that never edit the
    approved leave in place (BR-EL-023, BR-EL-034); `base_request` points at the
    leave they act on. `route` freezes the configured path resolved at
    submission, so a later hierarchy edit cannot rewrite a decision's history.
    """

    KINDS = [("new", "New leave application"), ("extension", "Extension of leave"),
             ("cancellation", "Cancellation of approved leave")]

    CATEGORIES = [("cl", "Casual Leave"), ("rh", "Restricted Holiday"),
                  ("scl", "Special Casual Leave"), ("el", "Earned Leave"),
                  ("col", "Commuted Leave"), ("vl", "Vacation Leave")]

    HALVES = [("", "Full day"), ("first", "First half"), ("second", "Second half")]

    SOURCES = [("online", "Submitted through ELM"),
               ("offline", "Already sanctioned offline and synchronised")]

    kind = models.CharField(max_length=12, choices=KINDS, default="new")
    category = models.CharField(max_length=8, choices=CATEGORIES)
    status = models.CharField(max_length=48, choices=REQUEST_STATUSES,
                              default="draft", db_index=True)

    reference = models.CharField(max_length=32, unique=True, null=True, blank=True)
    base_request = models.ForeignKey("self", null=True, blank=True,
                                     on_delete=models.PROTECT,
                                     related_name="derived_requests")

    period_from = models.DateField()
    period_to = models.DateField()
    half = models.CharField(max_length=8, choices=HALVES, blank=True)
    days_counted = models.DecimalField(max_digits=6, decimal_places=2,
                                       default=Decimal("0"))
    purpose = models.CharField(max_length=300, blank=True)

    #: BR-EL-013: Station Leave is information inside this application.
    station_leave = models.JSONField(default=dict, blank=True)

    #: BR-EL-014/015: one nominee at a time; consent gates the routing.
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_required = models.BooleanField(default=False)

    #: BR-EL-019/030: the resolved path, frozen at submission.
    route = models.JSONField(default=list, blank=True)
    current_step = models.PositiveSmallIntegerField(default=0)

    applicant_is_director = models.BooleanField(default=False)
    #: BR-EL-017: the Unit Head's recommendation for a higher-sanction request.
    recommendation = models.CharField(max_length=16, blank=True)
    recommendation_note = models.CharField(max_length=300, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)

    source = models.CharField(max_length=8, choices=SOURCES, default="online")
    #: BR-EL-029: sanction/reference evidence for an offline-sanctioned record.
    evidence_reference = models.CharField(max_length=160, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_request_user_idx"),
            models.Index(fields=["status", "current_step"],
                         name="leave_request_queue_idx"),
            models.Index(fields=["category", "-period_from"],
                         name="leave_request_period_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(period_to__gte=models.F("period_from")),
                                   name="leave_request_period_ordered"),
            # A half day only makes sense on a single date (BR-EL-010).
            models.CheckConstraint(
                condition=Q(half="") | Q(period_from=models.F("period_to")),
                name="leave_request_half_is_one_day",
            ),
            # An offline synchronisation must carry its sanction evidence.
            models.CheckConstraint(
                condition=~Q(source="offline") | ~Q(evidence_reference=""),
                name="leave_request_offline_has_evidence",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.reference or self.pk} u{self.user_id} {self.category} {self.status}"


class LeaveSubstituteAssignment(TimeStampedModel):
    """One nomination of a responsibility holder, kept as a history.

    A decline supersedes the assignment and the applicant nominates a
    replacement (EL-UC-019); the declined row stays so the recovery traversal
    is visible in the audit trail.
    """

    STATUSES = [("nominated", "Nominated"), ("accepted", "Accepted"),
                ("declined", "Declined"), ("superseded", "Superseded")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                               related_name="substitutions")
    nominee_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=STATUSES, default="nominated")
    responded_at = models.DateTimeField(null=True, blank=True)
    response_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_substitute_assignment"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["nominee_user_id", "status"],
                                name="leave_substitute_nominee_idx")]
        constraints = [
            # Exactly one assignment may await a response at a time.
            models.UniqueConstraint(
                fields=["request"], condition=Q(status="nominated"),
                name="leave_one_open_substitution_per_request"),
        ]

    def __str__(self) -> str:
        return f"request {self.request_id} -> u{self.nominee_user_id} ({self.status})"


class WorkflowTask(TimeStampedModel):
    """An actionable step in a resolved route (BR-EL-035, BR-EL-038).

    Opening a task is what notifies its assignee; the SLA sweep reminds or
    escalates only while the task is still pending (BR-EL-032/033).
    """

    STATUSES = [("pending", "Pending"), ("completed", "Completed"),
                ("cancelled", "Cancelled")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                               related_name="tasks")
    step_order = models.PositiveSmallIntegerField()
    step_kind = models.CharField(max_length=16)
    task_class = models.CharField(max_length=40, db_index=True)
    authority = models.CharField(max_length=32, blank=True)

    assignee_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    assignee_role = models.CharField(max_length=80, blank=True)

    status = models.CharField(max_length=12, choices=STATUSES, default="pending",
                              db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_workflow_task"
        ordering = ["request", "step_order", "-id"]
        indexes = [
            models.Index(fields=["status", "assigned_at"],
                         name="leave_task_sla_idx"),
            models.Index(fields=["assignee_user_id", "status"],
                         name="leave_task_assignee_idx"),
        ]

    def __str__(self) -> str:
        return f"task {self.task_class} request {self.request_id} ({self.status})"


class LeaveRequestTransition(models.Model):
    """Append-only audit of every request movement (ELM keeps history)."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                               related_name="transitions")
    from_status = models.CharField(max_length=48)
    to_status = models.CharField(max_length=48)
    action = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=80, blank=True)
    step_kind = models.CharField(max_length=16, blank=True)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "leave_request_transition"
        ordering = ["-at", "-id"]
        indexes = [models.Index(fields=["request", "at"],
                                name="leave_transition_request_idx")]

    def __str__(self) -> str:
        return f"request {self.request_id} {self.from_status}->{self.to_status}"


class LeaveResumption(TimeStampedModel, UserScopedModel):
    """Actual return to duty after EL/COL/VL (BR-EL-027, BR-EL-028).

    Review outcome distinguishes normal, early and late return; no generic
    "closed" status is invented.
    """

    OUTCOMES = [("pending", "Resumption review pending"),
                ("no_adjustment", "Reviewed — no adjustment"),
                ("early", "Reviewed — early return synchronised"),
                ("late", "Reviewed — late return synchronised")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.PROTECT,
                               related_name="resumptions")
    actual_date = models.DateField()
    remarks = models.CharField(max_length=300, blank=True)
    outcome = models.CharField(max_length=16, choices=OUTCOMES, default="pending",
                               db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    review_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_resumption"
        indexes = [models.Index(fields=["user_id", "-actual_date"],
                                name="leave_resumption_user_idx")]

    def __str__(self) -> str:
        return f"resumption request {self.request_id} {self.actual_date} ({self.outcome})"


class LeaveRecordAdjustment(TimeStampedModel):
    """Authorized leave-record maintenance (EL-UC-017, BR-EL-037).

    Recorded separately from any sanction so the two can never be confused:
    this table has no decision, only a change and its reason.
    """

    ACTIONS = [("update", "Correct a recorded value"),
               ("close", "Close a stale record"),
               ("annotate", "Attach an administrative note")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                               related_name="adjustments")
    action = models.CharField(max_length=12, choices=ACTIONS)
    field = models.CharField(max_length=60, blank=True)
    before = models.CharField(max_length=200, blank=True)
    after = models.CharField(max_length=200, blank=True)
    reason = models.CharField(max_length=300)
    actor_user_id = models.IntegerField()
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "leave_record_adjustment"
        indexes = [models.Index(fields=["request", "at"],
                                name="leave_adjustment_request_idx")]

    def __str__(self) -> str:
        return f"adjustment request {self.request_id} {self.action} {self.field}"


# -- Event-triggered processing (EL-UC-020, EL-UC-021) -------------------------
class YearEndRun(TimeStampedModel):
    """One execution of the year-end boundary event (EVT-01).

    Exceptions are reported rather than silently committed, so the run carries
    its own status and the exceptions hang off it.
    """

    STATUSES = [("running", "Running"), ("completed", "Completed"),
                ("completed_with_exceptions", "Completed with exceptions"),
                ("failed", "Failed")]

    leave_year = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=32, choices=STATUSES, default="running")
    accounts_processed = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_year_end_run"
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(fields=["leave_year"],
                                    name="leave_year_end_run_unique_year"),
        ]

    def __str__(self) -> str:
        return f"year-end {self.leave_year} ({self.status})"


class YearEndException(models.Model):
    """An account the run could not process consistently (EL-UC-020 A1)."""

    run = models.ForeignKey(YearEndRun, on_delete=models.CASCADE,
                            related_name="exceptions")
    user_id = models.IntegerField(null=True, blank=True)
    category = models.CharField(max_length=8, blank=True)
    reason = models.CharField(max_length=300)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_year_end_exception"

    def __str__(self) -> str:
        return f"{self.category or 'account'} u{self.user_id}: {self.reason}"


class SlaEvent(models.Model):
    """Every issued reminder and escalation, and every task skipped because it
    was no longer pending (BR-EL-032/033 make that distinguishable)."""

    KINDS = [("reminder", "Reminder"), ("escalation", "Escalation"),
             ("skipped", "Skipped — task no longer pending")]

    task = models.ForeignKey(WorkflowTask, on_delete=models.CASCADE,
                            related_name="sla_events")
    kind = models.CharField(max_length=12, choices=KINDS)
    threshold_hours = models.PositiveIntegerField()
    recipient_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "leave_sla_event"
        indexes = [models.Index(fields=["kind", "-at"], name="leave_sla_event_kind_idx")]

    def __str__(self) -> str:
        return f"{self.kind} for task {self.task_id}"


class LeaveNotificationOutbox(TimeStampedModel):
    """A notification ELM decided to send (BR-EL-035).

    Written inside the transaction that caused it and drained by a worker, so a
    decision and its notification commit together or not at all. Modules own
    their own outbox rather than sharing placement's table.
    """

    STATUSES = [("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"),
                ("failed", "Failed"), ("suppressed", "Suppressed")]

    topic = models.CharField(max_length=60, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField(null=True, blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=12, choices=STATUSES, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_notification_outbox"
        indexes = [
            models.Index(fields=["status", "created_at"],
                         name="leave_outbox_pending_idx"),
            models.Index(fields=["recipient_user_id", "-created_at"],
                         name="leave_outbox_recipient_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.topic} -> u{self.recipient_user_id}"
