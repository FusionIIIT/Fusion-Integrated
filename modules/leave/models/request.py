"""The leave-request aggregate and its sibling records (blueprint Step 3.2).

The ``state`` vocabularies mirror the transition tables in
``modules/leave/domain/state_machine.py`` (WF v1.6, CW-EL-01..04); that module
is the authority for which moves are legal. The choices are repeated here
rather than imported, following the placement module's convention of keeping
the DB column's vocabulary explicit.

No row is ever edited in place once pending (BR-EL-034, CFR-EL-017): that is a
service-layer guard (PY), not a DB constraint, and is not enforced here.
"""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.models.policy import LEAVE_TYPE_CHOICES

#: CW-EL-01 request states (WF v1.6 STT).
LEAVE_REQUEST_STATES = [
    ("draft", "Draft / not submitted"),
    ("awaiting_substitute_response", "Awaiting substitute response"),
    ("applicant_action_required", "Applicant action required"),
    ("awaiting_unit_head_review", "Awaiting unit head review"),
    ("awaiting_establishment_routing", "Awaiting establishment routing"),
    ("awaiting_final_sanction_decision", "Awaiting final sanction decision"),
    ("awaiting_director_self_sanction", "Awaiting director self-sanction"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("withdrawn", "Withdrawn"),
]

HALF_DAY_CHOICES = [("first", "First half"), ("second", "Second half")]


class LeaveRequest(TimeStampedModel):
    """A leave application — EXPLICIT fields; PROVISIONAL window constraint.

    ``half_day`` is null for a whole-day request and set only for a half-day CL
    request (BR-EL-010). Station Leave is coupled in this same record, not a
    separate process (BR-EL-013).
    """

    applicant_user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=8, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=6, choices=HALF_DAY_CHOICES,
                               blank=True)
    requested_days = models.DecimalField(max_digits=6, decimal_places=2)
    purpose = models.TextField(blank=True)

    station_leave_flag = models.BooleanField(default=False)
    station_leave_details = models.TextField(blank=True)

    state = models.CharField(max_length=40, choices=LEAVE_REQUEST_STATES,
                             default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        constraints = [
            # PROVISIONAL: the window must not run backwards. Whether the
            # boundary semantics are inclusive is not settled (see #6).
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="leave_request_window_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["applicant_user_id", "state"],
                         name="leave_request_applicant_idx"),
            models.Index(fields=["state"], name="leave_request_state_idx"),
        ]

    def __str__(self) -> str:
        return f"req#{self.pk} u{self.applicant_user_id} {self.leave_type} {self.state}"


class LeaveRequestDay(TimeStampedModel):
    """Materialised chargeable day — PROVISIONAL (counting/overlap support)."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="days")
    date = models.DateField()
    #: Blank means the whole day is charged; set for a half-day CL (BR-EL-010).
    half = models.CharField(max_length=6, choices=HALF_DAY_CHOICES,
                            blank=True)

    class Meta:
        db_table = "leave_request_day"
        constraints = [
            models.UniqueConstraint(fields=["request", "date", "half"],
                                    name="leave_request_day_unique"),
        ]
        indexes = [models.Index(fields=["date"],
                                name="leave_request_day_date_idx")]

    def __str__(self) -> str:
        return f"req#{self.request_id} {self.date} {self.half or 'full'}"


class SubstituteAssignment(TimeStampedModel):
    """A nominated substitute — EXPLICIT rule (BR-EL-014); PROVISIONAL shape.

    PY invariants (nominee≠applicant, no overlapping leave) live in
    ``domain/substitute.py``; the DB backstop is at most one accepted nominee
    per request.
    """

    STATES = [
        ("awaiting", "Awaiting response"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="substitute_assignments")
    nominee_user_id = models.IntegerField(db_index=True)
    responsibility_start = models.DateField()
    responsibility_end = models.DateField()
    state = models.CharField(max_length=10, choices=STATES, default="awaiting")
    rejection_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "leave_substitute_assignment"
        constraints = [
            # PROVISIONAL (blueprint §3.2): the responsibility window's
            # semantics are unsettled, so only its ordering is enforced here —
            # mirroring ``leave_request_window_valid`` and
            # ``leave_offline_window_valid``.
            models.CheckConstraint(
                condition=models.Q(
                    responsibility_end__gte=models.F("responsibility_start")),
                name="leave_substitute_window_valid",
            ),
            models.UniqueConstraint(
                fields=["request"], condition=models.Q(state="accepted"),
                name="leave_one_accepted_substitute",
            ),
        ]
        indexes = [models.Index(fields=["nominee_user_id", "state"],
                                name="leave_substitute_nominee_idx")]

    def __str__(self) -> str:
        return f"sub u{self.nominee_user_id} {self.state}"


class ApprovalTask(TimeStampedModel):
    """A pending approval task — CONVENTION (one open task per step).

    The task's subject is one of the request, a cancellation or an extension;
    exactly one must be set. The partial uniques make a duplicate open task for
    the same subject and step impossible even if a service double-fires.
    """

    STATES = [("open", "Open"), ("completed", "Completed")]

    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                      related_name="tasks", null=True, blank=True)
    cancellation = models.ForeignKey("LeaveCancellation", on_delete=models.CASCADE,
                                     related_name="tasks", null=True, blank=True)
    extension = models.ForeignKey("LeaveExtension", on_delete=models.CASCADE,
                                  related_name="tasks", null=True, blank=True)

    step_order = models.PositiveSmallIntegerField()
    assigned_designation = models.CharField(max_length=120, blank=True)
    assigned_user_id = models.IntegerField(null=True, blank=True)
    state = models.CharField(max_length=10, choices=STATES, default="open")
    due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_approval_task"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(leave_request__isnull=False,
                             cancellation__isnull=True, extension__isnull=True)
                    | models.Q(leave_request__isnull=True,
                               cancellation__isnull=False, extension__isnull=True)
                    | models.Q(leave_request__isnull=True,
                               cancellation__isnull=True, extension__isnull=False)
                ),
                name="leave_task_exactly_one_subject",
            ),
            models.UniqueConstraint(
                fields=["leave_request", "step_order"],
                condition=models.Q(state="open") & models.Q(leave_request__isnull=False),
                name="leave_task_open_per_request_step",
            ),
            models.UniqueConstraint(
                fields=["cancellation", "step_order"],
                condition=models.Q(state="open") & models.Q(cancellation__isnull=False),
                name="leave_task_open_per_cancellation_step",
            ),
            models.UniqueConstraint(
                fields=["extension", "step_order"],
                condition=models.Q(state="open") & models.Q(extension__isnull=False),
                name="leave_task_open_per_extension_step",
            ),
        ]
        indexes = [
            models.Index(fields=["state", "due_at"], name="leave_task_open_idx"),
            models.Index(fields=["assigned_user_id", "state"],
                         name="leave_task_assignee_idx"),
        ]

    def __str__(self) -> str:
        return f"task step={self.step_order} {self.state}"


class LeaveDecision(models.Model):
    """An append-only decision record — EXPLICIT (BR-EL-016..020)."""

    DECISIONS = [
        ("approve", "Approve"),
        ("reject", "Reject"),
        ("recommend", "Recommended"),
        ("not_recommend", "Not recommended"),
    ]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="decisions")
    actor_user_id = models.IntegerField(null=True, blank=True)
    decision = models.CharField(max_length=16, choices=DECISIONS)
    decided_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_decision"
        indexes = [models.Index(fields=["request", "decided_at"],
                                name="leave_decision_request_idx")]

    def __str__(self) -> str:
        return f"decision {self.decision} on req#{self.request_id}"


class LeaveCancellation(TimeStampedModel):
    """A cancellation of approved leave — PROVISIONAL shape (BR-EL-023/024).

    States are the CW-EL-02 pending/outcome states; the service creates the
    record in the STT's entry pending state (no model default is imposed).
    """

    STATES = [
        ("cancellation_pending_unit_head", "Cancellation pending — unit head"),
        ("cancellation_pending_establishment", "Cancellation pending — establishment"),
        ("cancellation_pending_final", "Cancellation pending — final decision"),
        ("cancelled", "Cancelled"),
        ("approved_unchanged", "Approved / unchanged"),
    ]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="cancellations")
    state = models.CharField(max_length=40, choices=STATES)
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_cancellation"
        indexes = [models.Index(fields=["request", "state"],
                                name="leave_cancellation_request_idx")]

    def __str__(self) -> str:
        return f"cancel#{self.pk} {self.state}"


class LeaveExtension(TimeStampedModel):
    """An extension of ongoing EL/COL/VL — PROVISIONAL shape (BR-EL-025)."""

    STATES = [
        ("awaiting_extension_substitute_response", "Awaiting extension substitute response"),
        ("extension_applicant_action_required", "Extension applicant action required"),
        ("awaiting_extension_unit_head_review", "Awaiting extension unit head review"),
        ("extension_pending_establishment", "Extension pending — establishment"),
        ("extension_pending_final", "Extension pending — final decision"),
        ("extended_incremental_posted", "Extended — incremental period posted"),
        ("original_ongoing_unchanged", "Original ongoing leave unchanged"),
        ("extension_withdrawn_original_unchanged", "Extension withdrawn — original unchanged"),
    ]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="extensions")
    new_end_date = models.DateField()
    #: Service-set: the STT branches to a substitute response OR straight to
    #: unit-head review, so no single starting value is imposed here.
    state = models.CharField(max_length=48, choices=STATES)
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_extension"
        indexes = [models.Index(fields=["request", "state"],
                                name="leave_extension_request_idx")]

    def __str__(self) -> str:
        return f"ext#{self.pk} {self.state}"


class ResumptionReview(TimeStampedModel):
    """A resumption-of-duty review — PROVISIONAL shape (BR-EL-027/028).

    ``actual_resumption_date`` is compared with the request's approved end date
    by ``domain/resumption.py``. The early/late synchronization of attendance
    is NOT implemented: the attendance contract is missing (§3.8 #3).
    """

    STATES = [
        ("resumption_review_pending", "Resumption review pending"),
        ("no_adjustment", "Reviewed — no adjustment"),
        ("early_return_synchronized", "Reviewed — early return synchronized"),
        ("late_return_synchronized", "Reviewed — late return synchronized"),
    ]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="resumptions")
    actual_resumption_date = models.DateField()
    state = models.CharField(max_length=32, choices=STATES)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_resumption_review"
        indexes = [models.Index(fields=["request", "state"],
                                name="leave_resumption_request_idx")]

    def __str__(self) -> str:
        return f"resumption#{self.pk} {self.state}"
