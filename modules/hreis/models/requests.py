"""One immutable route snapshot and event trail per HR request."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class HRRequest(TimeStampedModel, UserScopedModel):
    FAMILY_CHOICES = [
        ("leave", "Leave"),
        ("appraisal", "Appraisal"),
        ("ltc", "LTC"),
        ("cpda", "CPDA"),
    ]
    family = models.CharField(max_length=12, choices=FAMILY_CHOICES)
    subtype = models.CharField(max_length=40, blank=True)
    state = models.CharField(max_length=48)
    payload = models.JSONField(default=dict)
    policy_version = models.ForeignKey(
        "HRPolicyVersion", on_delete=models.PROTECT, null=True, blank=True, related_name="requests"
    )
    route_step = models.PositiveSmallIntegerField(default=0)
    version = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "hreis_request"
        indexes = [
            models.Index(fields=["user_id", "-created_at"], name="hr_request_owner_idx"),
            models.Index(fields=["family", "state", "-created_at"], name="hr_request_queue_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(family__in=["leave", "appraisal", "ltc", "cpda"]),
                name="hr_request_family_valid",
            ),
        ]


class ApprovalRouteStep(models.Model):
    request = models.ForeignKey(HRRequest, on_delete=models.PROTECT, related_name="authority_steps")
    position = models.PositiveSmallIntegerField()
    designation = models.CharField(max_length=150)
    policy_version_label = models.CharField(max_length=80)

    class Meta:
        db_table = "hreis_approval_step"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["request", "position"], name="hr_approval_step_unique"),
        ]
        indexes = [
            models.Index(fields=["designation", "request"], name="hr_approval_assigned_idx"),
        ]

    def __str__(self) -> str:
        return f"Route step {self.position} for {self.request_id}"


class HRRequestTransition(models.Model):
    request = models.ForeignKey(HRRequest, on_delete=models.PROTECT, related_name="transitions")
    source = models.CharField(max_length=48)
    event = models.CharField(max_length=48)
    target = models.CharField(max_length=48)
    actor_user_id = models.IntegerField()
    acting_designation = models.CharField(max_length=150)
    specification = models.CharField(max_length=24)
    step_before = models.PositiveSmallIntegerField()
    step_after = models.PositiveSmallIntegerField()
    idempotency_key = models.CharField(max_length=120, unique=True)
    reason = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hreis_request_transition"
        indexes = [
            models.Index(fields=["request", "recorded_at"], name="hr_transition_history_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event} for request {self.request_id}"
