"""The leave request, its append-only audit trail and its substitute nominees.

Institute people are referenced by plain `user_id` integers, never foreign keys:
there is no user table in this database.
"""

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain import state_machine as sm


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """One application, of one of the three kinds CW-EL-01 to CW-EL-03 cover."""

    KINDS = [("new", "New leave"), ("cancellation", "Cancellation"),
             ("extension", "Extension")]
    HALVES = [("", "Full day"), ("first_half", "First half"),
              ("second_half", "Second half")]
    RECOMMENDATIONS = [("recommended", "Recommended"),
                       ("not_recommended", "Not recommended")]

    kind = models.CharField(max_length=16, choices=KINDS, default="new")
    category = models.CharField(max_length=4)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=12, choices=HALVES, blank=True)
    purpose = models.CharField(max_length=300)
    status = models.CharField(max_length=40, choices=[(s, s) for s in sm.STATUSES],
                              default=sm.DRAFT)

    days_requested = models.DecimalField(max_digits=6, decimal_places=2,
                                         default=0)
    days_approved = models.DecimalField(max_digits=6, decimal_places=2,
                                        default=0)

    #: The applicant's acting role at submission: the only place BR-EL-020 can
    #: be decided from, because designation lives in the IAM and not locally.
    applicant_role = models.CharField(max_length=64, blank=True)
    applicant_is_faculty = models.BooleanField(default=False)

    #: BR-EL-013: Station Leave lives inside this application, never beside it.
    station_leave_required = models.BooleanField(default=False)
    station_leave_place = models.CharField(max_length=120, blank=True)
    station_leave_start = models.DateField(null=True, blank=True)
    station_leave_end = models.DateField(null=True, blank=True)

    #: BR-EL-014: set at submission from the current configured policy.
    substitute_required = models.BooleanField(default=False)
    evidence_note = models.CharField(max_length=300, blank=True)

    #: An extension or a cancellation hangs off the approved leave it changes.
    parent = models.ForeignKey("self", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="follow_ons")

    submitted_at = models.DateTimeField(null=True, blank=True)
    finalised_at = models.DateTimeField(null=True, blank=True)
    finalised_by_user_id = models.IntegerField(null=True, blank=True)
    final_decision_reason = models.CharField(max_length=300, blank=True)

    unit_head_recommendation = models.CharField(max_length=16,
                                                choices=RECOMMENDATIONS, blank=True)
    unit_head_recommendation_reason = models.CharField(max_length=300, blank=True)
    current_step_kind = models.CharField(max_length=20, blank=True)
    current_step_designation = models.CharField(max_length=64, blank=True)

    approved_days_posted = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_request"
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="leave_request_period_ordered"),
            models.CheckConstraint(condition=models.Q(days_approved__gte=0),
                                   name="leave_request_days_approved_positive"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_request_user_idx"),
            models.Index(fields=["status", "start_date"], name="leave_request_status_idx"),
            models.Index(fields=["current_step_kind", "status"],
                         name="leave_request_step_idx"),
        ]

    def __str__(self) -> str:
        return f"req#{self.pk} u{self.user_id} {self.category} {self.status}"


class LeaveRequestTransition(TimeStampedModel):
    """Append-only audit of every status change (BR-EL-035, BR-EL-036)."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                               related_name="transitions")
    from_status = models.CharField(max_length=40)
    to_status = models.CharField(max_length=40)
    event = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_kind = models.CharField(max_length=24, blank=True)
    actor_designation = models.CharField(max_length=64, blank=True)
    recommendation = models.CharField(max_length=16, blank=True)
    reason = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_request_transition"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["request", "id"], name="leave_transition_req_idx"),
        ]

    def __str__(self) -> str:
        return f"req#{self.request_id} {self.from_status}->{self.to_status}"


class SubstituteAssignment(TimeStampedModel):
    """One nominated substitute and their response (BR-EL-014, BR-EL-015)."""

    STATES = [("pending", "Pending"), ("accepted", "Accepted"),
              ("declined", "Declined"), ("closed", "Closed")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                               related_name="substitute_assignments")
    substitute_user_id = models.IntegerField(db_index=True)
    state = models.CharField(max_length=12, choices=STATES, default="pending")
    reason = models.CharField(max_length=300, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_substitute_assignment"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["substitute_user_id", "state"],
                         name="leave_substitute_holder_idx"),
        ]

    def __str__(self) -> str:
        return f"req#{self.request_id} u{self.substitute_user_id} {self.state}"
