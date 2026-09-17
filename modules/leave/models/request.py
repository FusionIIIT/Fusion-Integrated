"""The leave request itself, and what hangs off it."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain.counting import Half
from modules.leave.domain.state_machine import State
from modules.leave.models.policy import CATEGORY_CHOICES

STATE_CHOICES = [(s.value, s.value) for s in State]
HALF_CHOICES = [(h.value, h.value) for h in Half]


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """One application. Its state is whatever the workflow table last set."""

    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES, db_index=True)
    state = models.CharField(
        max_length=40, choices=STATE_CHOICES, default=State.DRAFT.value, db_index=True
    )
    starts_on = models.DateField()
    ends_on = models.DateField()
    #: BR-EL-010. Set only for a half-day casual leave, which is a single date.
    half = models.CharField(max_length=8, choices=HALF_CHOICES, blank=True)
    reason = models.TextField()
    #: BR-EL-001: the certificate or letter reference a category may demand.
    evidence_reference = models.CharField(max_length=120, blank=True)

    #: Charged days as computed at submission, and again at closure.
    requested_days = models.DecimalField(max_digits=6, decimal_places=2)
    actual_days = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    policy_id = models.IntegerField(null=True, blank=True)

    #: The approval path, resolved once at submission and then obeyed.
    authority_rule_id = models.IntegerField(null=True, blank=True)
    applicant_designation = models.CharField(max_length=120, blank=True)
    sanctioning_designation = models.CharField(max_length=120, blank=True)
    establishment_step = models.BooleanField(default=False)
    unit_head_is_final = models.BooleanField(default=False)
    self_sanction = models.BooleanField(default=False)
    calendar_id = models.IntegerField(null=True, blank=True)
    #: The applicant's department, as the directory spells it.
    unit = models.CharField(max_length=80, blank=True, db_index=True)

    #: BR-EL-013. Station leave travels inside the application, not beside it.
    station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=160, blank=True)
    station_from = models.DateField(null=True, blank=True)
    station_to = models.DateField(null=True, blank=True)

    #: Set when the leave is one an earlier request extended.
    extends_request_id = models.IntegerField(null=True, blank=True, db_index=True)

    #: A proposed extension, while it is being decided.
    extension_to = models.DateField(null=True, blank=True)
    extension_days = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    #: BR-EL-017: the unit head's view, where it is a recommendation.
    unit_head_recommended = models.BooleanField(null=True, blank=True)
    resumed_on = models.DateField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        ordering = ["-starts_on", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_on__gte=models.F("starts_on")),
                name="leave_request_period_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(half="") | models.Q(starts_on=models.F("ends_on")),
                name="leave_request_half_day_is_one_date",
            ),
            models.CheckConstraint(
                condition=models.Q(requested_days__gt=0),
                name="leave_request_days_positive",
            ),
            # BR-EL-013. Station details belong with a station-leave application.
            models.CheckConstraint(
                condition=models.Q(station_leave=False, station_destination="")
                | models.Q(station_leave=True),
                name="leave_request_station_details_need_flag",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "starts_on"], name="leave_request_person_idx"),
            models.Index(fields=["state", "unit"], name="leave_request_queue_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.category} {self.starts_on} to {self.ends_on} ({self.state})"


class SubstituteNomination(TimeStampedModel):
    """BR-EL-014, BR-EL-015. One nomination, awaiting or holding a decision."""

    class Response(models.TextChoices):
        PENDING = "PENDING", "Awaiting response"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"

    request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="nominations"
    )
    substitute_user_id = models.IntegerField(db_index=True)
    response = models.CharField(
        max_length=10, choices=Response.choices, default=Response.PENDING
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    remark = models.CharField(max_length=250, blank=True)
    #: An extension nominates afresh, so a request can hold several in turn.
    supersedes_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_substitute_nomination"
        ordering = ["request_id", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(response="PENDING", responded_at__isnull=True)
                | ~models.Q(response="PENDING"),
                name="leave_nomination_pending_has_no_decision_time",
            ),
        ]
        indexes = [
            models.Index(
                fields=["substitute_user_id", "response"], name="leave_nomination_inbox_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.substitute_user_id} on {self.request_id}: {self.response}"
