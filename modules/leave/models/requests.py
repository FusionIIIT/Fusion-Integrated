"""Leave requests, their substitutes, their tasks and their audit trail."""
from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.models.configuration import CATEGORY_CHOICES

PENDING_STATES = ("awaiting_substitute", "applicant_action_required", "awaiting_unit_head",
                  "awaiting_establishment", "awaiting_sanction", "awaiting_director")


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """`user_id` is the applicant; a cancellation or extension points at its leave by `parent`."""

    KIND = [("new", "New leave"), ("cancellation", "Cancellation"), ("extension", "Extension")]
    STATUS = [
        ("draft", "Not yet submitted"),
        ("awaiting_substitute", "Awaiting substitute response"),
        ("applicant_action_required", "Applicant action required"),
        ("awaiting_unit_head", "Awaiting Unit Head review"),
        ("awaiting_establishment", "Awaiting Establishment routing"),
        ("awaiting_sanction", "Awaiting final sanction"),
        ("awaiting_director", "Awaiting Director self-sanction"),
        ("approved", "Approved"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]
    HALF = [("", "Full day(s)"), ("first", "First half"), ("second", "Second half")]
    SOURCE = [("online", "Applied in ELM"), ("offline", "Recorded from an offline sanction")]

    kind = models.CharField(max_length=14, choices=KIND, default="new")
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True,
                               related_name="children")
    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=6, choices=HALF, blank=True)
    days = models.DecimalField(max_digits=6, decimal_places=1)
    leave_year = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=28, choices=STATUS)

    purpose = models.TextField(blank=True)
    station_leave = models.BooleanField(default=False)
    station_from = models.DateField(null=True, blank=True)
    station_to = models.DateField(null=True, blank=True)
    station_address = models.CharField(max_length=300, blank=True)
    evidence_reference = models.CharField(max_length=500, blank=True)

    #: Frozen at submission: routing reads these, never a later edit to the person.
    applicant_kind = models.CharField(max_length=10)
    applicant_department = models.CharField(max_length=100, blank=True)
    applicant_roles = models.JSONField(default=list)
    is_director_applicant = models.BooleanField(default=False)

    unit_head_outcome = models.CharField(max_length=16, blank=True)
    decision = models.CharField(max_length=10, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_role = models.CharField(max_length=155, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.CharField(max_length=500, blank=True)

    source = models.CharField(max_length=8, choices=SOURCE, default="online")
    offline_reference = models.CharField(max_length=200, blank=True)
    offline_reason = models.CharField(max_length=300, blank=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F("start_date")),
                                   name="leave_request_ordered"),
            models.CheckConstraint(condition=Q(half="") | Q(start_date=F("end_date")),
                                   name="leave_request_half_single_day"),
            models.CheckConstraint(condition=Q(kind="new") | Q(parent__isnull=False),
                                   name="leave_request_child_has_parent"),
            models.UniqueConstraint(fields=["parent", "kind"],
                                    condition=Q(status__in=PENDING_STATES),
                                    name="leave_request_one_pending_child"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_request_user_idx"),
            models.Index(fields=["user_id", "start_date", "end_date"],
                         name="leave_request_period_idx"),
            models.Index(fields=["status", "kind"], name="leave_request_status_idx"),
        ]

    def __str__(self) -> str:
        return f"leave#{self.pk} {self.kind} {self.category} {self.status}"


class Substitution(TimeStampedModel):
    PENDING, ACCEPTED, DECLINED, VOID = "pending", "accepted", "declined", "void"
    STATUS = [(PENDING, "Pending"), (ACCEPTED, "Accepted"), (DECLINED, "Declined"),
              (VOID, "Void")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="substitutions")
    substitute_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS, default=PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)
    remarks = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_substitution"
        constraints = [models.UniqueConstraint(fields=["request"], condition=Q(status="pending"),
                                               name="leave_substitution_one_pending")]

    def __str__(self) -> str:
        return f"sub#{self.pk} u{self.substitute_user_id} {self.status}"


class Task(models.Model):
    """The actionable work item behind a waiting state; assigned to a person or to a designation."""

    OPEN, DONE, CANCELLED = "open", "done", "cancelled"
    STATUS = [(OPEN, "Open"), (DONE, "Done"), (CANCELLED, "Cancelled")]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="tasks")
    step = models.CharField(max_length=24)
    assignee_user_id = models.IntegerField(null=True, blank=True)
    assignee_designation = models.CharField(max_length=155, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default=OPEN)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by_user_id = models.IntegerField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_task"
        constraints = [
            models.UniqueConstraint(fields=["request"], condition=Q(status="open"),
                                    name="leave_task_one_open"),
            models.CheckConstraint(
                condition=Q(assignee_user_id__isnull=False) | ~Q(assignee_designation=""),
                name="leave_task_has_assignee"),
        ]
        indexes = [
            models.Index(fields=["status", "assignee_designation"], name="leave_task_role_idx"),
            models.Index(fields=["status", "assignee_user_id"], name="leave_task_user_idx"),
        ]

    def __str__(self) -> str:
        return f"task#{self.pk} {self.step} {self.status}"


class RequestEvent(models.Model):
    """Append-only: every movement, who made it, acting as what."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="events")
    event = models.CharField(max_length=32)
    from_status = models.CharField(max_length=28, blank=True)
    to_status = models.CharField(max_length=28, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=155, blank=True)
    outcome = models.CharField(max_length=24, blank=True)
    remarks = models.CharField(max_length=500, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_request_event"
        ordering = ["at", "id"]
        indexes = [models.Index(fields=["request", "at"], name="leave_event_request_idx")]

    def __str__(self) -> str:
        return f"#{self.request_id} {self.event}"


class Resumption(TimeStampedModel):
    PENDING = "review_pending"
    STATUS = [("review_pending", "Review pending"), ("reviewed_normal", "Reviewed — no change"),
              ("reviewed_early", "Reviewed — early return synchronised"),
              ("reviewed_late", "Reviewed — late return synchronised")]

    leave = models.OneToOneField(LeaveRequest, on_delete=models.CASCADE,
                                 related_name="resumption")
    resumption_date = models.DateField()
    details = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default=PENDING)
    reviewer_designation = models.CharField(max_length=155)
    outcome = models.CharField(max_length=8, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    adjustment_days = models.DecimalField(max_digits=6, decimal_places=1, null=True,
                                          blank=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_remarks = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "leave_resumption"

    def __str__(self) -> str:
        return f"resumption #{self.leave_id} {self.status}"
