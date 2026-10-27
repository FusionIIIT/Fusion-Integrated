"""Leave requests and their audit trail. People are plain user_id integers."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.elm.domain import categories as c
from modules.elm.domain import state_machine as sm


class LeaveRequest(TimeStampedModel, UserScopedModel):
    LEAVE = "leave"
    EXTENSION = "extension"
    OFFLINE = "offline"
    KINDS = [(LEAVE, "Leave"), (EXTENSION, "Extension"), (OFFLINE, "Offline record")]

    kind = models.CharField(max_length=12, choices=KINDS, default=LEAVE)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                               related_name="extensions")
    category = models.CharField(max_length=4,
                                choices=[(k, v) for k, v in c.LABELS.items()])
    applicant_kind = models.CharField(max_length=12)
    applicant_unit = models.CharField(max_length=80, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=6, blank=True,
                            choices=[(h, h) for h in c.HALVES])
    days = models.DecimalField(max_digits=6, decimal_places=2)
    purpose = models.TextField()
    medical_evidence = models.CharField(max_length=500, blank=True)

    station_leave = models.BooleanField(default=False)
    station_from = models.DateField(null=True, blank=True)
    station_to = models.DateField(null=True, blank=True)
    station_address = models.CharField(max_length=300, blank=True)

    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(max_length=12, blank=True)
    responsibility = models.CharField(max_length=300, blank=True)

    status = models.CharField(max_length=24, db_index=True,
                              choices=[(s, s.replace("_", " ")) for s in sm.STATES])
    route = models.JSONField(default=list)
    stage = models.PositiveSmallIntegerField(default=0)
    current_role = models.CharField(max_length=100, blank=True, db_index=True)
    stage_entered_at = models.DateTimeField(null=True, blank=True)
    recommendation = models.CharField(max_length=20, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    actual_return_date = models.DateField(null=True, blank=True)
    resumption_note = models.CharField(max_length=500, blank=True)

    policy_version_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="elm_request_period_order"),
            models.CheckConstraint(condition=models.Q(days__gt=0),
                                   name="elm_request_days_positive"),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_request_user_idx"),
            models.Index(fields=["current_role", "status"], name="elm_request_queue_idx"),
        ]

    def __str__(self) -> str:
        return f"leave#{self.pk} u{self.user_id} {self.category} {self.status}"

    @property
    def current_step(self) -> dict | None:
        if 0 <= self.stage < len(self.route):
            return self.route[self.stage]
        return None


class LeaveTransition(models.Model):
    """Append-only audit of every state change."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="transitions")
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    event = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=500, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_transition"
        indexes = [models.Index(fields=["request", "at"], name="elm_transition_idx")]

    def __str__(self) -> str:
        return f"leave#{self.request_id} {self.from_status}->{self.to_status}"
