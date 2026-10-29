"""The leave request itself, its substitute nominations, and its open tasks."""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm

SELF_SERVICE = "self_service"
OFFLINE_SANCTIONED = "offline_sanctioned"

RECOMMENDED = "recommended"
NOT_RECOMMENDED = "not_recommended"

# -- nomination ---------------------------------------------------------------
NOMINATION_PENDING = "pending"
NOMINATION_ACCEPTED = "accepted"
NOMINATION_DECLINED = "declined"
NOMINATION_SUPERSEDED = "superseded"
NOMINATION_WITHDRAWN = "withdrawn"

NOMINATION_STATUSES: tuple[str, ...] = (
    NOMINATION_PENDING, NOMINATION_ACCEPTED, NOMINATION_DECLINED,
    NOMINATION_SUPERSEDED, NOMINATION_WITHDRAWN,
)

# -- task ---------------------------------------------------------------------
TASK_PENDING = "pending"
TASK_COMPLETED = "completed"
TASK_CANCELLED = "cancelled"

#: Task kinds, each mapping to one state machine edge.
KIND_SUBSTITUTE_RESPONSE = "substitute_response"
KIND_UNIT_HEAD_DECISION = "unit_head_decision"
KIND_ESTABLISHMENT_ROUTING = "establishment_routing"
KIND_FINAL_SANCTION = "final_sanction"
KIND_DIRECTOR_SELF_SANCTION = "director_self_sanction"
KIND_CANCELLATION_UNIT_HEAD = "cancellation_unit_head"
KIND_CANCELLATION_ESTABLISHMENT = "cancellation_establishment"
KIND_CANCELLATION_FINAL = "cancellation_final"
KIND_EXTENSION_UNIT_HEAD = "extension_unit_head"
KIND_EXTENSION_ESTABLISHMENT = "extension_establishment"
KIND_EXTENSION_FINAL = "extension_final"
KIND_RESUMPTION_REVIEW = "resumption_review"

TASK_KINDS: tuple[str, ...] = (
    KIND_SUBSTITUTE_RESPONSE, KIND_UNIT_HEAD_DECISION, KIND_ESTABLISHMENT_ROUTING,
    KIND_FINAL_SANCTION, KIND_DIRECTOR_SELF_SANCTION, KIND_CANCELLATION_UNIT_HEAD,
    KIND_CANCELLATION_ESTABLISHMENT, KIND_CANCELLATION_FINAL,
    KIND_EXTENSION_UNIT_HEAD, KIND_EXTENSION_ESTABLISHMENT, KIND_EXTENSION_FINAL,
    KIND_RESUMPTION_REVIEW,
)


class LeaveRequest(UserScopedModel, TimeStampedModel):
    """One leave application, from draft to a terminal outcome (CW-EL-01)."""
    status = models.CharField(max_length=48, choices=[(s, s) for s in sm.LEAVE_STATES],
                              default=sm.DRAFT, db_index=True)

    category = models.CharField(max_length=8,
                                choices=[(c, c) for c in cat.CATEGORIES], db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField()
    requested_days = models.DecimalField(max_digits=8, decimal_places=2,
                                         validators=[MinValueValidator(Decimal("0.01"))])

    half_day = models.BooleanField(default=False)
    half = models.CharField(max_length=16, blank=True, default="",
                            choices=[(h, h) for h in cat.HALVES])
    purpose = models.CharField(max_length=500)

    #: BR-EL-013: Station Leave lives inside this application, not beside it.
    station_leave_required = models.BooleanField(default=False)
    station_leave_details = models.CharField(max_length=500, blank=True, default="")

    #: Frozen at submission, so a later policy change cannot rewrite history.
    substitute_required = models.BooleanField(default=False)

    kind = models.CharField(max_length=16, db_index=True)
    department = models.CharField(max_length=80, blank=True, default="")
    org_unit = models.ForeignKey("leave.OrganizationalUnit",
                                 on_delete=models.PROTECT, null=True, blank=True,
                                 related_name="leave_requests")

    #: BR-EL-017 only: a recommendation, which is not a rejection (BR-EL-017).
    unit_head_recommendation = models.CharField(
        max_length=20, blank=True, default="",
        choices=[("", ""), (RECOMMENDED, RECOMMENDED),
                 (NOT_RECOMMENDED, NOT_RECOMMENDED)])

    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True, default="")

    #: BR-EL-009: medical evidence may be required where applicable.
    medical_evidence_reference = models.CharField(max_length=300, blank=True,
                                                  default="")
    #: BR-EL-029: sanction evidence for an offline-authorised entry.
    offline_sanction_reference = models.CharField(max_length=300, blank=True,
                                                  default="")
    source = models.CharField(max_length=24,
                              choices=[(SELF_SERVICE, SELF_SERVICE),
                                       (OFFLINE_SANCTIONED, OFFLINE_SANCTIONED)],
                              default=SELF_SERVICE)

    class Meta:
        ordering = ("-id",)
        indexes = [
            models.Index(fields=("user_id", "status")),
            models.Index(fields=("category", "start_date")),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="leave_request_dates_ordered"),
            models.CheckConstraint(condition=~models.Q(half=True)
                                   | models.Q(half__in=cat.HALVES),
                                   name="leave_request_half_day_has_half"),
            models.CheckConstraint(condition=models.Q(requested_days__gt=0),
                                   name="leave_request_days_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.category} {self.start_date}..{self.end_date}"

    @property
    def year(self) -> int:
        return self.start_date.year


class SubstituteNomination(TimeStampedModel):
    """One nominated substitute and their answer (BR-EL-014, BR-EL-015)."""
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                      related_name="nominations")
    #: Set only when the coverage is for an extension rather than the leave itself.
    extension_request_id = models.IntegerField(null=True, blank=True, db_index=True)

    nominee_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=16,
                              choices=[(s, s) for s in NOMINATION_STATUSES],
                              default=NOMINATION_PENDING, db_index=True)
    period_start = models.DateField()
    period_end = models.DateField()
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-id",)
        constraints = [
            models.CheckConstraint(condition=models.Q(period_end__gte=models.F("period_start")),
                                   name="leave_nomination_period_ordered"),
            models.UniqueConstraint(
                fields=("leave_request", "extension_request_id"),
                condition=models.Q(status="pending"),
                name="leave_one_pending_nomination_per_request"),
        ]

    def __str__(self) -> str:
        return f"{self.leave_request_id}:{self.nominee_user_id}:{self.status}"


class ApprovalTask(TimeStampedModel):
    """An outstanding action, and the SLA clock that runs while it waits.

    `subject_type`/`subject_id` name the workflow object the task belongs to
    without four nullable foreign keys; `leave_request` is always set so every
    scoping query has one indexed path.
    """
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                      related_name="tasks")
    subject_type = models.CharField(max_length=16,
                                    choices=[(w, w) for w in
                                             (sm.NEW_LEAVE, sm.CANCELLATION,
                                              sm.EXTENSION, sm.RESUMPTION)])
    subject_id = models.IntegerField(db_index=True)
    kind = models.CharField(max_length=48, choices=[(k, k) for k in TASK_KINDS])

    assignee_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=[(TASK_PENDING, TASK_PENDING),
                                                      (TASK_COMPLETED, TASK_COMPLETED),
                                                      (TASK_CANCELLED, TASK_CANCELLED)],
                              default=TASK_PENDING, db_index=True)
    assigned_at = models.DateTimeField(db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    #: BR-EL-032/033: the clock a still-pending task is measured against.
    reminder_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    escalation_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    #: Where SLA escalation moved responsibility, for the audit trail (XTP-EL-01).
    escalated_to_user_id = models.IntegerField(null=True, blank=True)

    outcome = models.CharField(max_length=24, blank=True, default="")
    note = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ("-id",)
        indexes = [models.Index(fields=("status", "reminder_due_at")),
                   models.Index(fields=("status", "escalation_due_at"))]
        constraints = [
            models.UniqueConstraint(
                fields=("subject_type", "subject_id", "kind"),
                condition=models.Q(status="pending"),
                name="leave_one_pending_task_per_kind"),
        ]

    def __str__(self) -> str:
        return f"{self.subject_type}:{self.subject_id}:{self.kind}:{self.status}"