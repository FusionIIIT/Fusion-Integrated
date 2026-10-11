"""ELM domain tables.

Every person is referenced by plain ``user_id`` integers, never
foreign keys — there is no user table in this database, and the
module boundary rule keeps ELM extractable without schema surgery.

The two projections that routing depends on — :model:`elm.EmployeeProfile`
(designation, organizational unit) and :model:`elm.OrgUnit` (with its
configured Unit Head) — are maintained here because the ELM
specification makes hierarchy configuration an ELM responsibility
(BR-EL-030/031); the IAM remains the identity source.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.db.models import UniqueConstraint

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.elm.domain.leave_types import (
    ACTOR_ESTABLISHMENT,
    ACTOR_SANCTIONING,
    ACTOR_SUBSTITUTE,
    ACTOR_UNIT_HEAD,
    CATEGORY_GROUP_CHOICES,
    CL,
    COL,
    EL,
    HALF_DAY_CHOICES,
    KIND_CANCELLATION,
    KIND_EXTENSION,
    KIND_NEW,
    NOMINATION_STATUSES,
    OUTBOX_STATUSES,
    RECORD_STATUSES,
    RESUMPTION_REVIEW_STATUSES,
    RESUMPTION_STATES,
    RH,
    SCL,
    TASK_STATUSES,
    UNIT_TYPE_CHOICES,
    VL,
)

DAYS = {"max_digits": 6, "decimal_places": 2}

# -- policy and configuration ------------------------------------------


class PolicyConfig(TimeStampedModel):
    """Current leave-policy parameters (BR-EL-030).

    Deliberately *not* versioned: there is no draft/publish
    lifecycle, the single row is what validation reads, and a
    change applies to requests submitted from the next moment.
    """

    #: category -> entitlement parameters
    #: (annual_days, half_day, half_day_value, carry_forward,
    #:  vacation_only, conversion_ratio)
    entitlements = models.JSONField(default=dict, blank=True)

    #: designations whose holder self-sanctions their own leave
    director_designations = models.JSONField(
        default=list, blank=True)
    #: designations that perform Establishment processing
    establishment_designations = models.JSONField(default=list, blank=True)

    #: "MM-DD" — the leave-year boundary used for year-end
    #: processing and leave-year derivation
    year_end_month_day = models.CharField(max_length=5, default="03-31")

    #: Station Leave is captured inside the same application when
    #: the employee will be outside Jabalpur (PS §2) — never a
    #: separate request kind
    station_leave_enabled = models.BooleanField(default=True)

    #: COL may require medical evidence (PS §3)
    medical_evidence_required = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_policy_config"
        verbose_name_plural = "elm policy config"

    def __str__(self) -> str:
        return "current ELM policy"


class HierarchyConfig(TimeStampedModel):
    """Sanctioning path for one (category group, unit type) pair.

    ``cl_rh`` rows end at the Unit Head; ``higher_sanction`` rows
    pass through Establishment processing when configured and end
    at the named Sanctioning Authority.
    """


    category_group = models.CharField(max_length=20,
                                       choices=CATEGORY_GROUP_CHOICES)
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPE_CHOICES)

    establishment_required = models.BooleanField(default=False)
    #: designation name of the competent final authority
    sanctioning_authority = models.CharField(max_length=120,
                                              default="Dean")

    class Meta:
        db_table = "elm_hierarchy_config"
        constraints = [
            UniqueConstraint(
                fields=["category_group", "unit_type"],
                name="elm_hierarchy_one_per_group_unit",
            )
        ]

    def __str__(self) -> str:
        return f"{self.category_group} / {self.unit_type}"


class SlaConfig(TimeStampedModel):
    """Reminder/escalation thresholds per workflow task class
    (EL-UC-021, BR-EL-032/033)."""

    ESCALATION_ACTIONS = [
        ("notify", "Notify the configured authority"),
        ("reassign", "Notify and reassign the task"),
    ]

    task_class = models.CharField(max_length=40, primary_key=True)
    reminder_hours = models.PositiveIntegerField(default=48)
    escalation_hours = models.PositiveIntegerField(default=120)
    escalation_action = models.CharField(
        max_length=20, choices=ESCALATION_ACTIONS, default="notify")
    #: designation notified (or reassigned to) on escalation
    escalation_target_role = models.CharField(max_length=120,
                                               blank=True, default="")

    class Meta:
        db_table = "elm_sla_config"

    def __str__(self) -> str:
        return self.task_class


# -- organizational projection ------------------------------------------


class OrgUnit(TimeStampedModel):
    """An organizational unit: Department, Section or Office (PS §1)."""


    code = models.SlugField(max_length=60, primary_key=True)
    name = models.CharField(max_length=120)
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPE_CHOICES)
    #: the configured Unit Head — an IAM user id
    head_user_id = models.IntegerField(null=True, blank=True,
                                        db_index=True)
    projected = models.BooleanField(
        default=False,
        help_text="Projected from the IAM directory rather than "
                  "maintained locally",
    )

    class Meta:
        db_table = "elm_org_unit"
        verbose_name_plural = "elm organizational units"

    def __str__(self) -> str:
        return f"{self.name} ({self.unit_type})"


class EmployeeProfile(TimeStampedModel):
    """ELM's projection of an employee: kind, designation, unit.

    Routing (Unit Head, Establishment, Sanctioning Authority) is
    resolved from these rows, so they are maintained here rather
    than derived per request.
    """

    EMPLOYEE_KINDS = [("faculty", "Faculty"), ("staff", "Staff")]

    user_id = models.IntegerField(primary_key=True)
    employee_kind = models.CharField(max_length=20,
                                      choices=EMPLOYEE_KINDS)
    designation_name = models.CharField(max_length=120)
    unit_code = models.ForeignKey(
        OrgUnit, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="members",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_employee_profile"

    def __str__(self) -> str:
        return f"{self.user_id}: {self.designation_name}"


# -- calendars ------------------------------------------------------------


class HolidayCalendar(TimeStampedModel):
    """A published holiday / Restricted-Holiday calendar.

    The currently effective calendar is the latest *published*
    row; RH requests must correspond to an RH in it (BR-EL-003).
    Draft rows may be revised freely; publishing promotes a draft
    and deactivates its predecessor.
    """

    name = models.CharField(max_length=120)
    year = models.PositiveIntegerField()
    published_at = models.DateTimeField(null=True, blank=True,
                                         db_index=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["-year"]

    def __str__(self) -> str:
        return f"{self.name} {self.year}"


class Holiday(TimeStampedModel):
    calendar = models.ForeignKey(
        HolidayCalendar, on_delete=models.CASCADE,
        related_name="holidays",
    )
    date = models.DateField()
    label = models.CharField(max_length=120)
    kind = models.CharField(
        max_length=20,
        choices=[("holiday", "Holiday"),
                 ("restricted_holiday", "Restricted Holiday (RH)")],
    )
    #: institute closed — counts as a closed day for non-continuous
    #: categories and as a leave day for EL/COL/VL
    closed = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_holiday"
        constraints = [
            UniqueConstraint(fields=["calendar", "date"],
                             name="elm_holiday_once_per_day")
        ]

    def __str__(self) -> str:
        return f"{self.date} — {self.label}"


class VacationPeriod(TimeStampedModel):
    """Academic-Calendar vacation windows (EXT-01 projection).

    VL is applicable only inside a published vacation period
    (BR-EL-006). The authoritative calendar is maintained by the
    institute Academic Calendar system outside ELM; this is the
    projection ELM reads.
    """

    label = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    academic_year = models.CharField(max_length=12, blank=True,
                                      default="")
    source = models.CharField(max_length=60, default="academic_calendar")

    class Meta:
        db_table = "elm_vacation_period"
        ordering = ["start_date"]

    def __str__(self) -> str:
        return f"{self.label} ({self.start_date} → {self.end_date})"


# -- leave accounts and the ledger ----------------------------------------


class LeaveAccount(TimeStampedModel):
    """An employee's leave account for one category and leave year.

    ``available = opening + entitled - used - pending`` — pending
    (non-terminal) requests reserve their days, computed by the
    selectors rather than stored.
    """

    CATEGORIES = [(c, c) for c in (CL, RH, SCL, EL, COL, VL)]

    user_id = models.IntegerField(db_index=True)
    leave_year = models.CharField(max_length=9)      # "2026-27"
    category = models.CharField(max_length=10, choices=CATEGORIES)

    opening_days = models.DecimalField(
        **DAYS, default=Decimal("0"),
        help_text="Carried forward from the previous leave year",
    )
    entitled_days = models.DecimalField(**DAYS, default=Decimal("0"))
    used_days = models.DecimalField(**DAYS, default=Decimal("0"))

    class Meta:
        db_table = "elm_leave_account"
        constraints = [
            UniqueConstraint(
                fields=["user_id", "leave_year", "category"],
                name="elm_account_one_per_year_category",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.leave_year} {self.category}"


class LeaveTransaction(TimeStampedModel):
    """Append-only ledger of every balance movement.

    Balances are never edited in place — approval, cancellation
    restoration, year-end lapse / conversion / carry-forward,
    offline records and resumption adjustments all post a signed
    delta, so any account state is reconstructible.
    """

    KINDS = [
        ("approval", "Leave approved"),
        ("cancellation_restoration", "Cancelled leave restored"),
        ("year_end_lapse", "Year-end lapse"),
        ("year_end_carry_forward", "Year-end carry-forward"),
        ("vl_conversion", "VL converted to EL (year end)"),
        ("offline_record", "Offline-sanctioned leave recorded"),
        ("resumption_adjustment", "Resumption review adjustment"),
        ("extension_posting", "Extension incremental posting"),
        ("correction", "Administrative correction"),
    ]

    account = models.ForeignKey(
        LeaveAccount, on_delete=models.PROTECT,
        related_name="transactions",
    )
    delta = models.DecimalField(**DAYS)
    balance_after = models.DecimalField(**DAYS)
    kind = models.CharField(max_length=30, choices=KINDS)
    reason = models.TextField(blank=True, default="")

    request = models.ForeignKey(
        "LeaveRequest", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="ledger_entries",
    )
    offline_record = models.ForeignKey(
        "OfflineLeaveRecord", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="ledger_entries",
    )
    actor_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_transaction"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.kind} {self.delta} on {self.account}"


# -- the workflow object ----------------------------------------------------


class LeaveRequest(UserScopedModel, TimeStampedModel):
    """One leave workflow object.

    ``kind`` selects which state machine applies:

    * ``new`` — an application (EL-UC-001)
    * ``cancellation`` — a request to cancel approved leave,
      referencing the application in ``base_request`` (EL-UC-008)
    * ``extension`` — a request to extend ongoing EL/COL/VL,
      referencing the ongoing application (EL-UC-009)

    The resolved ``route`` is snapshotted at submission so reviews
    replay the path that was valid then, even if the hierarchy
    configuration changes mid-flight.
    """

    KINDS = [(KIND_NEW, "New leave application"),
             (KIND_CANCELLATION, "Cancellation of approved leave"),
             (KIND_EXTENSION, "Extension of ongoing leave")]
    CATEGORIES = [(c, c) for c in (CL, RH, SCL, EL, COL, VL)]
    RECOMMENDATIONS = [
        ("recommended", "Recommended"),
        ("not_recommended", "Not Recommended"),
    ]

    kind = models.CharField(max_length=20, choices=KINDS)
    category = models.CharField(max_length=10, choices=CATEGORIES)
    status = models.CharField(max_length=40, db_index=True)

    #: the application a cancellation/extension acts on
    base_request = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE,
        related_name="derived_requests",
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    start_half = models.CharField(
        max_length=10, choices=HALF_DAY_CHOICES, default="full")
    end_half = models.CharField(
        max_length=10, choices=HALF_DAY_CHOICES, default="full")
    purpose = models.TextField(blank=True, default="")

    days = models.DecimalField(**DAYS, default=Decimal("0"))
    leave_year = models.CharField(max_length=9, blank=True, default="")

    #: Station Leave, captured inside this same application when the
    #: employee will be outside Jabalpur (PS §2)
    station_leave = models.BooleanField(default=False)
    station_details = models.JSONField(
        default=dict, blank=True,
        help_text="destination, from/to dates, purpose",
    )

    substitute_required = models.BooleanField(default=False)

    #: evidence references carried with the application —
    #: e.g. the medical certificate for COL when policy
    #: requires it (PS §3)
    evidence = models.JSONField(
        default=dict, blank=True,
        help_text="kind -> reference/description",
    )

    #: resolved route snapshot: [{role, decision, authority}, …]
    route = models.JSONField(default=list, blank=True)
    current_step = models.PositiveSmallIntegerField(default=0)

    recommendation = models.CharField(
        max_length=20, choices=RECOMMENDATIONS, blank=True,
        default="")
    recommendation_reason = models.TextField(blank=True, default="")

    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True, default="")

    #: set when the request is approved — the posted leave itself
    leave_record = models.ForeignKey(
        "LeaveRecord", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="source_requests",
    )

    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdraw_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kind} {self.category} {self.status} ({self.user_id})"


class SubstituteNomination(TimeStampedModel):
    """One substitute nomination (EL-UC-001/002/009).

    Exactly one active nomination exists per request: a decline
    moves the request to applicant action, and nominating someone
    else supersedes the declined row rather than reusing it.
    """


    request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE,
        related_name="substitute_nominations",
    )
    nominee_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=NOMINATION_STATUSES,
                               default="pending")
    responded_at = models.DateTimeField(null=True, blank=True)
    response_reason = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_substitute_nomination"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"nominee {self.nominee_user_id} — {self.status}"


class LeaveTask(TimeStampedModel):
    """One actionable workflow task (BR-EL-035).

    Created when a request enters a state that awaits an actor,
    completed when that actor acts. SLA reminder/escalation
    timestamps hang off the task (EL-UC-021).
    """

    TASK_CLASSES = [
        ("substitute_response", "Substitute response"),
        ("unit_head_review", "Unit Head review"),
        ("establishment_routing", "Establishment routing"),
        ("final_sanction", "Final sanctioning decision"),
        ("resumption_review", "Resumption review"),
    ]
    ASSIGNEE_ROLES = [
        (ACTOR_SUBSTITUTE, "Substitute / Responsibility Holder"),
        (ACTOR_UNIT_HEAD, "Unit Head"),
        (ACTOR_ESTABLISHMENT, "Establishment Processing Role"),
        (ACTOR_SANCTIONING, "Sanctioning Authority"),
    ]

    request = models.ForeignKey(
        LeaveRequest, null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="tasks",
        help_text="Null for resumption tasks on "
                  "offline-recorded leave, which has "
                  "no application",
    )
    task_class = models.CharField(max_length=30, choices=TASK_CLASSES)
    assignee_user_id = models.IntegerField(db_index=True)
    assignee_role = models.CharField(max_length=30,
                                      choices=ASSIGNEE_ROLES)
    status = models.CharField(max_length=20, choices=TASK_STATUSES,
                               default="pending", db_index=True)
    outcome = models.CharField(max_length=30, blank=True, default="")
    reason = models.TextField(blank=True, default="")

    reminder_at = models.DateTimeField(null=True, blank=True)
    escalation_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_detail = models.JSONField(default=dict, blank=True)

    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_task"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.task_class} for {self.assignee_user_id} ({self.status})"


class RequestEvent(TimeStampedModel):
    """Append-only audit trail of everything that happens to a
    request — state changes, task assignments, notifications,
    reminders and escalations (BR-EL-036 record maintenance)."""

    EVENT_KINDS = [
        ("state_change", "State change"),
        ("task_assigned", "Task assigned"),
        ("task_completed", "Task completed"),
        ("task_cancelled", "Task cancelled"),
        ("notification", "Notification sent"),
        ("reminder", "SLA reminder"),
        ("escalation", "SLA escalation"),
        ("balance_posted", "Balance movement posted"),
    ]

    request = models.ForeignKey(
        LeaveRequest, null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="events",
        help_text="Null for events about offline-recorded "
                  "leave, which has no application",
    )
    event = models.CharField(max_length=20, choices=EVENT_KINDS)
    from_status = models.CharField(max_length=40, blank=True,
                                    default="")
    to_status = models.CharField(max_length=40, blank=True, default="")
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=120, blank=True,
                                    default="")
    outcome = models.CharField(max_length=40, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_request_event"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.event} on {self.request_id} at {self.at}"


# -- approved leave, resumption, offline records ---------------------------


class LeaveRecord(TimeStampedModel):
    """An approved (or recorded) leave interval — the leave itself.

    Created when an application is sanctioned, when an extension
    posts its incremental period (``extends_record`` links the
    increment to its base), or when an offline-sanctioned leave is
    recorded. Cancellation marks it ``cancelled`` without deleting
    history.
    """


    user_id = models.IntegerField(db_index=True)
    leave_year = models.CharField(max_length=9)
    category = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    start_half = models.CharField(
        max_length=10, choices=HALF_DAY_CHOICES, default="full")
    end_half = models.CharField(
        max_length=10, choices=HALF_DAY_CHOICES, default="full")
    days = models.DecimalField(**DAYS)
    status = models.CharField(max_length=20, choices=RECORD_STATUSES,
                               default="ongoing")

    station_leave = models.BooleanField(default=False)
    station_details = models.JSONField(default=dict, blank=True)

    source_request = models.ForeignKey(
        LeaveRequest, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="posted_records",
    )
    #: the original approved leave this increment extends
    extends_record = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="extension_increments",
    )
    offline_record = models.ForeignKey(
        "OfflineLeaveRecord", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="posted_records",
    )
    #: set by resumption review (normal / early / late)
    actual_end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_record"
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return f"{self.user_id} {self.category} {self.start_date}→{self.end_date}"


class Resumption(TimeStampedModel):
    """A resumption-of-duty submission (EL-UC-010/011).

    Review outcomes: normal (no adjustment), early return
    (balance adjusted up, records synchronized) or late return
    (balance adjusted down, records synchronized).
    """


    record = models.ForeignKey(
        LeaveRecord, on_delete=models.CASCADE,
        related_name="resumptions",
    )
    request = models.ForeignKey(
        LeaveRequest, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="resumptions",
    )
    actual_resumption_date = models.DateField()
    details = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=RESUMPTION_REVIEW_STATUSES,
                               default=RESUMPTION_STATES[0])
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    #: signed day adjustment applied on early/late review
    adjustment_days = models.DecimalField(
        **DAYS, null=True, blank=True)
    sync_note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_resumption"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"resumption of record {self.record_id}"


class OfflineLeaveRecord(TimeStampedModel):
    """An already-sanctioned leave entered retrospectively (EL-UC-017).

    Used when ELM was unavailable while the leave was sanctioned on
    paper. The sanction evidence is mandatory, the entry is checked
    for record consistency, and it posts straight to the ledger —
    it deliberately carries no workflow and no sanctioning power
    (BR-EL-037).
    """

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    start_half = models.CharField(
        max_length=10, choices=HALF_DAY_CHOICES, default="full")
    end_half = models.CharField(
        max_length=10, choices=HALF_DAY_CHOICES, default="full")
    days = models.DecimalField(**DAYS)

    sanction_reference = models.CharField(max_length=120)
    sanction_date = models.DateField()
    sanctioning_authority = models.CharField(max_length=120)
    evidence_description = models.TextField(
        help_text="What the uploaded / referenced evidence is")
    reason_elm_unavailable = models.TextField()

    #: result of the consistency validation against existing records
    consistency_check = models.JSONField(default=dict, blank=True)

    recorded_by_user_id = models.IntegerField()
    leave_record = models.ForeignKey(
        LeaveRecord, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="offline_source",
    )

    class Meta:
        db_table = "elm_offline_leave_record"
        ordering = ["-sanction_date"]

    def __str__(self) -> str:
        return f"offline {self.category} {self.sanction_reference}"


# -- SLA and year-end audit -------------------------------------------------


class SlaEventLog(TimeStampedModel):
    """Every reminder and escalation the SLA sweep performed."""

    EVENT_KINDS = [("reminder", "Reminder"),
                   ("escalation", "Escalation")]

    task = models.ForeignKey(
        LeaveTask, on_delete=models.CASCADE,
        related_name="sla_events",
    )
    kind = models.CharField(max_length=20, choices=EVENT_KINDS)
    detail = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_sla_event_log"
        ordering = ["-id"]


class YearEndRun(TimeStampedModel):
    """One year-end processing run (EL-UC-020).

    Records what was processed and, just as importantly, what could
    not be processed consistently — the exceptions report the
    specification requires.
    """

    leave_year = models.CharField(max_length=9, primary_key=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    processed_by_user_id = models.IntegerField(null=True, blank=True)
    stats = models.JSONField(default=dict, blank=True)
    exceptions = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "elm_year_end_run"

    def __str__(self) -> str:
        return f"year-end {self.leave_year}"


class Notification(TimeStampedModel):
    """ELM's outbox (BR-EL-035: task assignment notifies the assignee).

    The platform has no shared notification service yet, so ELM owns
    its outbox the same way the placement module does: services
    enqueue, a Celery task drains. ``dedupe_key`` keeps a sweep from
    notifying twice for the same event.
    """


    recipient_user_id = models.IntegerField(db_index=True)
    topic = models.CharField(max_length=60)
    subject = models.CharField(max_length=200)
    body = models.TextField(blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=OUTBOX_STATUSES,
                               default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True,
                                      db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True,
                                   null=True, blank=True)

    class Meta:
        db_table = "elm_notification"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.topic} → {self.recipient_user_id}"
