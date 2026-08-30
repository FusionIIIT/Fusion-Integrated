"""The audit trail, and the hierarchy that routes a request.

Every state change is appended here. Together with the ledger this answers the
two questions asked years later about any leave: what happened to it, and who
decided.
"""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.domain.state_machine import Actor, Event
from modules.leave.models.policy import CATEGORY_CHOICES
from modules.leave.models.request import STATE_CHOICES, LeaveRequest


class RequestTransition(TimeStampedModel):
    """One movement of a request through the workflow. Never edited."""

    request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="transitions"
    )
    from_state = models.CharField(max_length=40, choices=STATE_CHOICES)
    to_state = models.CharField(max_length=40, choices=STATE_CHOICES)
    event = models.CharField(max_length=32, choices=[(e.value, e.value) for e in Event])
    actor_role = models.CharField(max_length=32, choices=[(a.value, a.value) for a in Actor])
    actor_user_id = models.IntegerField(null=True, blank=True)
    remark = models.TextField(blank=True)
    #: The workflow row this move came from, so the trail cites the document.
    workflow_ref = models.CharField(max_length=32, blank=True)

    class Meta:
        db_table = "leave_request_transition"
        ordering = ["request_id", "id"]
        indexes = [
            models.Index(fields=["request", "id"], name="leave_transition_trail_idx"),
            models.Index(fields=["actor_user_id"], name="leave_transition_actor_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.request_id}: {self.from_state} -> {self.to_state}"


class AuthorityRule(TimeStampedModel):
    """BR-EL-019. Who reviews and who sanctions, as configuration.

    The path is resolved from the applicant's unit, their designation and the
    leave category. Naming the offices in code would mean a reorganisation
    becomes a deployment; here it is a row.
    """

    policy_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    #: Empty matches any unit or any designation, so a general rule needs
    #: one row. Empty rather than null: a null defeats the unique constraint
    #: below on Postgres, and two conflicting general rules could then coexist.
    unit = models.CharField(max_length=80, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    applies_to_faculty = models.BooleanField(null=True, blank=True)

    #: Whether the establishment step sits between recommendation and sanction.
    establishment_step = models.BooleanField(default=False)
    #: The designation that finally sanctions. Empty means the unit head is final.
    sanctioning_designation = models.CharField(max_length=120, blank=True)
    #: BR-EL-020. The holder sanctions their own leave in this configuration.
    self_sanction = models.BooleanField(default=False)
    #: Higher number wins where several rows match.
    specificity = models.IntegerField(default=0)

    class Meta:
        db_table = "leave_authority_rule"
        ordering = ["-specificity", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["policy_id", "category", "unit", "designation"],
                name="leave_authority_unique_match",
            ),
        ]
        indexes = [
            models.Index(
                fields=["policy_id", "category"], name="leave_authority_lookup_idx"
            ),
        ]

    def __str__(self) -> str:
        target = self.sanctioning_designation or "unit head"
        return f"{self.category} in {self.unit or 'any unit'} -> {target}"


class SlaRule(TimeStampedModel):
    """BR-EL-032, BR-EL-033. How long a state may sit before someone is told.

    Thresholds hang off the policy version, so tightening them is a new policy
    rather than a deployment, and a request decided last year can still be
    judged against the deadline that applied to it.
    """

    policy_id = models.IntegerField(db_index=True)
    state = models.CharField(max_length=40, choices=STATE_CHOICES)
    remind_after_hours = models.PositiveIntegerField()
    escalate_after_hours = models.PositiveIntegerField()
    #: Who hears about it when the deadline passes. Empty escalates to whoever
    #: the authority configuration names as the next step.
    escalate_to_designation = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "leave_sla_rule"
        ordering = ["policy_id", "state"]
        constraints = [
            models.UniqueConstraint(
                fields=["policy_id", "state"], name="leave_sla_rule_one_per_state"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    escalate_after_hours__gt=models.F("remind_after_hours")
                ),
                name="leave_sla_escalation_after_reminder",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.state}: remind {self.remind_after_hours}h"


class SlaClock(TimeStampedModel):
    """BR-EL-032, BR-EL-033. What is owed by whom, and by when."""

    request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="sla_clocks"
    )
    state = models.CharField(max_length=40, choices=STATE_CHOICES)
    assigned_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    started_at = models.DateTimeField()
    remind_at = models.DateTimeField(null=True, blank=True)
    escalate_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_sla_clock"
        indexes = [
            models.Index(fields=["stopped_at", "remind_at"], name="leave_sla_due_idx"),
            models.Index(fields=["stopped_at", "escalate_at"], name="leave_sla_escal_idx"),
        ]

    def __str__(self) -> str:
        return f"SLA on {self.request_id} in {self.state}"
