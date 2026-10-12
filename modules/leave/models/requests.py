"""The leave request aggregate: the request itself, its audit trail, its
resumption, and the applicant's notifications.

One row serves all three intents (new / cancellation / extension) because
the workflow, SLA and audit are shared; `kind` says which. There is no
"draft" state — a request is born in its first workflow state (CFR-EL-003).
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain.states import STATUS_CHOICES


class LeaveRequest(UserScopedModel, TimeStampedModel):
    """One leave application, cancellation, extension or offline record.

    `user_id` is the applicant. People are referenced by plain integers
    throughout — there is no user table here (see docs/01 data ownership).
    """

    NEW = "new"
    CANCELLATION = "cancellation"
    EXTENSION = "extension"
    OFFLINE = "offline"
    KIND = [(NEW, "Leave application"), (CANCELLATION, "Cancellation"),
            (EXTENSION, "Extension"), (OFFLINE, "Offline record")]

    source = models.CharField(max_length=8, default="elm")
    kind = models.CharField(max_length=16, choices=KIND, default=NEW)
    category = models.CharField(max_length=8)          # domain.categories
    status = models.CharField(max_length=40, choices=STATUS_CHOICES)

    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=8, default="none")

    purpose = models.TextField(blank=True)
    evidence_note = models.TextField(blank=True)

    # Station leave (CFR-EL-015): captured inside the same application.
    station_leave = models.BooleanField(default=False)
    station_place = models.CharField(max_length=160, blank=True)
    station_reason = models.CharField(max_length=400, blank=True)

    chargeable_days = models.DecimalField(max_digits=6, decimal_places=2,
                                          default=0)
    year = models.PositiveSmallIntegerField(db_index=True)  # leave year

    # Cancellation/extension point at the original request.
    base_request = models.ForeignKey("self", null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name="derived_requests")

    # Substitute consent gate (BR-EL-014/015).
    substitute_user_id = models.IntegerField(null=True, blank=True,
                                             db_index=True)
    substitute_status = models.CharField(max_length=12, default="none")
    # none | pending | accepted | declined

    # Reviewer states, filled as the file passes each desk.
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    unit_head_outcome = models.CharField(max_length=20, blank=True)
    # approve | reject | recommended | not_recommended
    unit_head_at = models.DateTimeField(null=True, blank=True)
    unit_head_note = models.TextField(blank=True)

    establishment_user_id = models.IntegerField(null=True, blank=True)
    establishment_at = models.DateTimeField(null=True, blank=True)
    establishment_note = models.TextField(blank=True)

    authority_user_id = models.IntegerField(null=True, blank=True)
    is_director_self_sanction = models.BooleanField(default=False)

    decision = models.CharField(max_length=8, blank=True)   # approve | reject
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    # Offline records (BR-EL-029) carry their paper reference; EL-UC-006
    # references may be attached to any decision.
    sanction_reference = models.CharField(max_length=200, blank=True)

    # Open task for SLA (BR-EL-032/033); blank once the file moves on.
    task_class = models.CharField(max_length=32, blank=True)
    task_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    task_assigned_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    #: Set when a resumption review records the true last day (BR-EL-026).
    actual_end_date = models.DateField(null=True, blank=True)
    #: Free-text annotation for record maintenance (never the sanction path).
    admin_note = models.TextField(blank=True)

    class Meta:
        db_table = "leave_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="leave_request_interval_valid"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["status", "task_class"]),
            models.Index(fields=["category", "year"]),
        ]

    def __str__(self) -> str:
        return f"{self.category.upper()} {self.start_date}…{self.end_date}"

    @property
    def is_pending(self) -> bool:
        from modules.leave.domain.states import PENDING
        return self.status in PENDING


class LeaveRequestEvent(models.Model):
    """Append-only audit line (CFR-EL-003.6, BR-EL-035)."""

    SUBMITTED = "submitted"
    STATUS_CHANGE = "status_change"
    SUBSTITUTE_RESPONSE = "substitute_response"
    ASSIGNMENT = "assignment"
    DECISION = "decision"
    BALANCE_EFFECT = "balance_effect"
    SLA_REMINDER = "sla_reminder"
    SLA_ESCALATION = "sla_escalation"
    NOTE = "note"

    KIND = [(SUBMITTED, "Submitted"), (STATUS_CHANGE, "Status change"),
            (SUBSTITUTE_RESPONSE, "Substitute response"),
            (ASSIGNMENT, "Task assignment"), (DECISION, "Decision"),
            (BALANCE_EFFECT, "Balance effect"), (SLA_REMINDER, "SLA reminder"),
            (SLA_ESCALATION, "SLA escalation"), (NOTE, "Note")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="events")
    from_status = models.CharField(max_length=40, blank=True)
    to_status = models.CharField(max_length=40, blank=True)
    kind = models.CharField(max_length=24, choices=KIND)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=120, blank=True)
    note = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "leave_request_event"
        ordering = ["at"]

    def __str__(self) -> str:
        return f"{self.request_id}: {self.kind} @{self.at:%Y-%m-%d %H:%M}"


class LeaveResumption(TimeStampedModel):
    """BR-EL-026 / CFR-EL-019: employee reports actual return; the authority
    reviews and the balance follows the actual period, not the approved one."""

    PENDING = "pending_review"
    NO_ADJUSTMENT = "reviewed_no_adjustment"
    EARLY = "reviewed_early"
    LATE = "reviewed_late"
    STATUS = [(PENDING, "Pending review"), (NO_ADJUSTMENT, "Reviewed: as is"),
              (EARLY, "Reviewed: returned early"),
              (LATE, "Reviewed: returned late")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="resumptions")
    actual_date = models.DateField()
    details = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=STATUS, default=PENDING)
    #: Snapshot so a review can compare approved vs actual.
    approved_end_date = models.DateField()
    adjustment_days = models.DecimalField(max_digits=6, decimal_places=2,
                                          default=0)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        db_table = "leave_resumption"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"resumption of #{self.request_id}: {self.actual_date}"


class LeaveNotification(TimeStampedModel):
    """In-app notification written by the ELM itself (BR-EL-035); the
    outbox/email transport is out of scope for this baseline."""

    user_id = models.IntegerField(db_index=True)          # recipient
    request = models.ForeignKey(LeaveRequest, null=True, blank=True,
                                on_delete=models.CASCADE,
                                related_name="notifications")
    kind = models.CharField(max_length=32)                # assigned | ...
    message = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_notification"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"#{self.user_id} {self.kind}"
