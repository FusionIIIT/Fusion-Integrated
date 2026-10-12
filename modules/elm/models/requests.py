"""The leave request aggregate and its satellite records.

Institute people are referenced by plain `user_id` integers, never foreign keys —
there is no user table in this database (ADR-0013).
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """One application: a new leave, a cancellation, or an extension."""

    KINDS = [("new", "New leave"), ("cancellation", "Cancellation"),
             ("extension", "Extension")]
    HALVES = [("first", "First half"), ("second", "Second half")]
    STATUS = [(s, s.replace("_", " ").title()) for s in (
        "draft", "awaiting_substitute", "applicant_action_required",
        "awaiting_unit_head", "awaiting_establishment",
        "awaiting_final_sanction", "awaiting_director_sanction",
        "approved", "rejected", "withdrawn", "cancelled",
    )]

    kind = models.CharField(max_length=12, choices=KINDS, default="new")
    category = models.CharField(max_length=8, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=8, choices=HALVES, blank=True)
    days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    purpose = models.TextField(blank=True)

    # Station Leave is captured within the same application (BR-EL-013).
    station_leave = models.BooleanField(default=False)
    station_place = models.CharField(max_length=160, blank=True)
    station_contact = models.CharField(max_length=40, blank=True)

    status = models.CharField(max_length=32, choices=STATUS, default="draft")
    substitute_user_id = models.IntegerField(null=True, blank=True)
    original = models.ForeignKey("self", null=True, blank=True,
                                 on_delete=models.PROTECT,
                                 related_name="derived_requests")
    #: Routing facts frozen at submission: applicant role, establishment step.
    route = models.JSONField(default=dict, blank=True)

    final_decision = models.CharField(max_length=16, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=300, blank=True)

    department = models.CharField(max_length=80, blank=True)

    # Offline recording (BR-EL-029): already sanctioned on paper.
    is_offline = models.BooleanField(default=False)
    sanction_reference = models.CharField(max_length=160, blank=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_request_user_idx"),
            models.Index(fields=["status", "-created_at"],
                         name="elm_request_status_idx"),
            models.Index(fields=["category"], name="elm_request_cat_idx"),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"req#{self.pk} u{self.user_id} {self.category} {self.status}"

    @property
    def is_pending(self) -> bool:
        return self.status not in ("approved", "rejected", "withdrawn",
                                   "cancelled")


class LeaveRequestEvent(TimeStampedModel):
    """Append-only audit of every status change."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="events")
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=24, blank=True)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_request_event"
        ordering = ["at", "id"]

    def __str__(self) -> str:
        return f"req#{self.request_id} {self.from_status}->{self.to_status}"


class SubstituteAssignment(TimeStampedModel):
    """A substitute's responsibility window and response (BR-EL-014/015)."""

    STATUS = [("pending", "Pending"), ("accepted", "Accepted"),
              ("declined", "Declined")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="assignments")
    substitute_user_id = models.IntegerField(db_index=True)
    responsibility_start = models.DateField()
    responsibility_end = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    decline_reason = models.CharField(max_length=300, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    nominated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_substitute_assignment"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"sub#{self.pk} req#{self.request_id} {self.status}"


class WorkflowTask(TimeStampedModel):
    """An actionable step awaiting somebody (BR-EL-030/032/033/035)."""

    STATUS = [("pending", "Pending"), ("done", "Done"), ("skipped", "Skipped")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="tasks")
    task_type = models.CharField(max_length=24, db_index=True)
    role = models.CharField(max_length=24, blank=True)
    assigned_to_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    decision = models.CharField(max_length=20, blank=True)
    acted_by_user_id = models.IntegerField(null=True, blank=True)
    acted_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_workflow_task"
        indexes = [
            models.Index(fields=["status", "task_type"],
                         name="elm_task_status_idx"),
            models.Index(fields=["assigned_to_user_id", "status"],
                         name="elm_task_assignee_idx"),
        ]
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"task#{self.pk} {self.task_type} {self.status}"


class SlaEvent(TimeStampedModel):
    """A reminder or escalation actually issued (BR-EL-031/032 logging)."""

    KINDS = [("reminder", "Reminder"), ("escalation", "Escalation")]

    task = models.ForeignKey(WorkflowTask, on_delete=models.CASCADE,
                             related_name="sla_events")
    kind = models.CharField(max_length=12, choices=KINDS)
    note = models.CharField(max_length=300, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_sla_event"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.kind} task#{self.task_id}"


class ResumptionRecord(TimeStampedModel):
    """Actual return-to-duty against an approved EL/COL/VL (BR-EL-027/028)."""

    STATUS = [("pending", "Pending"), ("reviewed", "Reviewed")]
    OUTCOMES = [("normal", "Normal"), ("early", "Early"), ("late", "Late")]

    request = models.OneToOneField(LeaveRequest, on_delete=models.CASCADE,
                                   related_name="resumption")
    user_id = models.IntegerField(db_index=True)
    actual_date = models.DateField()
    details = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    outcome = models.CharField(max_length=8, choices=OUTCOMES, blank=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    adjustment_note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "elm_resumption_record"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"resumption req#{self.request_id} {self.status}"
