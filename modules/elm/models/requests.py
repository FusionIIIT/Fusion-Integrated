"""Leave requests and their trail (CW-EL-01..04)."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.elm.domain import policy
from modules.elm.domain import state_machine as sm

CATEGORY_CHOICES = [(c, c) for c in policy.CATEGORIES]
STATE_CHOICES = [(s, s.replace("_", " ").title()) for s in (
    sm.AWAITING_SUBSTITUTE, sm.APPLICANT_ACTION, sm.AWAITING_UNIT_HEAD,
    sm.AWAITING_ESTABLISHMENT, sm.AWAITING_SANCTION, sm.AWAITING_DIRECTOR,
    sm.AWAITING_RESUMPTION_REVIEW, sm.APPROVED, sm.REJECTED, sm.WITHDRAWN,
    sm.CANCELLED, sm.RESUMPTION_REVIEWED)]


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """`user_id` is the applicant. Never edited after submission (BR-EL-034)."""

    LEAVE, CANCELLATION, EXTENSION, RESUMPTION = (
        "leave", "cancellation", "extension", "resumption")
    KIND = [(LEAVE, "Leave"), (CANCELLATION, "Cancellation"),
            (EXTENSION, "Extension"), (RESUMPTION, "Resumption")]
    ONLINE, OFFLINE = "online", "offline"
    SOURCE = [(ONLINE, "Online"), (OFFLINE, "Offline-sanctioned")]
    RECOMMENDED, NOT_RECOMMENDED = "recommended", "not_recommended"
    RECOMMENDATION = [(RECOMMENDED, "Recommended"),
                      (NOT_RECOMMENDED, "Not Recommended")]

    kind = models.CharField(max_length=12, choices=KIND, default=LEAVE)
    source = models.CharField(max_length=8, choices=SOURCE, default=ONLINE)
    parent = models.ForeignKey("self", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="children")
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    applicant_kind = models.CharField(max_length=8)
    unit = models.CharField(max_length=80, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=6, blank=True)
    days = models.DecimalField(max_digits=6, decimal_places=1)
    purpose = models.TextField(blank=True)
    #: BR-EL-013: Station Leave lives inside the same application.
    station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=300, blank=True)
    substitute_id = models.IntegerField(null=True, blank=True, db_index=True)
    is_director_applicant = models.BooleanField(default=False)

    state = models.CharField(max_length=32, choices=STATE_CHOICES, db_index=True)
    recommendation = models.CharField(max_length=16, choices=RECOMMENDATION,
                                      blank=True)
    decided_by_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.CharField(max_length=500, blank=True)

    actual_resumption_date = models.DateField(null=True, blank=True)
    offline_reference = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=["user_id", "state"], name="elm_req_user_state_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")),
                                   name="elm_req_period_ordered"),
            models.CheckConstraint(condition=Q(days__gte=0), name="elm_req_days_nonneg"),
            models.CheckConstraint(
                condition=Q(substitute_id__isnull=True)
                | ~Q(substitute_id=models.F("user_id")),
                name="elm_req_substitute_not_applicant"),
            # One open cancellation/extension/resumption per original leave.
            models.UniqueConstraint(
                fields=["parent", "kind"],
                condition=Q(state__in=sorted(sm.PENDING
                                             | {sm.AWAITING_RESUMPTION_REVIEW})),
                name="elm_req_one_open_child"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.category} #{self.pk} ({self.state})"

    @property
    def active_step(self):
        """Reads the prefetched chain when there is one, so lists stay O(1)."""
        return next((s for s in self.steps.all()
                     if s.status == ApprovalStep.ACTIVE), None)

    @property
    def assignee_id(self) -> int | None:
        step = self.active_step
        return step.assignee_id if step else None


class ApprovalStep(TimeStampedModel):
    """One link of the route, resolved in full when the request is submitted."""

    WAITING, ACTIVE, DONE, DECLINED, CANCELLED = (
        "waiting", "active", "done", "declined", "cancelled")
    STATUS = [(s, s.title()) for s in (WAITING, ACTIVE, DONE, DECLINED, CANCELLED)]
    STAGE = [(s, s.replace("_", " ").title()) for s in (
        sm.SUBSTITUTE, sm.UNIT_HEAD, sm.ESTABLISHMENT, sm.AUTHORITY, sm.DIRECTOR)]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="steps")
    sequence = models.PositiveSmallIntegerField()
    stage = models.CharField(max_length=16, choices=STAGE)
    assignee_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS, default=WAITING)
    outcome = models.CharField(max_length=16, blank=True)
    remarks = models.CharField(max_length=500, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    acted_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_approval_step"
        ordering = ["sequence", "id"]
        indexes = [models.Index(fields=["assignee_id", "status"],
                                name="elm_step_queue_idx")]
        constraints = [models.UniqueConstraint(
            fields=["request"], condition=Q(status="active"),
            name="elm_step_one_active")]


class RequestEvent(TimeStampedModel):
    """Append-only audit trail: every move, by whom, in which role."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="events")
    actor_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=20)
    from_state = models.CharField(max_length=32, blank=True)
    to_state = models.CharField(max_length=32, blank=True)
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "elm_request_event"
        ordering = ["created_at", "id"]


class Notification(TimeStampedModel, UserScopedModel):
    """BR-EL-035 and final-decision notices; drained by the portal's bell later."""

    request = models.ForeignKey(LeaveRequest, null=True, blank=True,
                                on_delete=models.CASCADE,
                                related_name="notifications")
    message = models.CharField(max_length=300)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_notification"
        ordering = ["-created_at", "-id"]
